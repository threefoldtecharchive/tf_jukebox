from jumpscale.clients.explorer.models import NextAction
from jumpscale.core.base import StoredFactory
from jumpscale.loader import j

from jumpscale.sals.jukebox.jukebox import JukeboxDeployment
from jumpscale.sals.jukebox.models import State

BLOCKCHAIN_INSTANCE_FORMAT = "{}_{}_{}"


class BlockchainStoredFactory(StoredFactory):
    def new(self, solution_type, deployment_name, identity_name, nodes_count):
        identity_name = j.data.text.removesuffix(identity_name, ".3bot")
        instance_name = BLOCKCHAIN_INSTANCE_FORMAT.format(solution_type, identity_name, deployment_name)
        return super().new(
            instance_name,
            solution_type=solution_type,
            identity_name=identity_name,
            deployment_name=deployment_name,
            nodes_count=nodes_count,
        )

    def find(self, name=None, solution_type=None, identity_name=None, deployment_name=None):
        identity_name = j.data.text.removesuffix(identity_name, ".3bot") if identity_name else None
        instance_name = name or BLOCKCHAIN_INSTANCE_FORMAT.format(solution_type, identity_name, deployment_name)
        instance = super().find(instance_name)
        if not instance:
            return
        if identity_name and instance.identity_name != identity_name:
            return
        return instance

    def list(self, identity_name):
        identity_name = j.data.text.removesuffix(identity_name, ".3bot")
        _, _, instances = self.find_many(identity_name=identity_name)
        return instances

    def list_deployments(self, identity_name, solution_type):
        identity_name = j.data.text.removesuffix(identity_name, ".3bot")
        instances = self.list(identity_name=identity_name)
        deployments = []
        for instance in instances:
            if instance.solution_type == solution_type:
                deployments.append(instance)
        return deployments

    def delete(self, name):
        deployment = self.find(name)
        if deployment:
            j.logger.info(f"Deleting deployment {deployment.instance_name}")
            self.cleanup(deployment)
        return super().delete(name)

    def cleanup(self, deployment):
        for blockchain_node in deployment.nodes:
            deployment.zos.workloads.decomission(blockchain_node.wid)
            blockchain_node.state = State.DELETED
            deployment.save()


BCNodeFACTORY = BlockchainStoredFactory(JukeboxDeployment)
BCNodeFACTORY.always_reload = True


def export_module_as():
    return BCNodeFACTORY
