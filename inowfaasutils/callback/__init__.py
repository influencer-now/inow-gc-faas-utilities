from typing import Dict, Optional, Type
from .base import BaseCallback
from .pubsub import PubSubCallback
from .webhook import WebhookCallback
from ..misc.enum import CallbackType
from ..misc.model import CallbackCreation, Request

import re


__callback_type_dict: Dict[CallbackType, Type[BaseCallback]] = {
    CallbackType.WEBHOOK: WebhookCallback,
    CallbackType.PUBSUB: PubSubCallback,
}


def _get_callback_data(req: Request) -> Optional[CallbackCreation]:
    if req.callback_type:
        return CallbackCreation(
            type=req.callback_type,
            token=req.callback_token,
            location=req.callback_location,
        )
    else:
        return None


def _get_err_callback_data(req: Request) -> Optional[CallbackCreation]:
    if req.callback_type:
        return CallbackCreation(
            type=req.err_callback_type,
            token=req.err_callback_token,
            location=req.err_callback_location,
        )
    else:
        return None


def _get_callback(callback_data: CallbackCreation) -> Optional[BaseCallback]:
    if callback_data is not None:
        callback_class = __callback_type_dict[callback_data.type]
        callback_instance: BaseCallback
        if WebhookCallback == callback_class:
            url = callback_data.location
            token = callback_data.token
            callback_instance = WebhookCallback(url, token)
        if PubSubCallback == callback_class:
            project = re.findall(r"projects/(.*?)/", callback_data.location)
            topic = re.findall(r".*topics/(.*)", callback_data.location)
            callback_instance = PubSubCallback(project, topic)
        return callback_instance
    else:
        return None


def get_callback(req: Request) -> Optional[BaseCallback]:
    callback_data = _get_callback_data(req)
    return _get_callback(callback_data)


def get_err_callback(req: Request) -> Optional[BaseCallback]:
    callback_data = _get_err_callback_data(req)
    return _get_callback(callback_data)
