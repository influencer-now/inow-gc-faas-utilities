import base64
from typing import Any, Callable, Dict

from ..misc.model import Request
from typing import Type


def pubsub_input(req_model: Type[Request]):
    """PubSub decorator, to translate message into request model

    Args:
        req_model (Type[Request]): Request model input (class, not instance).
        Must inherit from `inowfaasutils.misc.model.Request`
    """

    def decorator(
        function: Callable[
            [Dict, Any],
            None,
        ]
    ):
        def wrapper(event, context):
            pubsub_msg = base64.b64decode(event["data"]).decode("utf-8")
            req = req_model.Schema().loads(pubsub_msg)
            res = function(req)
            # if not callback or callback.callback_function(res):
            #     return
            # else:
            #     raise CallbackRunError()

        return wrapper

    return decorator
