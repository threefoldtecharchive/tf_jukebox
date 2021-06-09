import gevent
from jumpscale.loader import j
from jumpscale.sals.zos.billing import InsufficientFunds
from jumpscale.tools.servicemanager.servicemanager import BackgroundService

from jumpscale.packages.admin.services.notifier import MAIL_QUEUE
from jumpscale.packages.jukebox.sals.jukebox import list_deployments


class MonitorDeployments(BackgroundService):
    def __init__(self, interval=60 * 60 * 12, *args, **kwargs):
        """
        Monitor deployed nodes service
        """
        super().__init__(interval, *args, **kwargs)

    def job(self):
        j.logger.info("Starting monitoring deployments...")
        for identity_name in j.core.identity.list_all():
            if not identity_name.startswith("jukebox"):
                continue
            all_deployments = list_deployments(identity_name)
            self._check_down_containers_and_auto_extend_pools(all_deployments, identity_name)

        j.logger.info("All deployments are monitored")

    def _check_down_containers_and_auto_extend_pools(self, all_deployments, identity_name):
        user = j.data.text.removeprefix(identity_name, "jukebox_")
        for deployment_type, deployments in all_deployments.items():
            for deployment in deployments:
                number_of_down_deployment = deployment["metadata"]["number_of_nodes"] - len(deployment["workloads"])
                if number_of_down_deployment > 0:
                    j.logger.warning(
                        f"Deployment: {deployment['name']}, Deployment type: {deployment_type}, owner: {user} has 1 node(s) went down"
                    )
                    message = (
                        f"Dear {user},\n\n"
                        f"{number_of_down_deployment} node(s) of {deployment_type} went down for your deployment {deployment['name']}."
                    )
                    subject = "Jukebox Nodes Down"
                    self._send_email(identity_name, subject, message)
                self._auto_extend_pool(
                    pool_id=deployment["workloads"][0]["info"]["pool_id"],
                    identity_name=identity_name,
                    deployment_name=deployment["name"],
                    deployment_type=deployment_type,
                    user=user,
                    auto_extend=deployment["auto_extend"],
                )
                gevent.sleep(1)

    def _auto_extend_pool(self, pool_id, identity_name, deployment_name, deployment_type, user, auto_extend=False):
        j.logger.info(f"Auto extend pool {pool_id}")
        zos = j.sals.zos.get(identity_name)
        pool = zos.pools.get(pool_id)
        expiration = pool.empty_at
        if expiration > j.data.time.utcnow().timestamp + 60 * 60 * 24 * 2:
            return

        if not auto_extend:
            j.logger.error(
                f"Deployment: {deployment_name}, Deployment type: {deployment_type}, owner: {user} is about to expire"
            )
            subject = "Jukebox Deployment Expiry"
            message = (
                f"Dear {user},\n\n"
                f"Your pool with ID {pool_id} of {deployment_type} for deployment {deployment_name} is about to expire"
                "please extend it manually or enable the auto extend option for this deployment"
            )
            self._send_email(identity_name, subject, message)
            return

        needed_cu = pool.active_cu * 60 * 60 * 24 * 14
        needed_su = pool.active_su * 60 * 60 * 24 * 14
        pool_info = zos.pools.extend(pool_id, cu=needed_cu, su=needed_su, ipv4us=0)
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
            zos.billing.payout_farmers(wallet, pool_info)
            subject = "Jukebox Auto Extend Pools"
            message = f"Dear {user},\n\nYour pool with ID {pool_id} of {deployment_type} for deployment {deployment_name} has been extended successfully."
            self._send_email(identity_name, subject, message)
        except InsufficientFunds:
            j.logger.error(f"Failed to pay for pool {pool_info.reservation_id}")
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
        sender = mail_config.get("username")
        mail_info = {
            "recipients_emails": [recipient_email],
            "sender": sender,
            "subject": subject,
            "message": message,
        }
        j.core.db.rpush(MAIL_QUEUE, j.data.serializers.json.dumps(mail_info))


service = MonitorDeployments()
