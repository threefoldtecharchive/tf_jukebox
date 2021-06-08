# Jukebox installer

This manual will go through setting up an environment for Jukebox.

## Requirements

- tf_jukebox package
- Machine with a domain
- Stellar wallet
  - **activation_wallet**: Used to activate user wallet. (Required asset: XLMs)

## Setup

- Clone the repo https://github.com/threefoldtech/tf_jukebox/ and install the package

```bash
cd tf_jukebox
poetry shell
poetry install
```

- Edit `package.toml` in tf_jukebox package with your domain and email address

  ```bash
  domain = "<your domain>"
  letsencryptemail = "<your email>"
  ```

- Create/Import the required wallets mentioned in the previous requirements through `jsng` shell

  ```bash
  # activation wallet
  activation_wallet = j.clients.stellar.new("activation_wallet") 
  # you can pass the secret if you have a wallet already, and skip the activation step, needs to have xlms for activation
  activation_wallet.secret = <your secret>
  activation_wallet.activate_through_threefold_service()
  activation.save()
  ```

- Add billing package from Admin dashboard.
- Add jukebox package.

```bash
server = j.servers.threebot.get("default")
server.packages.add(path="<repo path>/tf_jukebox/jumpscale/packages/jukebox")1
```

- Start 3Bot server from jsng

```bash
j.servers.threebot.start_default()
```

- Visit the domain you entered in package.toml should redirect you to the main page