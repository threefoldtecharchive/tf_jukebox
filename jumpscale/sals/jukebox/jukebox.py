from collections import defaultdict
from time import sleep
import uuid

import gevent
from jumpscale.clients.explorer.models import DiskType, State as WorkloadState, NextAction
from jumpscale.core.base import Base, fields
from jumpscale.core.base import Base, fields
from jumpscale.loader import j
from jumpscale.sals.reservation_chatflow import DeploymentFailed, deployer

from jumpscale.sals.jukebox import utils
from jumpscale.sals.jukebox.models import BlockchainNode, State
from jumpscale.sals.vdc.scheduler import Scheduler
from gevent.lock import BoundedSemaphore


CURRENCIES = ["TFT"]
IDENTITY_PREFIX = "jukebox"
POOL_EXPIRATION_VALUE = 9223372036854775807


def on_exception(greenlet_thread):
    """Callback to handle exception raised by service greenlet_thread
    Arguments:
        greenlet_thread (Greenlet): greenlet_thread object
    """
    message = f"raised an exception: {greenlet_thread.exception}"
    j.tools.alerthandler.alert_raise(app_name="jukebox", message=message, alert_type="exception")
    j.logger.error(message)


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
    secret_env = fields.String()
    __lock = BoundedSemaphore(1)
    _zos = None

    @property
    def zos(self):
        if self._zos is None:
            self._zos = j.sals.zos.get(self.identity_name)
        return self._zos

    def lock_deployment(function):
        def wrapper(self, *args, **kwargs):
            self.__lock.acquire()
            try:
                result = function(self, *args, **kwargs)
            except Exception as e:
                raise e
            finally:
                self.__lock.release()

            return result

        return wrapper

    def wait_pool_payment(self, reservation_id, exp=5):
        j.logger.info(f"waiting pool payment for reservation_id: {reservation_id}")
        expiration = j.data.time.now().timestamp + exp * 60
        while j.data.time.get().timestamp < expiration:
            payment_info = self.zos.pools.get_payment_info(reservation_id)
            if payment_info.paid and payment_info.released:
                return True
            gevent.sleep(1)
        return False

    def create_capacity_pool(self, wallet, cu=100, su=100, ipv4us=0, farm="freefarm"):
        payment_detail = self.zos.pools.create(cu=cu, su=su, ipv4us=ipv4us, farm=farm)
        # wallet = j.clients.stellar.get(wallet)
        self.zos.billing.payout_farmers(wallet, payment_detail)
        if not self.wait_pool_payment(payment_detail.reservation_id):
            raise DeploymentFailed(f"Failed to pay to pool {payment_detail.reservation_id}")

        # TODO add in QR code with payment total for users
        self.pool_ids.append(payment_detail.reservation_id)
        self.save()
        return payment_detail.reservation_id

    def extend_capacity_pool(self, pool_id, wallet, cu=100, su=100, ipv4us=0):
        payment_detail = self.zos.pools.extend(pool_id=pool_id, cu=cu, su=su, ipv4us=ipv4us)
        self.zos.billing.payout_farmers(wallet, payment_detail)
        if not self.wait_pool_payment(payment_detail.reservation_id):
            raise DeploymentFailed(f"Failed to pay to pool {payment_detail.reservation_id}")
        return payment_detail.reservation_id

    def get_container_ip(self, network_name, node, excluded_ips=None):
        excluded_ips = excluded_ips or []
        excluded_nodes = j.core.db.get("excluded_nodes")
        if not excluded_nodes:
            excluded_nodes = []
        else:
            excluded_nodes = j.data.serializers.json.loads(excluded_nodes.decode())

        try:
            network_view = deployer.get_network_view(network_name, identity_name=self.identity_name)
            network_view_copy = network_view.copy()
            result = deployer.add_network_node(
                network_view.name,
                node,
                self.pool_ids[0],
                network_view_copy,
                identity_name=self.identity_name,
                owner=self.identity_name,
            )

            if result:
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

    def deploy_network(self, network_name, ip_range=None):
        ip_range = ip_range or utils.get_network_ip_range()
        scheduler = Scheduler(pool_id=self.pool_ids[0])
        network_success = False
        ip_version = "IPv4"
        for access_node in scheduler.nodes_by_capacity(ip_version=ip_version, accessnodes=True):
            j.logger.info(f"Deploying network on node {access_node.node_id}")
            network_success = True
            result = deployer.deploy_network(
                network_name, access_node, ip_range, ip_version, self.pool_ids[0], self.identity_name
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
                    f"saving wireguard config to {j.core.dirs.CFGDIR}/jukebox/wireguard/{self.identity_name}/{network_name}.conf"
                )
                wg_quick = result["wg"]
                j.sals.fs.mkdirs(f"{j.core.dirs.CFGDIR}/jukebox/wireguard/{self.identity_name}")
                j.sals.fs.write_file(
                    f"{j.core.dirs.CFGDIR}/jukebox/wireguard/{self.identity_name}/{network_name}.conf", wg_quick
                )
                return True, wg_quick

    def deploy_all_containers(
        self, number_of_deployments, network_name, env=None, secret_env=None, metadata=None, flist=None, entry_point="",
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
        scheduler = Scheduler(farm_name=self.farm_name)
        scheduler.exclude_nodes(*excluded_nodes)
        deployment_threads = []
        i = 0
        while i < number_of_deployments:
            # for each node check how many containers can be deployed on it, and based on that assign that node for X deployments
            node = next(scheduler.nodes_by_capacity(cru=self.cpu, sru=self.disk_size / 1024, mru=self.memory / 1024))

            excluded_ips = used_ip_addresses.get(node.node_id, [])
            ip_address = self.get_container_ip(network_name, node, excluded_ips)
            if not ip_address:
                continue

            used_ip_addresses[node.node_id].append(ip_address)

            # START SPAWN
            thread = gevent.spawn(
                self.deploy_container, network_name, node, ip_address, env, metadata, flist, entry_point, secret_env,
            )
            thread.link_exception(on_exception)
            deployment_threads.append(thread)
            i += 1
            # END SPAWN
        # TODO check resv ids success/failure, if resv failed retry on same node
        gevent.joinall(deployment_threads)

    def deploy_container(
        self, network_name, node, ip_address, env=None, metadata=None, flist=None, entry_point="", secret_env=None,
    ):
        metadata = metadata or {}
        env = env or {}
        secret_env = secret_env or {}
        if not flist:
            raise Exception(f"Flist for {self.solution_type} not found, Please pass it")

        resv_id = deployer.deploy_container(
            identity_name=self.identity_name,
            pool_id=self.pool_ids[0],
            node_id=node.node_id,
            network_name=network_name,
            ip_address=ip_address,
            flist=flist,
            cpu=self.cpu,
            memory=self.memory,
            disk_size=self.disk_size,
            env=env,
            interactive=False,
            entrypoint=entry_point,
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

    @lock_deployment
    def delete_node(self, wid):
        for node in self.nodes:
            if node.wid == wid and node.state != State.DELETED:
                node.state = State.DELETED
                self.nodes_count -= 1
                self.save()
                self.zos.workloads.decomission(node.wid)

    def deploy_from_workload(self, number_of_containers, final_state=State.DEPLOYED, redeploy=False):
        self._update_state(State.DEPLOYING)
        wid = self.nodes[0].wid
        workload = self.zos.workloads.get(wid)
        network_name = f"{self.identity_name}_{self.pool_ids[0]}"
        secret_env = j.sals.reservation_chatflow.deployer.decrypt_metadata(self.secret_env, self.identity_name)
        secret_env_dict = j.data.serializers.json.loads(secret_env)
        metadata = j.sals.reservation_chatflow.deployer.decrypt_metadata(workload.info.metadata, self.identity_name)
        metadata_dict = j.data.serializers.json.loads(metadata)
        metadata_dict.pop("solution_uuid")

        self.deploy_all_containers(
            number_of_containers,
            network_name=network_name,
            env=workload.environment,
            secret_env=secret_env_dict,
            metadata=metadata_dict,
            flist=workload.flist,
            entry_point=workload.entrypoint,
        )
        if not redeploy:
            self._update_nodes_count(self.nodes_count + number_of_containers)
        self._update_state(final_state)

    def redeploy_containers(self, number_of_containers):
        self.deploy_from_workload(number_of_containers, final_state=State.DEPLOYING, redeploy=True)

        number_deployed_containers = len(self.nodes) - self.nodes_count
        number_failed_containers = number_of_containers - number_deployed_containers
        nodes = self.nodes.copy()
        for node in self.nodes:
            if not number_deployed_containers:
                break
            if node.state == State.ERROR:
                nodes.remove(node)
                number_deployed_containers -= 1

        self._update_nodes(nodes)
        if number_failed_containers:
            self._update_state(State.ERROR)  # not all container will be redeployed successfully
        else:
            self._update_state(State.DEPLOYED)

    @lock_deployment
    def _update_state(self, new_state):
        self.state = new_state
        self.save()

    @lock_deployment
    def _update_nodes(self, new_nodes):
        self.nodes = new_nodes
        self.save()

    @lock_deployment
    def _update_nodes_count(self, new_count):
        self.nodes_count = new_count
        self.save()

    @lock_deployment
    def _update_deployment(self):
        pool = self.zos.pools.get(self.pool_ids[0])
        if pool.empty_at == POOL_EXPIRATION_VALUE and pool.cus == 0:  # Also add check on sus if VMs are used
            self.state = State.EXPIRED
        elif pool.empty_at == POOL_EXPIRATION_VALUE:
            self.state = State.ERROR
        else:
            self.expiration_date = pool.empty_at
        for node in self.nodes:
            workload = self.zos.workloads.get(node.wid)
            if workload.info.next_action == NextAction.DEPLOY or node.state in [State.DELETED, State.EXPIRED]:
                continue

            elif pool.empty_at == POOL_EXPIRATION_VALUE and pool.cus == 0:  # Also add check on sus if VMs are used
                node.state = State.EXPIRED
            else:
                node.state = State.ERROR
        self.save()
