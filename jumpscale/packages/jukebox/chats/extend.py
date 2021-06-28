from textwrap import dedent

from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import chatflow_step

from jumpscale.sals.jukebox.jukebox_deploy_chatflow import JukeboxDeployChatflow
from jumpscale.sals.jukebox import utils


class Extend(JukeboxDeployChatflow):
    title = "Extend Deployment"
    steps = [
        "number_of_nodes",
        "payment",
        "deploy",
        "success",
    ]

    def _init(self):
        super()._init()
        self.deployment_name = self.kwargs["deployment_name"]
        self.SOLUTION_TYPE = self.kwargs["solution_type"]
        self.deployment = j.sals.jukebox.find(
            deployment_name=self.deployment_name, solution_type=self.SOLUTION_TYPE, identity_name=self.identity_name
        )
        self.QUERY = {
            "cru": int(self.deployment.cpu),
            "mru": int(self.deployment.memory / 1024),
            "hru": int(self.deployment.disk_size / 1024),
        }
        self.farm = self.deployment.farm_name
        self.expiration = self.deployment.expiration_date.timestamp() - j.data.time.utcnow().timestamp

    @chatflow_step(title="Number of Nodes")
    def number_of_nodes(self):
        self._init()
        self.nodes_count = self.int_ask("Please enter the number of nodes you want to deploy", required=True)
        self.nodes_count = self.nodes_count
        self.no_farms = 1
        available_farms = utils.get_possible_farms(
            self.QUERY["cru"], self.QUERY["hru"], self.QUERY["mru"], self.nodes_count
        )
        available_farms = list(available_farms)
        if len(available_farms) < self.no_farms:
            self.stop("There is not enough capacity to deploy your nodes.")

    @chatflow_step(title="Deploy")
    def deploy(self):
        self.md_show_update("Deploying...")
        cloud_units = utils.calculate_required_units(
            cpu=self.QUERY["cru"],
            memory=self.QUERY["mru"] * 1024,
            disk_size=self.QUERY["hru"] * 1024,
            duration_seconds=self.expiration,
            number_of_containers=self.nodes_count,
        )
        self.deployment.extend_capacity_pool(
            pool_id=self.deployment.pool_ids[0], wallet=self.wallet, cu=cloud_units["cu"], su=cloud_units["su"]
        )
        self.deployment.deploy_from_workload(self.nodes_count, redeploy=False)

    @chatflow_step(title="Success", disable_previous=True, final_step=True)
    def success(self):
        message = f"""\
        # You Extended {self.nodes_count} nodes of {self.SOLUTION_TYPE}
        """
        self.md_show(dedent(message), md=True)


chat = Extend
