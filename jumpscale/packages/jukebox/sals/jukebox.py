from jumpscale.core.base import Base, fields
from jumpscale.loader import j
from jumpscale.clients.explorer.models import DiskType, NextAction, Container
from enum import Enum
from jumpscale.sals.reservation_chatflow import DeploymentFailed, deployer, deployment_context, solutions
from jumpscale.sals.vdc.scheduler import Scheduler, GlobalCapacityChecker, GlobalScheduler
import datetime
from decimal import Decimal
import uuid
from time import sleep
from collections import defaultdict
import gevent

# 1. create pool
# 2. create network
# 3. create wallet for user
# 4. create indentity for the user
# 5. blockchain ndoes crud

CURRENCIES = ["TFT"]


def on_exception(greenlet_thread):
    """Callback to handle exception raised by service greenlet_thread
    Arguments:
        greenlet_thread (Greenlet): greenlet_thread object
    """
    message = f"raised an exception: {greenlet_thread.exception}"
    j.tools.alerthandler.alert_raise(app_name="jukebox", message=message, alert_type="exception")
    j.logger.error(message)


class STATE(Enum):
    CREATING = "CREATING"
    DEPLOYED = "DEPLOYED"
    ERROR = "ERROR"
    EMPTY = "EMPTY"


class BlockchainNode(Base):
    deployment_name = fields.String()
    owner_tname = fields.String()
    solution_uuid = fields.String(default=lambda: uuid.uuid4().hex)
    identity_tid = fields.Integer()
    created = fields.DateTime(default=datetime.datetime.utcnow)
    expiration = fields.Float(default=lambda: j.data.time.utcnow().timestamp + 30 * 24 * 60 * 60)
    last_updated = fields.DateTime(default=datetime.datetime.utcnow)
    is_blocked = fields.Boolean(default=False)  # grace period action is applied
    explorer_url = fields.String(default=lambda: j.core.identity.me.explorer_url)
    state = fields.Enum(STATE)
    # __lock = BoundedSemaphore(1)


flist_map = {
    "digibyte": {"flist": "http"},
    "dash": "",
    "matic": "",
    "ubuntu": "https://hub.grid.tf/tf-bootable/3bot-ubuntu-20.04.flist",
}


def get_or_create_user_wallet(wallet_name):
    # Create a wallet for the user to be used in extending his pool
    if not j.clients.stellar.find(wallet_name):
        wallet = j.clients.stellar.new(wallet_name)
        try:
            wallet.activate_through_threefold_service()
        except Exception:
            j.clients.stellar.delete(name=wallet_name)
            raise j.exceptions.JSException("Error on wallet activation")

        try:
            wallet.add_known_trustline("TFT")
        except Exception:
            j.clients.stellar.delete(name=wallet_name)
            raise j.exceptions.JSException(
                f"Failed to add trustlines to wallet {wallet_name}. Any changes made will be reverted."
            )

        wallet.save()
    else:
        wallet = j.clients.stellar.get(wallet_name)
    return wallet


def create_empty_pool(identity_name, farm="freefarm"):
    # create a pool for the user if the pool doesn't exist
    zos = j.sals.zos.get(identity_name)
    if not zos.pools.list():
        payment_detail = zos.pools.create(cu=0, su=0, ipv4us=0, farm=farm)
        return payment_detail.reservation_id
    else:
        return zos.pools.list()[0].pool_id


def calculate_payment_from_payment_info(payment_info):
    escrow_info = payment_info.escrow_information
    resv_id = payment_info.reservation_id
    escrow_address = escrow_info.address
    escrow_asset = escrow_info.asset
    total_amount = escrow_info.amount
    if not total_amount:
        return 0
    total_amount_dec = Decimal(total_amount) / Decimal(1e7)
    total_amount = "{0:f}".format(total_amount_dec)
    return escrow_address, total_amount, escrow_asset


def calculate_payment_from_container_resources(
    cpu, memory, disk_size, duration, farm_id=None, farm_name="freefarm", disk_type=DiskType.SSD
):
    if farm_name and not farm_id:
        zos = j.sals.zos.get()
        farm_id = zos._explorer.farms.get(farm_name=farm_name).id
    empty_container = Container()
    empty_container.capacity.cpu = cpu
    empty_container.capacity.memory = memory
    empty_container.capacity.disk_size = disk_size
    empty_container.capacity.disk_type = disk_type
    cost = j.tools.zos.consumption.cost(empty_container, duration=duration, farm_id=farm_id)
    return cost


