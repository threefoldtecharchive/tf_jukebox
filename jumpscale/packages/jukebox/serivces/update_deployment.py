import gevent
from jumpscale.clients.explorer.models import NextAction
from jumpscale.loader import j
from jumpscale.tools.servicemanager.servicemanager import BackgroundService

from jumpscale.sals.jukebox.models import State


class UpdateDeployment(BackgroundService):
    def __init__(self, interval=60 * 60 * 12, *args, **kwargs):
        """
        Update deployments' objects.
        """
        super().__init__(interval, *args, **kwargs)

    def job(self):
        j.logger.info("Starting updating deployments...")
        for deployment_instance_name in j.sals.jukebox.list_all():
            deployment = j.sals.jukebox.find(deployment_instance_name)
            self._update_deployment(deployment)
            gevent.sleep(0.1)

        j.logger.info("All deployments are updated")

    def _update_deployment(self, deployment):
        pool = deployment.zos.pools.get(deployment.pool_ids[0])
        if pool.empty_at == 9223372036854775807:
            deployment.state = State.EXPIRED
        else:
            deployment.expiration_date = pool.empty_at
        for node in deployment.nodes:
            workload = deployment.zos.workloads.get(node.wid)
            if workload.info.next_action == NextAction.DEPLOY or node.state in [State.DELETED, State.EXPIRED]:
                continue

            elif pool.empty_at == 9223372036854775807:
                node.state = State.EXPIRED
            else:
                node.state = State.ERROR
        deployment.save()


service = UpdateDeployment()
