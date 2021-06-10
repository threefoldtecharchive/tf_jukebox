from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import chatflow_step
from jumpscale.packages.jukebox.sals.jukebox_deploy_chatflow import JukeboxDeployChatflow


class DigibyteDeploy(JukeboxDeployChatflow):
    title = "Digibyte"
    SOLUTION_TYPE = "digibyte"
    FLIST = "https://hub.grid.tf/ashraf.3bot/arrajput-digibyte-2.7.flist"
    steps = [
        "get_deployment_name",
        "block_chain_info",
        "choose_farm",
        "set_expiration",
        "upload_public_key",
        "rpc_credentials",
        "environment",
        "payment",
        "deploy",
        "success",
    ]
    QUERY = {"cru": 1, "sru": 1, "mru": 1}
    ENTERY_POINT = "/start_dgb.sh"
    @chatflow_step(title="RPC Credentials")
    def rpc_credentials(self):
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
            }
        self.secret_env = {
            "rpcuser": self.rpc_username,
            "rpcpasswd": self.rpc_password
        }
        self.metadata = {
            "form_info": {
                "chatflow": self.SOLUTION_TYPE,
                "Solution name": self.deployment_name,
                "number_of_nodes": self.nodes_count,
            },
        }


chat = DigibyteDeploy
