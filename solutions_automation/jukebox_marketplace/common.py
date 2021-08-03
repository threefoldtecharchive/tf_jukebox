from solutions_automation.utils.gedispatch import GedisChatBotPatch


class CommonChatBot(GedisChatBotPatch):
    SOLUTION_NAME = "Please enter a name for your Deployment (will be used in listing and deletions in the future)"
    NODES_NUMBER = "Please enter the number of nodes you want to deploy"
    FARM_AUTOMATICALLY = "Do you want to select the farm automatically?"
    EXPIRATION_TIME = "Please enter the solution's expiration time"
    PAYMENT_TYPE = r"Do you want to use your existing balance to pay (.*)$"


    QS_BASE = {
        SOLUTION_NAME: "solution_name",
        NODES_NUMBER: "nodes_number",
        FARM_AUTOMATICALLY: "farm_automatically",
        EXPIRATION_TIME: "expiration_time",
        PAYMENT_TYPE: "paymet_type"
    }
