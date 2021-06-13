from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import chatflow_step
from jumpscale.packages.jukebox.sals.jukebox_deploy_chatflow import JukeboxDeployChatflow


class PresearchDeploy(JukeboxDeployChatflow):
    title = "Presearch"
    SOLUTION_TYPE = "presearch"
    FLIST = "https://hub.grid.tf/waleedhammam.3bot/arrajput-presearch-latest.flist"
    steps = [
        "block_chain_info",
        "choose_farm",
        "set_expiration",
        "get_input",
        "environment",
        "payment",
        "deploy",
        "success",
    ]
    QUERY = {"cru": 1, "sru": 1, "mru": 1}

    @chatflow_step(title="Node Settings")
    def get_input(self):
        form = self.new_form()
        self.deployment_name = form.string_ask("Deployment Name", required=True)
        self.registration_code = form.string_ask("Registration code", required=True)
        form.ask()
        self.deployment_name = self.deployment_name.value
        self.registration_code = self.registration_code.value

    @chatflow_step(title="User configurations")
    def environment(self):
        self.env = {"registration_code": self.registration_code}
        self.metadata = {
            "form_info": {
                "chatflow": self.SOLUTION_TYPE,
                "Solution name": self.deployment_name,
                "number_of_nodes": self.nodes_count,
            },
        }


chat = PresearchDeploy
