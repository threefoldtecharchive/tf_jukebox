from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import chatflow_step
from jumpscale.packages.jukebox.sals.jukebox_deploy_chatflow import JukeboxDeployChatflow


class DigibyteDeploy(JukeboxDeployChatflow):
    title = "Digibyte"
    SOLUTION_TYPE = "digibyte"
    FLIST = f"https://hub.grid.tf/ashraf.3bot/arrajput-digibyte-2.7.flist"
    steps = [
        "block_chain_info",
        "choose_farm",
        "set_expiration",
        "upload_public_key",
        "environment",
       # TODO:  "ask_username_password",
        "payment",
        "deploy",
        "success",
    ]
    QUERY = {"cru": 1, "sru": 1, "mru": 1}

    @chatflow_step(title="RPC Credentials")
    def rpc_credentials(slef):
        form = self.new_form()
        self.rpc_username = form.string_ask("RPC Username", required=True)
        self.rpc_password = form.string_ask("RPC Password", required=True)
        form.ask()
        self.rpc_username = self.rpc_username.value
        self.rpc_password = self.rpc_password.value
    @chatflow_step(title="User configurations")
    def environment(self):
        self.env = {
            "pub_key": self.public_key,
            "rpcuser": self.rpc_username,
            "rpcpasswd": self.rpc_password
            }
        self.metadata = {
            "form_info": {
                "chatflow": self.SOLUTION_TYPE,
                "Solution name": "test_node",
                "number_of_nodes": self.nodes_count,
            },
        }


chat = DigibyteDeploy
