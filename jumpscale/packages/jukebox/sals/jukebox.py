from collections import defaultdict
import datetime
from decimal import Decimal
from enum import Enum
from time import sleep
import uuid

import gevent
from jumpscale.clients.explorer.models import Container, DiskType, NextAction, WorkloadType
from jumpscale.core.base import Base, fields
from jumpscale.loader import j
from jumpscale.sals.reservation_chatflow import DeploymentFailed, deployer, deployment_context, solutions

from jumpscale.sals.vdc.scheduler import GlobalCapacityChecker, GlobalScheduler, Scheduler

# 1. create pool
# 2. create network
# 3. create wallet for user
# 4. create indentity for the user
# 5. blockchain ndoes crud

CURRENCIES = ["TFT"]
IDENTITY_PREFIX = "jukebox"


def on_exception(greenlet_thread):
    """Callback to handle exception raised by service greenlet_thread
    Arguments:
        greenlet_thread (Greenlet): greenlet_thread object
    """
    message = f"raised an exception: {greenlet_thread.exception}"
    j.tools.alerthandler.alert_raise(app_name="jukebox", message=message, alert_type="exception")
    j.logger.error(message)


# flist_map = {
#     "digibyte": {"flist": "http"},
#     "dash": "",
#     "matic": "",
#     "ubuntu": "https://hub.grid.tf/tf-bootable/3bot-ubuntu-20.04.flist",
#     "presearch": "https://hub.grid.tf/waleedhammam.3bot/arrajput-presearch-latest.flist",
# }


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
    flist=None,
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
            deploy_container,
            network_name,
            identity_name,
            node,
            pool_id,
            ip_address,
            blockchain_type,
            env,
            metadata,
            flist,
        )
        thread.link_exception(on_exception)
        deployment_threads.append(thread)
        # END SPAWN
    # TODO check resv ids success/failure, if resv failed retry on same node
    gevent.joinall(deployment_threads)


def deploy_container(
    network_name,
    identity_name,
    node,
    pool_id,
    ip_address,
    blockchain_type="ubuntu",
    env=None,
    metadata=None,
    flist=None,
):
    metadata = metadata or {}
    env = env or {}

    if not flist:
        raise Exception(f"Flist for {blockchain_type} not found, Please pass it")

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


def _get_farm_name(pool_id, identity_name):
    zos = j.sals.zos.get(identity_name)
    farm_id = j.sals.reservation_chatflow.deployer.get_pool_farm_id(pool_id=pool_id)
    return zos._explorer.farms.get(farm_id).name


def _filter_deployments(workloads, identity_name, solution_type=None):
    deployments = defaultdict(lambda: [])
    for workload in workloads:
        if workload.info.workload_type == WorkloadType.Container:
            metadata = j.sals.reservation_chatflow.deployer.decrypt_metadata(workload.info.metadata, identity_name)
            try:
                metadata_dict = j.data.serializers.json.loads(metadata)
            except Exception as e:
                continue
            if not metadata_dict.get("form_info"):
                continue
            form_info = metadata_dict["form_info"]
            workload_solution_type = form_info["chatflow"]
            name = form_info["Solution name"]
            if (solution_type and solution_type == workload_solution_type) or not solution_type:
                for deployment in deployments[workload_solution_type]:
                    if name == deployment["name"]:
                        deployment["workloads"].append(workload.to_dict())
                        break
                else:
                    farm_name = _get_farm_name(workload.info.pool_id, identity_name)
                    deployments[workload_solution_type].append(
                        {"name": name, "metadata": form_info, "farm": farm_name, "workloads": [workload.to_dict()]}
                    )

    return deployments


# listing
def list_deployments(identity_name, solution_type=None):
    identity_name = j.data.text.removesuffix(identity_name, ".3bot")
    identity = j.core.identity.find(identity_name)
    if not identity:
        return {}

    zos = j.sals.zos.get(identity_name)
    workloads = zos.workloads.list_workloads(identity.tid, NextAction.DEPLOY)
    return _filter_deployments(workloads, identity_name, solution_type)


def delete_deployment(identity_name, solution_type, deployment_name):
    zos = j.sals.zos.get(identity_name)
    deployments = list_deployments(identity_name, solution_type)
    if solution_type not in deployments:
        return False

    deleted_workloads = []
    # Delete workloads of the deployment with deployment_name
    for deployment in deployments[solution_type]:
        if deployment["name"] == deployment_name:
            for workload in deployment["workloads"]:
                zos.workloads.decomission(workload["id"])
                deleted_workloads.append(workload["id"])
            success = True
            break
    else:
        success = False

    # Wait for all workloads to be deleted successfully
    for wid in deleted_workloads:
        success = success and deployer.wait_workload_deletion(wid, identity_name=identity_name)

    return success
