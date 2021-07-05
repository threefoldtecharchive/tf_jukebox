from contextlib import ContextDecorator
import random
from textwrap import dedent

from jumpscale.clients.explorer.models import DiskType
from jumpscale.clients.stellar import TRANSACTION_FEES
from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import GedisChatBot, StopChatFlow, chatflow_step
from jumpscale.sals.marketplace.apps_chatflow import MarketPlaceAppsChatflow

from jumpscale.sals.jukebox import utils
from jumpscale.sals.jukebox.models import State

IDENTITY_PREFIX = "jukebox"
INIT_WALLET = "init_wallet"


class new_jukebox_context(ContextDecorator):
    def __init__(self, instance_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance_name = instance_name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            j.logger.error(f"new_jukebox_context: deployment failed due to exception: {exc_value}")
            j.sals.jukebox.delete(self.instance_name)


class JukeboxDeployChatflow(MarketPlaceAppsChatflow):
    ENTRY_POINT = ""
    DISK_TYPE = DiskType.HDD

    title = "Blockchain"
    steps = [
        "get_deployment_name",
        "block_chain_info",
        "choose_farm",
        "set_expiration",
        "payment",
        "deploy",
        "success",
    ]
    # FLIST = "<flist_url>" # needs to be defined in the child chatflows
    QUERY = {"cru": 1, "mru": 1, "hru": 1}

    def _check_wallet(self, name, asset, limit):
        if name in j.clients.stellar.list_all():
            try:
                w = j.clients.stellar.find(name)
                if w.get_balance_by_asset(asset) < limit:
                    raise StopChatFlow(f"{name} doesn't have enough {asset} to support the deployment.")
            except:
                raise StopChatFlow(f"Couldn't get the balance for {name} wallet")
            else:
                j.logger.info(f"{name} is funded")
        else:
            j.logger.info(f"This system doesn't have {name} configured")
            raise StopChatFlow(f"{name} doesn't exist, please contact support.")

    def _init(self):
        self.env = {}
        self.secret_env = {}
        self.user_info_data = self.user_info()
        # Setup identity and owner
        self.username = self.user_info_data["username"]
        self.owner_tname = j.data.text.removesuffix(self.username, ".3bot")
        self.identity_name = f"{IDENTITY_PREFIX}_{self.owner_tname}"

        self.md_show_update("It will take a few seconds to be ready to help you ...")
        # check stellar service
        if not j.clients.stellar.check_stellar_service():
            raise StopChatFlow("Payment service is currently down, try again later")

        self._check_wallet(name=INIT_WALLET, asset="TFT", limit=50)

        wallet_name = f"jukebox_{self.owner_tname}"
        if not j.clients.stellar.find(wallet_name):
            # check xlms
            self._check_wallet(name="activation_wallet", asset="XLM", limit=10)

        self.wallet = utils.get_or_create_user_wallet(wallet_name)

    @chatflow_step(title="Deployment Name")
    def get_deployment_name(self):
        self._init()
        deployment_names = []
        all_deployments = j.sals.jukebox.list_deployments(
            identity_name=self.identity_name, solution_type=self.SOLUTION_TYPE
        )
        if all_deployments:
            deployment_names = [deployment.deployment_name for deployment in all_deployments]
        self.deployment_name = self.string_ask(
            "Please enter a name for your Deployment (will be used in listing and deletions in the future)",
            required=True,
            not_exist=["Deployment", deployment_names],
            max_length=20,
            is_identifier=True,
        )

    @chatflow_step(title="Blockchain Information")
    def block_chain_info(self):
        # location
        # num of nodes
        # node type
        form = self.new_form()
        self.nodes_count = form.int_ask(
            "Please enter the number of nodes you want to deploy", required=True, min=1, max=50, default=1
        )
        self.farm_selection = form.single_choice(
            "Do you want to select the farm automatically?", ["Yes", "No"], required=True, default="Yes",
        )
        form.ask()
        self.nodes_count = self.nodes_count.value

    @chatflow_step(title="Choose farm")
    def choose_farm(self):
        self.md_show_update("Getting available locations...")
        while True:
            self.no_farms = 1
            available_farms = utils.get_possible_farms(
                self.QUERY["cru"], self.QUERY["hru"], self.QUERY["mru"], self.nodes_count
            )
            available_farms = list(available_farms)
            if len(available_farms) < self.no_farms:
                self.md_show(f"There are not enough farms to deploy {self.nodes_count} nodes.")
            else:
                break
        if self.farm_selection.value == "No":
            self.farm = self.drop_down_choice(f"Please select a farm to deploy on", available_farms, required=True)
        else:
            self.farm = random.choice(available_farms)

    @chatflow_step(title="New Expiration")
    def set_expiration(self):
        self.expiration = j.sals.marketplace.deployer.ask_expiration(
            self, default=j.data.time.utcnow().timestamp + 3600 * 25
        )

    @chatflow_step(title="Payment")
    def payment(self):
        self.currencies = ["TFT"]

        calculated_cost_per_cont = utils.calculate_payment_from_container_resources(
            self.QUERY["cru"],
            self.QUERY["mru"] * 1024,
            self.QUERY["hru"] * 1024,
            duration=self.expiration,
            farm_name=self.farm,
        )

        payment_success, _, self.payment_id = utils.show_payment(
            bot=self,
            amount=calculated_cost_per_cont * self.nodes_count + 2 * TRANSACTION_FEES,
            wallet_name=self.wallet.instance_name,
            expiry=5,
            description=j.data.serializers.json.dumps({"type": "jukebox", "owner": self.owner_tname}),
        )
        if not payment_success:
            self.stop(f"Payment timedout. Please restart.")

    @chatflow_step(title="Deployment")
    def deploy(self):
        deployment = j.sals.jukebox.new(
            solution_type=self.SOLUTION_TYPE,
            deployment_name=self.deployment_name,
            identity_name=self.identity_name,
            nodes_count=self.nodes_count,
        )
        deployment.cpu = self.QUERY["cru"]
        deployment.memory = self.QUERY["mru"] * 1024
        deployment.disk_size = self.QUERY["hru"] * 1024
        deployment.disk_type = self.DISK_TYPE
        deployment.expiration_date = self.expiration + j.data.time.utcnow().timestamp
        deployment.farm_name = self.farm
        deployment.secret_env = j.sals.reservation_chatflow.deployer.encrypt_metadata(
            self.secret_env, self.identity_name
        )
        deployment.save()

        with new_jukebox_context(deployment.instance_name):
            # create pool
            self.md_show_update("Initializing the deployment...")
            init_wallet = j.clients.stellar.find(INIT_WALLET)
            # Calculate required units from query for one hour
            one_hour_cloud_units = utils.calculate_required_units(
                cpu=self.QUERY["cru"],
                memory=self.QUERY["mru"] * 1024,
                disk_size=self.QUERY["hru"] * 1024,
                duration_seconds=60 * 60,
                number_of_containers=self.nodes_count,
            )

            # TODO to be done for all farms to have a list of pool_ids, the following is per one farm
            try:
                pool_rev_id = deployment.create_capacity_pool(
                    init_wallet, cu=one_hour_cloud_units["cu"], su=one_hour_cloud_units["su"], ipv4us=0, farm=self.farm
                )

                self.network_name = f"jukebox_{self.owner_tname}_{pool_rev_id}"

                self.md_show_update("Deploying network...")
                # Create network
                _, self.wg_quick = deployment.deploy_network(network_name=self.network_name)

                # Get possible nodes,ip_addresses then spawn deployment of container in gevent
                self.md_show_update("Deploying containers...")
                deployment.deploy_all_containers(
                    number_of_deployments=self.nodes_count,
                    network_name=self.network_name,
                    env=self.env,
                    metadata=self.metadata,
                    flist=self.FLIST,
                    entry_point=self.ENTRY_POINT,
                    secret_env=self.secret_env,
                )
                deployment._update_state(State.DEPLOYED)

                # Extend pool with the remain expiration
                cloud_units = utils.calculate_required_units(
                    cpu=self.QUERY["cru"],
                    memory=self.QUERY["mru"] * 1024,
                    disk_size=self.QUERY["hru"] * 1024,
                    duration_seconds=self.expiration - 60 * 60,
                    number_of_containers=self.nodes_count,
                )
                deployment.extend_capacity_pool(
                    pool_id=deployment.pool_ids[0],
                    wallet=self.wallet,
                    cu=cloud_units["cu"],
                    su=cloud_units["su"],
                    ipv4us=0,
                )

            except Exception as e:
                j.logger.exception(f"Failed to deploy", exception=e)
                j.sals.billing.issue_refund(self.payment_id)
                self.stop("Failed to deploy")

        # take back one hour payment to the init_wallet.
        calculated_cost_per_cont = utils.calculate_payment_from_container_resources(
            self.QUERY["cru"],
            self.QUERY["mru"] * 1024,
            self.QUERY["hru"] * 1024,
            duration=60 * 60,
            farm_name=self.farm,
        )
        amount_to_refund = round(calculated_cost_per_cont * self.nodes_count + TRANSACTION_FEES, 6)
        asset = self.wallet._get_asset("TFT")
        self.wallet.transfer(init_wallet.address, amount_to_refund, asset=f"{asset.code}:{asset.issuer}")

    @chatflow_step(title="Success", disable_previous=True, final_step=True)
    def success(self):
        message = f"""\
        # You have deployed {self.nodes_count} nodes of {self.SOLUTION_TYPE}
        <br />\n
        """
        self.md_show(dedent(message), md=True)
