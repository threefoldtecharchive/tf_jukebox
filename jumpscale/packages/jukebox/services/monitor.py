from jumpscale.sals.jukebox.models import State
import gevent
from jumpscale.loader import j
from jumpscale.sals.zos.billing import InsufficientFunds
from jumpscale.tools.servicemanager.servicemanager import BackgroundService

from jumpscale.packages.admin.services.notifier import MAIL_QUEUE


class MonitorDeployments(BackgroundService):
    def __init__(self, interval=60 * 60 * 12, *args, **kwargs):
        """
        Monitor deployed nodes service
        """
        super().__init__(interval, *args, **kwargs)

    def job(self):
        j.logger.info("Starting monitoring deployments...")
        for deployment_instance_name in j.sals.jukebox.list_all():
            deployment = j.sals.jukebox.find(deployment_instance_name)
            if deployment.state == State.EXPIRED:
                continue
            self._check_down_containers(deployment)
            self._auto_extend_pool(deployment)

            gevent.sleep(1)

        j.logger.info("All deployments are monitored")

    def _check_down_containers(self, deployment):
        user = j.data.text.removeprefix(deployment.identity_name, "jukebox_")

        number_of_deployed = len([node for node in deployment.nodes if node.state == State.DEPLOYED])
        number_of_down_deployment = deployment.nodes_count - number_of_deployed
        if number_of_down_deployment > 0:
            j.logger.warning(
                f"Deployment: {deployment.deployment_name}, Deployment type: {deployment.solution_type}, owner: {user} has {number_of_down_deployment} node(s) went down"
            )
            message = (
                f"Dear {user},\n\n"
                f"{number_of_down_deployment} node(s) of {deployment.solution_type} went down for your deployment {deployment.deployment_name}. The system will try to bring it back, Please refer for your jukebox dashboard for more information."
            )
            subject = "Jukebox Nodes Down"
            self._send_email(deployment.identity_name, subject, message)

    def _auto_extend_pool(self, deployment):
        identity_name = deployment.identity_name
        user = j.data.text.removeprefix(identity_name, "jukebox_")
        pool_id = deployment.pool_ids[0]
        zos = j.sals.zos.get(identity_name)

        j.logger.info(f"Auto extend pool {pool_id}")

        deployment_name = deployment.deployment_name
        deployment_type = deployment.solution_type
        auto_extend = deployment.auto_extend

        pool = zos.pools.get(pool_id)
        expiration = pool.empty_at
        if expiration > j.data.time.utcnow().timestamp + 60 * 60 * 24 * 2.5:
            return

        if not auto_extend:
            j.logger.error(
                f"Deployment: {deployment_name}, Deployment type: {deployment_type}, owner: {user} is about to expire"
            )
            subject = "Jukebox Deployment Expiry"
            message = (
                f"Dear {user},\n\n"
                f"Your pool with ID {pool_id} of {deployment_type} for deployment {deployment_name} is about to expire"
                "please enable the auto extend option for this deployment and fund the wallet if needed"
            )
            self._send_email(identity_name, subject, message)
            return

        wallet = j.clients.stellar.find(identity_name)
        if not wallet:
            error_msg = f"Failed to get user {identity_name} wallet"
            j.logger.critical(error_msg)
            alert = j.tools.alerthandler.alert_raise(app_name="jukebox", message=error_msg, alert_type="exception")
            subject = "Jukebox Auto Extend Pools Failed"
            message = (
                f"Dear {user},\n\n"
                f"Your pool with ID {pool_id} of {deployment_type} for deployment {deployment_name} is about to expire and we are not "
                "able to extend it automatically, "
                f"please contact our support team with alert ID {alert.id}"
            )
            self._send_email(identity_name, subject, message)
            return
        try:
            deployment.extend()
            subject = "Jukebox Auto Extend Pools"
            message = f"Dear {user},\n\nYour pool with ID {pool_id} of {deployment_type} for deployment {deployment_name} has been extended successfully."
            self._send_email(identity_name, subject, message)
        except InsufficientFunds:
            subject = "Jukebox Auto Extend Pools Failed"
            message = (
                f"Dear {user},\n\n"
                f"Your pool with ID {pool_id} of {deployment_type} for deployment {deployment_name} is about to expire and we are not "
                "able to extend it automatically, "
                "please check the fund in your wallets and extend it manually "
                "or contact our support team."
            )
            self._send_email(identity_name, subject, message)

    def _send_email(self, identity_name, subject, message):
        identity = j.core.identity.find(identity_name)
        recipient_email = identity.email.replace("_jukebox@", "@")
        mail_config = j.core.config.get("EMAIL_SERVER_CONFIG")
        sender = mail_config.get("sender", "support@jukebox.grid.tf")
        mail_info = {"recipients_emails": [recipient_email], "sender": sender, "subject": subject, "message": message}
        j.core.db.rpush(MAIL_QUEUE, j.data.serializers.json.dumps(mail_info))


service = MonitorDeployments()
