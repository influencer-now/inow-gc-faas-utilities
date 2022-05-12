from datetime import datetime
from typing import Any, Callable, Dict
from ..misc.model import Request


def firestore_input(req_model: Request):

    _action_dict = {
        "geoPointValue": (lambda x: dict(x)),
        "stringValue": (lambda x: str(x)),
        "arrayValue": (
            lambda x: [_parse_value(value_dict) for value_dict in x.get("values", [])]
        ),
        "booleanValue": (lambda x: bool(x)),
        "nullValue": (lambda x: None),
        "timestampValue": (lambda x: _parse_timestamp(x)),
        "mapValue": (
            lambda x: {key: _parse_value(value) for key, value in x["fields"].items()}
        ),
        "integerValue": (lambda x: int(x)),
        "doubleValue": (lambda x: float(x)),
    }

    def _parse_value(value_dict: dict) -> Any:
        data_type, value = value_dict.popitem()

        return _action_dict[data_type](value)

    def _parse_timestamp(timestamp: str):
        try:
            return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")

    def convert(data_dict: dict) -> dict:
        result_dict = {}
        for key, value_dict in data_dict.items():
            result_dict[key] = _parse_value(value_dict)
        return result_dict

    def decorator(
        function: Callable[
            [Dict, Any],
            None,
        ]
    ):
        def wrapper(event, context):
            data = convert(event["value"]["fields"])
            req = req_model.Schema().load(data)
            function(req)

        return wrapper

    return decorator