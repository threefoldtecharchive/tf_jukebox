from jumpscale.core.base import Base, fields
from jumpscale.loader import j
from jumpscale.clients.explorer.models import (
    DiskType,
    K8s,
    NextAction,
    PublicIP,
    WorkloadType,
    Container
)
from enum import Enum
from jumpscale.sals.reservation_chatflow import DeploymentFailed, deployer, deployment_context, solutions
import datetime
from decimal import Decimal
import uuid

# 1. create pool
# 2. create network
# 3. create wallet for user 
# 4. create indentity for the user
# 5. blockchain ndoes crud

CURRENCIES = ["TFT"]
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
    "digibyte": "http",
    "dash": "",
    "matic": "",
    "ubuntu": "https://hub.grid.tf/tf-bootable/3bot-ubuntu-20.04.flist",
}
def create_user_wallet(tname):
    # Create a wallet for the user to be used in extending his pool
    wallet_name = f"jukebox_{tname}"
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

def create_empty_pool(identity_name, farm="freefarm"):
    # create a pool for the user if the pool doesn't exist
    zos = j.sals.zos.get(identity_name)
    if not zos.pools.list():
        
        payment_detail = zos.pools.create(cu=0, su=0, ipv4us=0, farm=farm, currencies=CURRENCIES)
        return payment_details.reservation_id 
    else:
        return zos.pools.list()[0].pool_id
def calculate_payment(payment_info):
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


def extend_pool(pool_id, cloud_units, farm, identity_name, wallet):
    zos = j.sals.zos.get(identity_name)
    node_ids = [node.node_id for node in zos.nodes_finder.nodes_search(farm)]
    payment_info = zos.pools.extend(pool_id=pool_id, cu=int(cloud_units["cu"]), su=int(cloud_units["su"]), ipv4us=int(cloud_units["ipv4u"]), currencies=CURRENCIES, node_ids=[])
    # escrow_address, total_amount, escrow_asset = calculate_payment(payment_info)
    zos.billing.payout_farmers(wallet, payment_info)
    if not deployer.wait_pool_reservation(payment_info.reservation_id):
        j.logger.warning(
            f"pool {pool_id} extension timedout for reservation: {payment_info.reservation_id}"
        )
    # wallet.transfer(destination_address=escrow_address, amount=total_amount, asset=escrow_asset)


def calculate_required_units(containers, days):
    cloud_units = {"cu":0, "su":0, "ipv4u": 0}
    for cont in containers:
        cont_units = cont.resource_units().cloud_units()
        cloud_units["cu"] += cont_units.cu
        cloud_units["su"] += cont_units.su
        cloud_units["cu"] *= days * 24 * 60 * 60
        cloud_units["su"] *= days * 24 * 60 * 60
    return cloud_units

def create_capacity_pool(wallet, cu=100, su=100, ipv4us=0, farm="freefarm", currencies=None):
    currencies = currencies or ["TFT"]
    payment_detail = zos.pools.create(cu=cu, su=su, ipv4us=ipv4us, farm=farm, currencies=currencies)
    # wallet = j.clients.stellar.get(wallet)
    txs = zos.billing.payout_farmers(wallet, payment_detail)
    pool = zos.pools.get(payment_detail.reservation_id)
    while pool.cus == 0:
        pool = zos.pools.get(payment_detail.reservation_id)
        sleep(1)
    return payment_detail.reservation_id

def wait_workload(wid):
    workload = zos.workloads.get(wid)
    timeout = j.data.time.now().timestamp + 15 * 60 * 60
    while not workload.info.result.state.value and not workload.info.result.message:
        if j.data.time.now().timestamp > timeout:
            raise j.exceptions.Runtime(f"workload {wid} failed to deploy in time")
        sleep(1)
        workload = zos.workloads.get(wid)
    if workload.info.result.state != State.Ok:
        raise j.exceptions.Runtime(f"workload {wid} failed due to {workload.info.result.message}")

def get_container_ip(network_name, identity_name, node, pool_id, tname):
    network_view = deployer.get_network_view(network_name)
    network_view_copy = network_view.copy()
    result = deployer.add_network_node(
        network_view.name,
        node,
        pool_id,
        network_view_copy,
        identity_name=identity_name,
        owner=tname,
    )
    if result:
        # self.md_show_update("Deploying Network on Nodes....")
        for wid in result["ids"]:
            success = deployer.wait_workload(wid, None, breaking_node_id=node.node_id)
            if not success:
                raise DeploymentFailed(f"Failed to add node {node.node_id} to network {wid}", wid=wid)
        network_view_copy = network_view_copy.copy()
    free_ips = network_view_copy.get_node_free_ips(node)
    return free_ips[0]
    # self.ip_address = self.drop_down_choice(
    #     "Please choose IP Address for your solution", free_ips, default=free_ips[0], required=True,
    # )

