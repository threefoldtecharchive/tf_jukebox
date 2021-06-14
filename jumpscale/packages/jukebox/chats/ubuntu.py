from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import chatflow_step
from jumpscale.packages.jukebox.sals.jukebox_deploy_chatflow import JukeboxDeployChatflow


class UbuntuDeploy(JukeboxDeployChatflow):
    # HUB_URL = "https://hub.grid.tf/tf-bootable"
    # IMAGES = ["ubuntu-18.04", "ubuntu-20.04"]
    title = "Ubuntu"
    SOLUTION_TYPE = "ubuntu"
    ENTERY_POINT = "/bin/bash /start.sh"
    FLIST = f"https://hub.grid.tf/tf-bootable/3bot-ubuntu-20.04.flist"
    steps = [
        "get_deployment_name",
        "block_chain_info",
        "choose_farm",
        "set_expiration",
        "upload_public_key",
        "environment",
        "payment",
        "deploy",
        "success",
    ]
    QUERY = {"cru": 1, "sru": 1, "mru": 1}

    @chatflow_step(title="User configurations")
    def environment(self):
        self.env = {"pub_key": self.public_key}
        self.metadata = {
            "form_info": {
                "chatflow": self.SOLUTION_TYPE,
                "Solution name": self.deployment_name,
                "number_of_nodes": self.nodes_count,
            },
        }
        self.secret_env = {}


chat = UbuntuDeploy
