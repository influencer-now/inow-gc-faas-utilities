from enum import Enum


class CallbackType(Enum):
    WEBHOOK = "webhook"
    PUBSUB = "pubsub"


class FaasOpState(Enum):
    CRTD = "created"
    """created state"""
    ERR = "error"
    """error state"""
    SCCS = "success"
    """success state"""
