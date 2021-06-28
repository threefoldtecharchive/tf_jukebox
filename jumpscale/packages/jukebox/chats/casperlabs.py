from textwrap import dedent

from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import chatflow_step

from jumpscale.sals.jukebox.jukebox_deploy_chatflow import JukeboxDeployChatflow


class CasperDeploy(JukeboxDeployChatflow):
    title = "CasperLabs"
    SOLUTION_TYPE = "casperlabs"
    QUERY = {"cru": 4, "mru": 16, "hru": 1024}
    ENTERY_POINT = "/start_casper"
    FLIST = "https://hub.grid.tf/ahmed_hanafy_1/arrajput-casper-flist-1.0.flist"
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

    @chatflow_step(title="User configurations")
    def environment(self):
        self.metadata = {
            "form_info": {"chatflow": self.SOLUTION_TYPE, "Solution name": self.deployment_name,},
        }


chat = CasperDeploy
