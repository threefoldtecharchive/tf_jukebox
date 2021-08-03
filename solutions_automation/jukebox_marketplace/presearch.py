from jumpscale.packages.jukebox.chats.presearch import PresearchDeploy
from solutions_automation.jukebox_marketplace.common import CommonChatBot


class PresearchAutomated(CommonChatBot, PresearchDeploy):
    REGISTER_CODE = r"Register your node and get a registration code from (.*)$"

    QS = {
        REGISTER_CODE: "register_code",
    }