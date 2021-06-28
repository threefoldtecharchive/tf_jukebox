from textwrap import dedent

from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import chatflow_step

from jumpscale.sals.jukebox.jukebox_deploy_chatflow import JukeboxDeployChatflow


class CasperDeploy(JukeboxDeployChatflow):
    title = "CasperLabs"
    SOLUTION_TYPE = "casperlabs"
    QUERY = {"cru": 1, "sru": 1, "mru": 1}
    ENTERY_POINT = "/start_casper"
    FLIST = "https://hub.grid.tf/arehman/arrajput-casper-flist-1.0.flist"
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
