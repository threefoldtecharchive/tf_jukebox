from solutions_automation.jukebox_marketplace.dash import DashAutomated
from solutions_automation.jukebox_marketplace.digibyte import DigibyteAutomated
from solutions_automation.jukebox_marketplace.presearch import PresearchAutomated

from jumpscale.loader import j


def deploy_dash(solution_name, expiration_time, nodes_number=1, farm_automatically="Yes", paymet_type="No", debug="Yes", ):
    return DashAutomated(expiration_time=expiration_time, solution_name=solution_name, nodes_number=nodes_number,farm_automatically=farm_automatically, paymet_type=paymet_type, debug=debug)

def deploy_digibyte(solution_name, expiration_time, nodes_number=1, farm_automatically="Yes", paymet_type="No", debug="Yes", ):
    return DigibyteAutomated(expiration_time=expiration_time, solution_name=solution_name, nodes_number=nodes_number,farm_automatically=farm_automatically, paymet_type=paymet_type, debug=debug)

def deploy_presearch(solution_name, expiration_time, register_code, nodes_number=1, farm_automatically="Yes", paymet_type="No", debug="Yes", ):
    return PresearchAutomated(expiration_time=expiration_time, solution_name=solution_name, register_code=register_code, nodes_number=nodes_number,farm_automatically=farm_automatically, paymet_type=paymet_type, debug=debug)
