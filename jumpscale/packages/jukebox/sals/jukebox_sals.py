from jumpscale.loader import j
import netaddr
from time import sleep
import uuid
from jumpscale.clients.explorer.models import State, WorkloadType, NextAction

zos = j.sals.zos.get()

NETWORKS = {"mainnet": "explorer.grid.tf", "testnet": "explorer.testnet.grid.tf", "devnet": "explorer.devnet.grid.tf"}


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


def generate_qr_payment(address, amount, currency):
    pass


def create_identity(name, email, network):

    identity = j.core.identity.get(f"jukebox_{network}_{name}", email=email, explorer_url=NETWORKS[network])
    identity.save()


def create_wallet(name):
    # how many wallets to be created? user->wallet or usser-> wallet+central wallet used to fund initiating pools
    pass


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


def create_network(identity_name, pool_id, network_name, ip_range):
    identity = j.core.identity.get(identity_name)
    zos = j.sals.zos.get(identity_name)
    workloads = zos.workloads.list(identity.tid, NextAction.DEPLOY)
    network = zos.network.load_network(network_name)  # TODO do we need to use different networks or one is enough?

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
        zos.network.add_node(network, access_node.node_id, "100.10.0.0/24", pool_id)
        wg_quick = zos.network.add_access(network, access_node.node_id, "100.10.1.0/24", ipv4=True)
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


def create_vm(pool_id):
    pass

