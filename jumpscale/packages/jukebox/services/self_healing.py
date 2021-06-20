import gevent
from jumpscale.loader import j
from jumpscale.tools.servicemanager.servicemanager import BackgroundService

from jumpscale.sals.jukebox.models import State


class SelfHealing(BackgroundService):
    def __init__(self, interval=60 * 60 * 2, *args, **kwargs):
        """
        self healing for deployments' workloads.
        """
        super().__init__(interval, *args, **kwargs)

    def job(self):
        j.logger.info("Starting self healing for deployments...")
        for deployment_instance_name in j.sals.jukebox.list_all():
            deployment = j.sals.jukebox.find(deployment_instance_name)
            if deployment.state in [State.DEPLOYING, State.DELETED, State.EXPIRED]:
                continue
            errored_workloads = 0
            for node in deployment.nodes:
                if node.state == State.ERROR:
                    errored_workloads += 1
            deployment.redeploy_containers(errored_workloads)
            gevent.sleep(0.1)

        j.logger.info("Self healing is done")


service = SelfHealing()