def create_network(identity_name, pool_id, network_name, ip_range):
    identity = j.core.identity.get(identity_name)
    zos = j.sals.zos.get(identity_name)
    workloads = zos.workloads.list(identity.tid, NextAction.DEPLOY)
    network = zos.network.load_network(network_name)  

    if not network:
        # used_ip_ranges = set()
        # existing_nodes = set()
        # for workload in self.network_workloads:
        #     used_ip_ranges.add(workload.iprange)
        #     for peer in workload.peers:
        #         used_ip_ranges.add(peer.iprange)
        #     if workload.info.node_id in node_ids:
        #         existing_nodes.add(workload.info.node_id)

        # if len(existing_nodes) == len(node_ids):
        #     return

        # node_to_range = {}
        # node_to_pool = {}
        # for idx, node_id in enumerate(node_ids):
        #     if node_id in existing_nodes:
        #         continue
        #     node_to_pool[node_id] = pool_ids[idx]
        #     network_range = netaddr.IPNetwork(self.iprange)
        #     for _, subnet in enumerate(network_range.subnet(24)):
        #         subnet = str(subnet)
        #         if subnet not in used_ip_ranges:
        #             node_to_range[node_id] = subnet
        #             used_ip_ranges.add(subnet)
        #             break
        #     else:
        #         raise StopChatFlow("Failed to find free network")

        network = zos.network.create(ip_range=ip_range, network_name=network_name)
        nodes = zos.nodes_finder.nodes_by_capacity(pool_id=pool_id)
        access_node = list(filter(zos.nodes_finder.filter_public_ip4, nodes))[0]
        zos.network.add_node(network, access_node.node_id, "10.100.0.0/24", pool_id)
        wg_quick = zos.network.add_access(network, access_node.node_id, "10.100.1.0/24", ipv4=True)
        wids = []
        for workload in network.network_resources:
            wid = zos.workloads.deploy(workload)
            wids.append(wid)
        for wid in wids:
            wait_workload(wid)
        print(wg_quick)
        with open(f"jukebox_{network_name}.conf", "w") as f:
            f.write(wg_quick)

    return network

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
    **metadata, ):
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

    

def start(identity_name):
    farm_id = 1
    pool_id = create_empty_pool(identity_name)
    print(f"***************{pool_id}****************")
    network_name = "my_network"
    create_network(identity_name, pool_id, network_name, "10.100.0.0/16")
    zos = j.sals.zos.get(identity_name)
    cont = Container()
    cont.capacity.cpu = 1
    cont.capacity.memory = 1024
    cont.capacity.disk_size = 1024
    cont.capacity.disk_type = DiskType.SSD
    cloud_units = calculate_required_units([cont], days=1)
    wallet = j.clients.stellar.get("work")
    extend_pool(pool_id, cloud_units, farm_id, identity_name, wallet)

    # getting node_id 
    nodes = j.sals.zos.get().nodes_finder.nodes_by_capacity(pool_id=pool_id, cru=cont.capacity.cpu, sru=cont.capacity.disk_size/1024, mru=cont.capacity.memory/1024, hru=0)
    nodes = list(nodes)
    if not nodes:
        raise Exception("No nodes available")
    # nodes_ids = [node.node_id for node in nodes]
    metadata = {
            "name": "test_ubuntu",
            "form_info": {"chatflow": "jukebox", "Solution name": "test_ubuntu"},
        }
    ip_address = get_container_ip(network_name, identity_name, nodes[0], pool_id, "ashraf.3bot")
    flist = flist_map.get("ubuntu")
    if not flist:
        raise Exception(f"Flist for {blockchain_type} not found")
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDTwULSsUubOq3VPWL6cdrDvexDmjfznGydFPyaNcn7gAL9lRxwFbCDPMj7MbhNSpxxHV2+/iJPQOTVJu4oc1N7bPP3gBCnF51rPrhTpGCt5pBbTzeyNweanhedkKDsCO2mIEh/92Od5Hg512dX4j7Zw6ipRWYSaepapfyoRnNSriW/s3DH/uewezVtL5EuypMdfNngV/u2KZYWoeiwhrY/yEUykQVUwDysW/xUJNP5o+KSTAvNSJatr3FbuCFuCjBSvageOLHePTeUwu6qjqe+Xs4piF1ByO/6cOJ8bt5Vcx0bAtI8/MPApplUU/JWevsPNApvnA/ntffI+u8DCwgP"
    resv_id = deployer.deploy_container(
        pool_id=pool_id,
        node_id=nodes[0].node_id,
        network_name=network_name,
        ip_address=ip_address,
        flist=flist,
        cpu=1,
        memory=1024,
        disk_size=512,
        env={"pub_key": public_key},
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
    # create_blockchain_container("ubuntu", pool_id, nodes[0].node_id, network_name, ip, **metadata)
    



    

