from typing import Type, Any, Callable, Dict

from ..misc.model import Request
from ..misc.model import ResponseStatus

import json


def http_input(
    req_model: Type[Request],
    res_model: Type[ResponseStatus],
):
    """HTTP decorator, to translate message into request model

    Args:
        req_model (Type[Request]): Request model input (class, not instance).
        Must inherit from `inowfaasutils.misc.model.Request`
        res_model (Type[Request]): Response model input (class, not instance).
        Must inherit from `inowfaasutils.misc.model.ResponseStatus`
    """

    def decorator(
        function: Callable[
            [Dict, Any],
            None,
        ]
    ):
        def wrapper(request):
            html_msg = request.get_json()
            req = req_model.Schema().loads(json.dumps(html_msg))
            res = function(req)
            return res_model.Schema().dumps(res)

        return wrapper

    return decorator
