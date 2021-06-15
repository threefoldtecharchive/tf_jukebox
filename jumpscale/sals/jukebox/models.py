import datetime
from enum import Enum

from jumpscale.core.base import Base, fields


class State(Enum):
    DEPLOYED = "deployed"
    DELETED = "deleted"
    ERROR = "error"
    EXPIRED = "expired"


class BlockchainNode(Base):
    state = fields.Enum(State)
    wid = fields.Integer()
    node_id = fields.String()
    ipv4_address = fields.IPAddress()
    ipv6_address = fields.IPAddress()
    creation_time = fields.DateTime(default=datetime.datetime.utcnow)