def calculate_required_units(cpu, memory, disk_size, duration_seconds, number_of_containers=1):
    cont = Container()
    cont.capacity.cpu = cpu
    cont.capacity.memory = memory
    cont.capacity.disk_size = disk_size
    cont.capacity.disk_type = DiskType.SSD

    cloud_units = {"cu": 0, "su": 0, "ipv4u": 0}
    cont_units = cont.resource_units().cloud_units()
    cloud_units["cu"] += cont_units.cu * number_of_containers
    cloud_units["su"] += cont_units.su * number_of_containers
    cloud_units["cu"] *= duration_seconds
    cloud_units["su"] *= duration_seconds
    return cloud_units


def get_possible_farms(cru, sru, mru, number_of_deployments):
    gcc = GlobalCapacityChecker()
    farm_names = gcc.get_available_farms(
        cru=cru * number_of_deployments,
        mru=mru * number_of_deployments,
        sru=sru * number_of_deployments,
        # ip_version=None,
        # no_nodes=1,
        accessnodes=True,
    )
    return farm_names


def get_network_ip_range():
    return j.sals.reservation_chatflow.reservation_chatflow.get_ip_range()


def show_payment(bot, cost, wallet_name, expiry=5, description=None):
    payment_id, _ = j.sals.billing.submit_payment(
        amount=cost, wallet_name=wallet_name, refund_extra=False, expiry=expiry, description=description
    )

    if cost > 0:
        notes = []
        return j.sals.billing.wait_payment(payment_id, bot=bot, notes=notes), cost, payment_id
    else:
        return True, cost, payment_id


# def extend_pool(pool_id, cloud_units, farm, identity_name, wallet):
#     zos = j.sals.zos.get(identity_name)
#     node_ids = [node.node_id for node in zos.nodes_finder.nodes_search(farm)]
#     payment_info = zos.pools.extend(
#         pool_id=pool_id,
#         cu=int(cloud_units["cu"]),
#         su=int(cloud_units["su"]),
#         ipv4us=int(cloud_units["ipv4u"]),
#         node_ids=[],
#     )
#     # escrow_address, total_amount, escrow_asset = calculate_payment(payment_info)
#     zos.billing.payout_farmers(wallet, payment_info)
#     if not deployer.wait_pool_reservation(payment_info.reservation_id):
#         j.logger.warning(f"pool {pool_id} extension timedout for reservation: {payment_info.reservation_id}")
#     # wallet.transfer(destination_address=escrow_address, amount=total_amount, asset=escrow_asset)


def create_capacity_pool(wallet, cu=100, su=100, ipv4us=0, farm="freefarm", identity_name=None):
    zos = j.sals.zos.get(identity_name)
    payment_detail = zos.pools.create(cu=cu, su=su, ipv4us=ipv4us, farm=farm)
    # wallet = j.clients.stellar.get(wallet)
    txs = zos.billing.payout_farmers(wallet, payment_detail)
    pool = zos.pools.get(payment_detail.reservation_id)
    while pool.cus == 0:
        pool = zos.pools.get(payment_detail.reservation_id)
        sleep(1)
    # TODO add in QR code with payment total for users
    return payment_detail.reservation_id


def get_container_ip(network_name, identity_name, node, pool_id, tname, excluded_ips=None):
    excluded_ips = excluded_ips or []
    network_view = deployer.get_network_view(network_name, identity_name=identity_name)
    network_view_copy = network_view.copy()
    result = deployer.add_network_node(
        network_view.name, node, pool_id, network_view_copy, identity_name=identity_name, owner=tname
    )
    if result:
        # self.md_show_update("Deploying Network on Nodes....")
        for wid in result["ids"]:
            success = deployer.wait_workload(wid, None, breaking_node_id=node.node_id)
            if not success:
                raise DeploymentFailed(f"Failed to add node {node.node_id} to network {wid}", wid=wid)
        network_view_copy = network_view_copy.copy()
    free_ips = network_view_copy.get_node_free_ips(node)
    for ip in free_ips:
        if ip not in excluded_ips:
            return ip

    # self.ip_address = self.drop_down_choice(
    #     "Please choose IP Address for your solution", free_ips, default=free_ips[0], required=True,
    # )


# def create_network(identity_name, pool_id, network_name, ip_range=None):
#     ip_range = ip_range or get_network_ip_range()
#     identity = j.core.identity.get(identity_name)
#     zos = j.sals.zos.get(identity_name)
#     workloads = zos.workloads.list(identity.tid, NextAction.DEPLOY)
#     network = zos.network.load_network(network_name)

#     if not network:

