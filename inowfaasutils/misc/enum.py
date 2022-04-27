from enum import Enum


class CallbackType(Enum):
    WEBHOOK = "webhook"
    PUBSUB = "pubsub"


class FaasOpState(Enum):
    CRTD = "CRTD"
    """created state"""
    ERR = "ERR"
    """error state"""
    SCCS = "SCCS"
    """success state"""
