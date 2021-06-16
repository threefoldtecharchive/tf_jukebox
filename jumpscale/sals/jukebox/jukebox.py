from collections import defaultdict
from time import sleep
import uuid

import gevent
from jumpscale.clients.explorer.models import Container, DiskType, NextAction, WorkloadType
from jumpscale.clients.explorer.models import DiskType, State as WorkloadState
from jumpscale.clients.stellar import TRANSACTION_FEES
from jumpscale.core.base import Base, fields
from jumpscale.core.base import Base, fields
from jumpscale.loader import j
from jumpscale.sals.reservation_chatflow import DeploymentFailed, deployer

from jumpscale.sals.jukebox.models import BlockchainNode, State
from jumpscale.sals.vdc.scheduler import GlobalCapacityChecker, Scheduler

# 1. create pool
# 2. create network
# 3. create wallet for user
# 4. create indentity for the user
# 5. blockchain ndoes crud

CURRENCIES = ["TFT"]
IDENTITY_PREFIX = "jukebox"
JUKEBOX_AUTO_EXTEND_KEY = "jukebox:auto_extend"


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
            wallet.activate_through_activation_wallet()
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
    return True, cost, payment_id


def calculate_funding_amount(identity_name):
    identity = j.core.identity.find(identity_name)
    zos = j.sals.zos.get(identity_name)
    if not identity:
        return 0
    total_price = 0
    deployments = j.sals.jukebox.list(identity_name=identity_name)
    for deployment in deployments:
        price = 0
        if not deployment.auto_extend:
            continue
        if deployment.expiration_date.timestamp() > j.data.time.utcnow().timestamp + 60 * 60 * 24 * 2:
            continue
        pool_id = deployment.pool_ids[0]  # TODO change when having multiple pools
        pool = zos.pools.get(pool_id)  # TODO: set active unit while listing
        cus = pool.active_cu
        sus = pool.active_su
        ipv4us = pool.active_ipv4
        farm_id = zos._explorer.farms.get(farm_name=deployment.farm_name).id
        farm_prices = zos._explorer.farms.get_deal_for_threebot(farm_id, j.core.identity.me.tid)[
            "custom_cloudunits_price"
        ]
        price += zos._explorer.prices.calculate(cus=cus, sus=sus, ipv4us=ipv4us, farm_prices=farm_prices)
        price *= 60 * 60 * 24 * 30
        price += TRANSACTION_FEES
        total_price += price
    return total_price


def get_wallet_funding_info(identity_name):
    wallet = j.clients.stellar.find(identity_name)
    if not wallet:
        return {}

    asset = "TFT"
    current_balance = wallet.get_balance_by_asset(asset)
    amount = calculate_funding_amount(identity_name) - current_balance
    amount = 0 if amount < 0 else round(amount, 6)

    qrcode_data = f"TFT:{wallet.address}?amount={amount}&message=topup&sender=me"
    qrcode_image = j.tools.qrcode.base64_get(qrcode_data, scale=3)

    data = {
        "address": wallet.address,
        "balance": {"amount": current_balance, "asset": asset},
        "amount": amount,
        "qrcode": qrcode_image,
        "network": wallet.network.value,
    }
    return data


