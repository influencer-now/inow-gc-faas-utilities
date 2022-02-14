import dataclasses
from enum import Enum


def custom_dict(data):
    return {
        field: value.value if isinstance(value, Enum) else value
        for field, value in data
        if value is not None
    }


def asdict(data_instance, dict_factory=custom_dict):
    return dataclasses.asdict(data_instance, dict_factory=dict_factory)
