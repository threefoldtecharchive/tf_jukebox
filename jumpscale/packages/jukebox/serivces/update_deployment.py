import gevent
from jumpscale.clients.explorer.models import NextAction
from jumpscale.loader import j
from jumpscale.tools.servicemanager.servicemanager import BackgroundService

from jumpscale.sals.jukebox.models import State

POOL_EXPIRATION_VALUE = 9223372036854775807


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
            if deployment.state == State.DEPLOYING:
                continue
            deployment._update_deployment()
            gevent.sleep(0.1)

        j.logger.info("All deployments are updated")


service = UpdateDeployment()
