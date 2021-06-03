from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import GedisChatBot, StopChatFlow, chatflow_step
from jumpscale.packages.jukebox.sals import jukebox 
from jumpscale.sals.marketplace import deployer
from jumpscale.sals.marketplace.apps_chatflow import MarketPlaceAppsChatflow
class BlockChainDeploy(MarketPlaceAppsChatflow):
    title = "Blockchain"
    steps = [
        "block_chain_info",
        "choose_farm",
        "set_expiration",
        "upload_public_key",
        "solution_extension",
        "deploy",
        "success",
    ]
    FLIST = "<flist_url>"
    QUERY = {"cru": 1, "sru": 1, "mru": 1}
    def _init(self):
        self.user_info_data = self.user_info()
        self.username = self.user_info_data["username"]
        self.md_show_update("It will take a few seconds to be ready to help you ...")
        # check stellar service
        if not j.clients.stellar.check_stellar_service():
            raise StopChatFlow("Payment service is currently down, try again later")
        wallet_name = f"jukebox_{self.username}"
        if not j.clients.stellar.find(wallet_name):
            # check xlms 
            wname = "activation_wallet"
            if wname in j.clients.stellar.list_all():
                try:
                    w = j.clients.stellar.get(wname)
                    if w.get_balance_by_asset("XLM") < 10:
                        raise StopChatFlow(f"{wname} doesn't have enough XLM to support the deployment.")
                except:
                    raise StopChatFlow(f"Couldn't get the balance for {wname} wallet")
                else:
                    j.logger.info(f"{wname} is funded")
            else:
                j.logger.info(f"This system doesn't have {wname} configured")
                raise StopChatFlow(f"{wname} doesn't exist, please contact support.")
        
        self.wallet = jukebox.get_or_create_user_wallet(wallet_name)
    
    def _blockchain_form(self):
        # location
        # num of nodes
        # node type
        form = self.new_form()
        self.nodes_count = form.int_ask(
            "Please enter the number of nodes you want to deploy",
            required=True,
        )
        self.farm_selection = form.single_choice(
            "Do you wish to select farms automatically?",
            ["Automatically Select Farms", "Manually Select Farms"],
            required=True,
            default="Automatically Select Farms",
        )
        form.ask()
        self.nodes_count = self.nodes_count.value

    @chatflow_step(title="Blockchain Information")
    def block_chain_info(self):
        self._init()
        self._blockchain_form()
    
    @chatflow_step(title="Choose farm"):
    def choose_farm(self):
        if self.farm_selection.value == "Manually Select Farms":
            while True:
                self.no_farms = 1
                gcc = GlobalCapacityChecker()
                available_farms = list(
                    gcc.get_available_farms(ip_version="IPv6", no_nodes=self.no_farms, **QUERY)
                )
                if len(available_farms) < self.no_farms:
                    self.md_show(
                        f"There are not enough farms to deploy {no_nodes} ZDBs each. Click next to try again with smaller number of farms."
                    )
                else:
                    break
            self.farm = self.single_choice(
                    f"Please select {self.no_farms} farms", available_farms, required=True
                )


    @chatflow_step(title="Payment")
    def solution_extension(self):
        self.md_show_update("Extending pool...")
        self.currencies = ["TFT"]

        self.pool_info, self.qr_code = deployer.extend_solution_pool(
            self, self.pool_id, self.expiration, self.currencies, **self.query
        )
        if self.pool_info and self.qr_code:
            # cru = 1 so cus will be = 0
            result = deployer.wait_pool_reservation(self.pool_info.reservation_id, qr_code=self.qr_code, bot=self)
            if not result:
                raise StopChatFlow(f"Waiting for pool payment timedout. pool_id: {self.pool_id}")

    @chatflow_step
    def deploy(self):
        identity_name = ""
        pool_id = jukebox.create_empty_pool(identity_name, self.farm.value)
        owner_tname = self.username
        blockchain_type = "ubuntu"
        env = {"pub_key": self.ssh_keys.value}``
        metadata = {"name": "test_ubuntu", "form_info": {"chatflow": "jukebox", "Solution name": "test_ubuntu"}}
        # extend_pool 
        