class JukeboxDeployment(Base):
    solution_type = fields.String(required=True)
    identity_name = fields.String(required=True)
    deployment_name = fields.String(required=True)
    farm_name = fields.String()
    nodes_count = fields.Integer(required=True)
    pool_ids = fields.List(fields.Integer())  # in case we will support multiple locations
    nodes = fields.List(fields.Object(BlockchainNode))
    state = fields.Enum(State)
    expiration_date = fields.DateTime()
    auto_extend = fields.Boolean(default=False)
    cpu = fields.Integer()  # per node
    memory = fields.Integer()  # per node
    disk_size = fields.Integer()  # per node
    disk_type = fields.Enum(DiskType)  # per node
    _zos = None

    @property
    def zos(self):
        if self._zos is None:
            self._zos = j.sals.zos.get(self.identity_name)
        return self._zos

    def create_capacity_pool(self, wallet, cu=100, su=100, ipv4us=0, farm="freefarm"):
        payment_detail = self.zos.pools.create(cu=cu, su=su, ipv4us=ipv4us, farm=farm)
        # wallet = j.clients.stellar.get(wallet)
        txs = self.zos.billing.payout_farmers(wallet, payment_detail)
        pool = self.zos.pools.get(payment_detail.reservation_id)
        while pool.cus == 0:
            pool = self.zos.pools.get(payment_detail.reservation_id)
            sleep(1)
        # TODO add in QR code with payment total for users
        self.pool_ids.append(payment_detail.reservation_id)
        return payment_detail.reservation_id

    def get_container_ip(self, network_name, node, pool_id, tname, excluded_ips=None):
        excluded_ips = excluded_ips or []
        excluded_nodes = j.core.db.get("excluded_nodes")
        if not excluded_nodes:
            excluded_nodes = []
        else:
            excluded_nodes = j.data.serializers.json.loads(excluded_nodes.decode())

        network_view = deployer.get_network_view(network_name, identity_name=self.identity_name)
        network_view_copy = network_view.copy()
        result = deployer.add_network_node(
            network_view.name, node, pool_id, network_view_copy, identity_name=self.identity_name, owner=tname
        )

        if result:
            # self.md_show_update("Deploying Network on Nodes....")
            try:
                for wid in result["ids"]:
                    success = deployer.wait_workload(wid, None, breaking_node_id=node.node_id, expiry=3)
                    if not success:
                        raise DeploymentFailed(f"Failed to add node {node.node_id} to network {wid}", wid=wid)
            except Exception as e:
                j.logger.exception(f"Failed to deploy network on {node.node_id}", exception=e)
                excluded_nodes = set(excluded_nodes)
                excluded_nodes.add(node.node_id)
                j.core.db.set("excluded_nodes", j.data.serializers.json.dumps(list(excluded_nodes)), ex=3 * 60 * 60)
                return

        network_view_copy = network_view_copy.copy()
        free_ips = network_view_copy.get_node_free_ips(node)
        for ip in free_ips:
            if ip not in excluded_ips:
                return ip

    def deploy_network(self, pool_id, network_name, owner_tname, ip_range=None):
        ip_range = ip_range or get_network_ip_range()
        scheduler = Scheduler(pool_id=pool_id)
        network_success = False
        ip_version = "IPv4"
        for access_node in scheduler.nodes_by_capacity(ip_version=ip_version, accessnodes=True):
            j.logger.info(f"Deploying network on node {access_node.node_id}")
            network_success = True
            result = deployer.deploy_network(
                network_name, access_node, ip_range, ip_version, pool_id, self.identity_name
            )
            for wid in result["ids"]:
                try:
                    success = deployer.wait_workload(
                        wid,
                        breaking_node_id=access_node.node_id,
                        identity_name=self.identity_name,
                        bot=None,
                        cancel_by_uuid=False,
                        expiry=3,
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
                j.sals.fs.write_file(
                    f"{j.core.dirs.CFGDIR}/jukebox/wireguard/{owner_tname}/{network_name}.conf", wg_quick
                )
                return True, wg_quick

    def deploy_all_containers(
        self,
        farm_name,
        number_of_deployments,
        network_name,
        cru,
        sru,
        mru,
        pool_ids,
        owner_tname,
        blockchain_type,
        env=None,
        secret_env=None,
        metadata=None,
        flist=None,
        entry_point="",
    ):
        metadata = metadata or {}
        env = env or {}
        secret_env = secret_env or {}
        used_ip_addresses = defaultdict(lambda: [])  # {node_id:[ip_addresses]}
        # TODO when using multiple farms use GlobalScheduler instead and pass farm_name when deploying
        excluded_nodes = j.core.db.get("excluded_nodes")
        if not j.core.db.get("excluded_nodes"):
            excluded_nodes = []
        else:
            excluded_nodes = j.data.serializers.json.loads(excluded_nodes.decode())
        scheduler = Scheduler(farm_name=farm_name)
        scheduler.exclude_nodes(*excluded_nodes)
        deployment_threads = []
        for i in range(number_of_deployments):
            # for each node check how many containers can be deployed on it, and based on that assign that node for X deployments
            pool_id = pool_ids[0]  # TODO
            node = next(scheduler.nodes_by_capacity(cru=cru, sru=sru, mru=mru))

            excluded_ips = used_ip_addresses.get(node.node_id, [])
            ip_address = self.get_container_ip(network_name, node, pool_id, owner_tname, excluded_ips)
            if not ip_address:
                i -= 1
                continue

            used_ip_addresses[node.node_id].append(ip_address)

            # START SPAWN

            thread = gevent.spawn(
                self.deploy_container,
                network_name,
                node,
                pool_id,
                ip_address,
                blockchain_type,
                env,
                metadata,
                flist,
                entry_point,
                secret_env,
                cru,
                sru * 1024,
                mru * 1024,
            )
            thread.link_exception(on_exception)
            deployment_threads.append(thread)
            # END SPAWN
        # TODO check resv ids success/failure, if resv failed retry on same node
        gevent.joinall(deployment_threads)

    def deploy_container(
        self,
        network_name,
        node,
        pool_id,
        ip_address,
        blockchain_type="ubuntu",
        env=None,
        metadata=None,
        flist=None,
        entry_point="",
        secret_env=None,
        cpu=1,
        memory=1024,
        disk_size=512,
    ):
        metadata = metadata or {}
        env = env or {}
        secret_env = secret_env or {}
        if not flist:
            raise Exception(f"Flist for {blockchain_type} not found, Please pass it")

        resv_id = deployer.deploy_container(
            identity_name=self.identity_name,
            pool_id=pool_id,
            node_id=node.node_id,
            network_name=network_name,
            ip_address=ip_address,
            flist=flist,
            cpu=cpu,
            memory=memory,
            disk_size=disk_size,
            env=env,
            interactive=False,
            entrypoint=entry_point,
            # log_config=self.log_config,
            public_ipv6=True,
            **metadata,
            solution_uuid=uuid.uuid4().hex,
            secret_env=secret_env,
        )
        success = deployer.wait_workload(resv_id, None, expiry=3)
        if not success:
            raise DeploymentFailed(f"Failed to deploy workload {resv_id}", wid=resv_id)

        j.logger.info(f"succeeded, {resv_id}")
        workload = self.zos.workloads.get(resv_id)
        node = BlockchainNode()
        node.wid = workload.id
        node.node_id = workload.info.node_id
        node.creation_time = workload.info.epoch
        node.state = State.DEPLOYED
        if workload.info.result.data_json:
            data_dict = j.data.serializers.json.loads(workload.info.result.data_json)
            node.ipv4_address = data_dict["ipv4"]
            node.ipv6_address = data_dict["ipv6"]
        else:
            if workload.info.result.state != WorkloadState.Ok:
                node.state = State.ERROR
        self.nodes.append(node)
        self.save()
        return resv_id

    def delete_node(self, wid):
        for node in self.nodes:
            if node.wid == wid:
                node.state = State.DELETED
                self.nodes_count -= 1
                self.save()
                self.zos.workloads.decomission(node.wid)
