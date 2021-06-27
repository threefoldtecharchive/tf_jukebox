# Jukebox Installer

This manual will go through setting up an environment for Jukebox.

## System requirements

```bash
apt-get update
apt-get install -y git python3-venv python3-pip redis-server tmux nginx
pip3 install poetry
```

## Requirements

- tf_jukebox package
- Machine with a domain
- Stellar wallet
  - **activation_wallet**: Used to activate user wallet. (Required asset: XLMs)
  - **init_wallet**: Used to pay for the first hour in the deployment (Required asset: TFTs)

## Setup

- Clone the repo https://github.com/threefoldtech/tf_jukebox/ and install the package

```bash
cd tf_jukebox
poetry shell
poetry install
```

- Edit `package.toml` in tf_jukebox package with your domain and email address

  ```toml
  domain = "<your domain>"
  letsencryptemail = "<your email>"
  ```

- Create/Import the required wallets mentioned in the previous requirements through `jsng` shell

  ```python
  # activation wallet
  activation_wallet = j.clients.stellar.new("activation_wallet")
  # you can pass the secret if you have a wallet already, and skip the activation step, needs to have xlms for activation
  activation_wallet.secret = <your secret>
  activation_wallet.activate_through_threefold_service()
  activation.save()
  # init wallet can be done with the same way as the activation one.
  ```

- Add billing package.

```python
server = j.servers.threebot.get("default")
path = j.sals.fs.parent(j.packages.billing.__file__)
server.packages.add(path=path)
```

- Add jukebox package.

```python
server = j.servers.threebot.get("default")
server.packages.add(path="<repo path>/tf_jukebox/jumpscale/packages/jukebox")
```

- Create an identity.
  **Note:** network can either be `testnet` or `devnet` or empty for mainnet.

```python
identity = j.core.identity.new("default", <identity_name>, <email>, <words>, f"https://explorer.{network}.grid.tf/api/v1")
identity.register()
identity.set_default()
identity.save()
```

- Start 3Bot server from jsng.

```python
j.servers.threebot.start_default()
```

- Visit the domain you entered in package.toml should redirect you to the main page.