#         network = zos.network.create(ip_range=ip_range, network_name=network_name)
#         nodes = zos.nodes_finder.nodes_by_capacity(pool_id=pool_id)
#         access_node = list(filter(zos.nodes_finder.filter_public_ip4, nodes))[0]
#         zos.network.add_node(network, access_node.node_id, "10.100.0.0/24", pool_id)
#         wg_quick = zos.network.add_access(network, access_node.node_id, "10.100.1.0/24", ipv4=True)
#         wids = []
#         for workload in network.network_resources:
#             wid = zos.workloads.deploy(workload)
#             wids.append(wid)
#         for wid in wids:
#             deployer.wait_workload(wid, identity_name)
#         print(wg_quick)
#         with open(f"jukebox_{network_name}.conf", "w") as f:
#             f.write(wg_quick)

#     return network


def deploy_network(identity_name, pool_id, network_name, owner_tname, ip_range=None):
    ip_range = ip_range or get_network_ip_range()
    scheduler = Scheduler(pool_id=pool_id)
    network_success = False
    ip_version = "IPv4"
    for access_node in scheduler.nodes_by_capacity(ip_version=ip_version, accessnodes=True):
        j.logger.info(f"Deploying network on node {access_node.node_id}")
        network_success = True
        result = deployer.deploy_network(network_name, access_node, ip_range, ip_version, pool_id, identity_name)
        for wid in result["ids"]:
            try:
                success = deployer.wait_workload(
                    wid,
                    breaking_node_id=access_node.node_id,
                    identity_name=identity_name,
                    bot=None,
                    cancel_by_uuid=False,
                    expiry=5,
                )
                network_success = network_success and success
            except Exception as e:
                network_success = False
                j.logger.error(f"Network workload {wid} failed on node {access_node.node_id} due to error {str(e)}")
                break
        if network_success:
            # store wireguard config
            j.logger.info(
                f"saving wireguard config to {j.core.dirs.CFGDIR}/jukebox/wireguard/{owner_tname}/{network_name}.conf"
            )
            wg_quick = result["wg"]
            j.sals.fs.mkdirs(f"{j.core.dirs.CFGDIR}/jukebox/wireguard/{owner_tname}")
            j.sals.fs.write_file(f"{j.core.dirs.CFGDIR}/jukebox/wireguard/{owner_tname}/{network_name}.conf", wg_quick)
            return True, wg_quick


def create_blockchain_container(
    blockchain_type,
    pool_id,
    node_id,
    network_name,
    ip_address,
    env=None,
    cpu=1,
    identity_name=None,
    memory=1024,
    disk_size=256,
    disk_type=DiskType.SSD,
    entrypoint="",
    interactive=False,
    secret_env=None,
    volumes=None,
    log_config=None,
    public_ipv6=False,
    description="",
    **metadata,
):
    # Create a new container using a blockchain flist
    flist = flist_map.get(blockchain_type)
    if not flist:
        raise Exception(f"Flist for {blockchain_type} not found")
    env = env or {}
    encrypted_secret_env = {}
    if secret_env:
        for key, val in secret_env.items():
            val = val or ""
            encrypted_secret_env[key] = j.sals.zos.get(identity_name).container.encrypt_secret(node_id, val)
    for key, val in env.items():
        env[key] = val or ""
    container = j.sals.zos.get(identity_name).container.create(
        node_id,
        network_name,
        ip_address,
        flist,
        pool_id,
        env,
        cpu,
        memory,
        disk_size,
        entrypoint,
        interactive,
        encrypted_secret_env,
        public_ipv6=public_ipv6,
    )
    if volumes:
        for mount_point, vol_id in volumes.items():
            j.sals.zos.get(identity_name).volume.attach_existing(container, f"{vol_id}-1", mount_point)
    if metadata:
        container.info.metadata = deployer.encrypt_metadata(metadata, identity_name=identity_name)
        container.info.description = description
    if log_config:
        j.sals.zos.get(identity_name).container.add_logs(container, **log_config)
    return j.sals.zos.get(identity_name).workloads.deploy(container)


def deploy_all_containers(
    farm_name,
    number_of_deployments,
    network_name,
    cru,
    sru,
    mru,
    pool_ids,
    identity_name,
    owner_tname,
    blockchain_type,
    env=None,
    metadata=None,
):
    metadata = metadata or {}
    env = env or {}

    used_ip_addresses = defaultdict(lambda: [])  # {node_id:[ip_addresses]}
    # TODO when using multiple farms use GlobalScheduler instead and pass farm_name when deploying
    scheduler = Scheduler(farm_name=farm_name)
    deployment_threads = []
    for _ in range(number_of_deployments):
        # for each node check how many containers can be deployed on it, and based on that assign that node for X deployments
        pool_id = pool_ids[0]  # TODO
        node = next(scheduler.nodes_by_capacity(cru=cru, sru=sru, mru=mru))

        excluded_ips = used_ip_addresses.get(node.node_id, [])
        ip_address = get_container_ip(network_name, identity_name, node, pool_id, owner_tname, excluded_ips)

        used_ip_addresses[node.node_id].append(ip_address)

        # START SPAWN

        thread = gevent.spawn(
            deploy_container, network_name, identity_name, node, pool_id, ip_address, blockchain_type, env, metadata
        )
        thread.link_exception(on_exception)
        deployment_threads.append(thread)
        # END SPAWN
    # TODO check resv ids success/failure, if resv failed retry on same node
    gevent.joinall(deployment_threads)


