from collections import defaultdict

from jumpscale.clients.stellar import TRANSACTION_FEES
from jumpscale.clients.explorer.models import DiskType, Container
from jumpscale.loader import j

from jumpscale.sals.vdc.scheduler import GlobalCapacityChecker


def get_or_create_user_wallet(wallet_name):
    # Create a wallet for the user to be used in extending his pool
    if not j.clients.stellar.find(wallet_name):
        wallet = j.clients.stellar.new(wallet_name)
        try:
            wallet.activate_through_activation_wallet()
        except Exception:
            j.clients.stellar.delete(name=wallet_name)
            raise j.exceptions.JSException("Error on wallet activation")

        try:
            wallet.add_known_trustline("TFT")
        except Exception:
            j.clients.stellar.delete(name=wallet_name)
            raise j.exceptions.JSException(
                f"Failed to add trustlines to wallet {wallet_name}. Any changes made will be reverted."
            )

        wallet.save()
    else:
        wallet = j.clients.stellar.get(wallet_name)
    return wallet


def calculate_payment_from_container_resources(
    cpu, memory, disk_size, duration, farm_id=None, farm_name="freefarm", disk_type=DiskType.HDD
):
    if farm_name and not farm_id:
        zos = j.sals.zos.get()
        farm_id = zos._explorer.farms.get(farm_name=farm_name).id
    empty_container = Container()
    empty_container.capacity.cpu = cpu
    empty_container.capacity.memory = memory
    empty_container.capacity.disk_size = disk_size
    empty_container.capacity.disk_type = disk_type
    cost = j.tools.zos.consumption.cost(empty_container, duration=duration, farm_id=farm_id)
    return cost


def calculate_required_units(cpu, memory, disk_size, duration_seconds, number_of_containers=1):
    cont = Container()
    cont.capacity.cpu = cpu
    cont.capacity.memory = memory
    cont.capacity.disk_size = disk_size
    cont.capacity.disk_type = DiskType.HDD

    cloud_units = {"cu": 0, "su": 0, "ipv4u": 0}
    cont_units = cont.resource_units().cloud_units()
    cloud_units["cu"] += cont_units.cu * number_of_containers
    cloud_units["su"] += cont_units.su * number_of_containers
    cloud_units["cu"] *= duration_seconds
    cloud_units["su"] *= duration_seconds
    return cloud_units


def get_possible_farms(cru, hru, mru, number_of_deployments):
    gcc = GlobalCapacityChecker()
    farm_names = gcc.get_available_farms(
        cru=cru, mru=mru, hru=hru, accessnodes=True, no_deployments=number_of_deployments
    )
    return farm_names


def get_network_ip_range():
    return j.sals.reservation_chatflow.reservation_chatflow.get_ip_range()


def show_payment(bot, amount, wallet_name, expiry=5, description=None):
    wallet = j.clients.stellar.find(wallet_name)
    if not wallet:
        raise j.exceptions.NotFound(f"Couldn't find wallet {wallet_name}")

    balance = wallet.get_balance_by_asset("TFT")
    if balance >= amount:
        if bot:
            result = bot.single_choice(
                f"Do you want to use your existing balance to pay {round(amount,4)} TFT? (This will impact the overall expiration of your deployments)",
                ["Yes", "No"],
                required=True,
            )
            if result == "Yes":
                amount = 0
        else:
            amount = 0
    elif not bot:
        # Not enough funds in prepaid wallet and no bot passed to use to view QRcode
        return False, amount, None

    payment_id, _ = j.sals.billing.submit_payment(
        amount=amount, wallet_name=wallet_name, refund_extra=False, expiry=expiry, description=description
    )
    if amount > 0:
        notes = []
        return j.sals.billing.wait_payment(payment_id, bot=bot, notes=notes), amount, payment_id
    else:
        return True, amount, payment_id


def calculate_funding_amount(identity_name):
    identity = j.core.identity.find(identity_name)
    zos = j.sals.zos.get(identity_name)
    if not identity:
        return 0, None
    total_price = 0
    details = defaultdict(lambda: {})
    deployments = j.sals.jukebox.list(identity_name=identity_name)
    for deployment in deployments:
        price = 0
        if not deployment.auto_extend:
            continue
        if deployment.expiration_date.timestamp() > j.data.time.utcnow().timestamp + 60 * 60 * 24 * 2:
            continue
        cloud_units = calculate_required_units(
            cpu=deployment.cpu,
            memory=deployment.memory,
            disk_size=deployment.disk_size,
            duration_seconds=60 * 60 * 24 * 30,
            number_of_containers=deployment.nodes_count,
        )
        farm_id = zos._explorer.farms.get(farm_name=deployment.farm_name).id
        farm_prices = zos._explorer.farms.get_deal_for_threebot(farm_id, j.core.identity.me.tid)[
            "custom_cloudunits_price"
        ]
        price += zos._explorer.prices.calculate(
            cus=cloud_units["cu"], sus=cloud_units["su"], ipv4us=cloud_units["ipv4u"], farm_prices=farm_prices
        )
        price += TRANSACTION_FEES
        total_price += price
        details[deployment.solution_type.capitalize()][deployment.deployment_name] = round(price, 6)
    return total_price, details


def get_wallet_funding_info(identity_name):
    wallet = j.clients.stellar.find(identity_name)
    if not wallet:
        return {}

    asset = "TFT"
    current_balance = wallet.get_balance_by_asset(asset)
    calculated_funding_amount, amount_detials = calculate_funding_amount(identity_name)
    amount = calculated_funding_amount - current_balance
    amount = 0 if amount < 0 else round(amount, 6)

    qrcode_data = f"TFT:{wallet.address}?amount={amount}&message=topup&sender=me"
    qrcode_image = j.tools.qrcode.base64_get(qrcode_data, scale=3)

    data = {
        "address": wallet.address,
        "balance": {"amount": current_balance, "asset": asset},
        "amount": amount,
        "details": amount_detials,
        "qrcode": qrcode_image,
        "network": wallet.network.value,
    }
    return data


def decrypt_secret_env(deployment):
    secret_env = ""
    secret_env_json = j.sals.reservation_chatflow.deployer.decrypt_metadata(
        deployment.secret_env, deployment.identity_name
    )
    if secret_env_json:
        secret_env = j.data.serializers.json.loads(secret_env_json)
    return secret_env
