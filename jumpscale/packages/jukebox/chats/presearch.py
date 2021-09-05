from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import chatflow_step
from jumpscale.sals.jukebox.jukebox_deploy_chatflow import JukeboxDeployChatflow
from textwrap import dedent


class PresearchDeploy(JukeboxDeployChatflow):
    title = "Presearch"
    SOLUTION_TYPE = "presearch"
    FLIST = "https://hub.grid.tf/arehman/arrajput-presearch-flist-latest.flist"
    ENTERY_POINT = "/start_presearch.sh"
    steps = [
        "get_deployment_name",
        "block_chain_info",
        "choose_farm",
        "set_expiration",
        "environment",
        "payment",
        "deploy",
        "success",
    ]
    QUERY = {"cru": 1, "mru": 1, "hru": 3}

    @chatflow_step(title="Registration Code")
    def environment(self):
        self.registration_code = self.string_ask("Register your node and get a registration code from <a href=https://nodes.presearch.org/dashboard>Presearch</a>", required=True, html=True) 
        self.secret_env = {"REGISTRATION_CODE": self.registration_code}
        self.metadata = {
            "form_info": {"chatflow": self.SOLUTION_TYPE, "Solution name": self.deployment_name,},
        }


chat = PresearchDeploy
