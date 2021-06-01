import datetime
import requests
import nacl
import base64
import json

from bottle import Bottle, request, abort, HTTPResponse, redirect

from jumpscale.loader import j
from jumpscale.core.base import StoredFactory
from jumpscale.packages.auth.bottle.auth import authenticated, get_user_info, login_required, package_authorized

from jumpscale.packages.jukebox.bottle.models import UserEntry

app = Bottle()

THREEFOLD_LOGIN_URL = "https://login.threefold.me/api"

IDENTITY_PREFIX = "JUKEBOX"


@app.route("/api/status", method="GET")
@login_required
def is_running():
    return HTTPResponse(
        j.data.serializers.json.dumps({"running": True}), status=200, headers={"Content-Type": "application/json"}
    )


@app.route("/api/admins/list", method="GET")
@package_authorized("jukebox")
def list_all_admins() -> str:
    threebot = j.servers.threebot.get("default")
    package = threebot.packages.get("jukebox")
    admins = list(set(package.admins))
    return j.data.serializers.json.dumps({"data": admins})


@app.route("/api/admins/add", method="POST")
@package_authorized("jukebox")
def add_admin() -> str:
    data = j.data.serializers.json.loads(request.body.read())
    name = data.get("name")
    threebot = j.servers.threebot.get("default")
    package = threebot.packages.get("jukebox")
    if not name:
        raise j.exceptions.Value(f"Admin name shouldn't be empty")
    if name in package.admins:
        raise j.exceptions.Value(f"Admin {name} already exists")
    package.admins.append(name)
    threebot.packages.save()


@app.route("/api/admins/remove", method="POST")
@package_authorized("jukebox")
def remove_admin() -> str:
    data = j.data.serializers.json.loads(request.body.read())
    name = data.get("name")
    threebot = j.servers.threebot.get("default")
    package = threebot.packages.get("jukebox")
    if not name:
        raise j.exceptions.Value(f"Admin name shouldn't be empty")
    if name not in package.admins:
        raise j.exceptions.Value(f"Admin {name} does not exist")
    if len(package.admins) == 1:
        raise j.exceptions.Value(f"Jukebox should have at least one admin")
    j.logger.info(f"Removing admin {name}")
    package.admins.remove(name)
    threebot.packages.save()


@app.route("/api/accept", method="GET")
@login_required
def accept():
    user_factory = StoredFactory(UserEntry)

    user_info = j.data.serializers.json.loads(get_user_info())
    tname = user_info["username"]
    explorer_url = j.core.identity.me.explorer.url

    if "testnet" in explorer_url:
        explorer_name = "testnet"
    elif "devnet" in explorer_url:
        explorer_name = "devnet"
    elif "explorer.grid.tf" in explorer_url:
        explorer_name = "mainnet"
    else:
        return HTTPResponse(
            j.data.serializers.json.dumps({"error": f"explorer {explorer_url} is not supported"}),
            status=500,
            headers={"Content-Type": "application/json"},
        )

    user_entry = user_factory.get(f"{IDENTITY_PREFIX}_{explorer_name}_{tname.replace('.3bot', '')}")
    if user_entry.has_agreed:
        return HTTPResponse(
            j.data.serializers.json.dumps({"allowed": True}), status=200, headers={"Content-Type": "application/json"}
        )
    else:
        user_entry.has_agreed = True
        user_entry.explorer_url = explorer_url
        user_entry.tname = tname
        user_entry.save()
        return HTTPResponse(
            j.data.serializers.json.dumps({"allowed": True}), status=201, headers={"Content-Type": "application/json"}
        )


@app.route("/api/allowed", method="GET")
@authenticated
def allowed():
    user_factory = StoredFactory(UserEntry)
    user_info = j.data.serializers.json.loads(get_user_info())
    tname = user_info["username"]
    explorer_url = j.core.identity.me.explorer.url
    instances = user_factory.list_all()
    for name in instances:
        user_entry = user_factory.get(name)
        if user_entry.tname == tname and user_entry.explorer_url == explorer_url and user_entry.has_agreed:
            return j.data.serializers.json.dumps({"allowed": True})
    return j.data.serializers.json.dumps({"allowed": False})


@app.route("/api/deployments/<solution_type>", method="GET")
@package_authorized("jukebox")
def list_deployments(solution_type: str) -> str:
    # TODO
    user_info = j.data.serializers.json.loads(get_user_info())
    loggedin_tname = user_info["username"]
    return j.data.serializers.json.dumps({"data": {}})


@app.route("/api/deployments", method="POST")
@package_authorized("jukebox")
def list_all_deployments() -> str:
    # TODO
    user_info = j.data.serializers.json.loads(get_user_info())
    loggedin_tname = user_info["username"]
    return j.data.serializers.json.dumps({"data": {}})