def deploy_container(
    network_name, identity_name, node, pool_id, ip_address, blockchain_type="ubuntu", env=None, metadata=None
):
    metadata = metadata or {}
    env = env or {}

    flist = flist_map.get(blockchain_type)
    if not flist:
        raise Exception(f"Flist for {blockchain_type} not found")
    resv_id = deployer.deploy_container(
        identity_name=identity_name,
        pool_id=pool_id,
        node_id=node.node_id,
        network_name=network_name,
        ip_address=ip_address,
        flist=flist,
        cpu=1,
        memory=1024,
        disk_size=512,
        env=env,
        interactive=False,
        entrypoint="/bin/bash /start.sh",
        # log_config=self.log_config,
        public_ipv6=True,
        **metadata,
        solution_uuid=uuid.uuid4().hex,
    )
    success = deployer.wait_workload(resv_id, None)
    if not success:
        raise DeploymentFailed(f"Failed to deploy workload {resv_id}", wid=resv_id)
    print(f"succeeded, {resv_id}")
    return resv_id


def start(identity_name, number_of_deployments=2):

    farm_id = 1
    pool_id = create_empty_pool(identity_name, farm)
    wallet = j.clients.stellar.get("work")
    owner_tname = "ranatarek.3bot"
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDTwULSsUubOq3VPWL6cdrDvexDmjfznGydFPyaNcn7gAL9lRxwFbCDPMj7MbhNSpxxHV2+/iJPQOTVJu4oc1N7bPP3gBCnF51rPrhTpGCt5pBbTzeyNweanhedkKDsCO2mIEh/92Od5Hg512dX4j7Zw6ipRWYSaepapfyoRnNSriW/s3DH/uewezVtL5EuypMdfNngV/u2KZYWoeiwhrY/yEUykQVUwDysW/xUJNP5o+KSTAvNSJatr3FbuCFuCjBSvageOLHePTeUwu6qjqe+Xs4piF1ByO/6cOJ8bt5Vcx0bAtI8/MPApplUU/JWevsPNApvnA/ntffI+u8DCwgP"
    env = {"pub_key": public_key}
    blockchain_type = "ubuntu"

    metadata = {"name": "test_ubuntu", "form_info": {"chatflow": "jukebox", "Solution name": "test_ubuntu"}}

    print(f"***************Empty pool: {pool_id}****************")
    network_name = "my_network"
    create_network(identity_name, pool_id, network_name, "10.100.0.0/16")
    zos = j.sals.zos.get(identity_name)

    query = {"cru": 1, "sru": 1, "mru": 1}
    duration_days = 1

    # Check the farms that will have enough resources for the deployment (the user will choose one from it)
    farm_names = get_possible_farms(query["cru"], query["sru"], query["mru"], number_of_deployments)
    farm_user_choice = next(farm_names)  # TODO to be adjusted so user can choose multiple farms to distribute nodes on

    # Calculate required units from query
    # cont = Container()
    # cont.capacity.cpu = query["cru"] * 1
    # cont.capacity.memory = query["mru"] * 1024
    # cont.capacity.disk_size = query["sru"] * 1024
    # cont.capacity.disk_type = DiskType.SSD
    cloud_units = calculate_required_units(
        query["cru"] * 1,
        query["mru"] * 1024,
        query["sru"] * 1024,
        duration_seconds=duration_days,
        number_of_containers=number_of_deployments,
    )

    # TODO to be done for all farms to have a list of pool_ids, the following is per one farm
    pool_rev_id = create_capacity_pool(
        wallet,
        cu=cloud_units["cu"] * number_of_deployments,
        su=cloud_units["su"] * number_of_deployments,
        ipv4us=0,
        farm=farm_user_choice,
    )
    pool_ids = [pool_rev_id]

    # Get possible nodes,ip_addresses then spawn deployment of container in gevent
    deploy_all_containers(
        farm_user_choice,
        number_of_deployments,
        network_name,
        query["cru"],
        query["sru"],
        query["mru"],
        pool_ids,
        identity_name,
        owner_tname,
        blockchain_type,
        env,
        metadata,
    )


# create_blockchain_container("ubuntu", pool_id, nodes[0].node_id, network_name, ip, **metadata)

