from marshmallow_dataclass import dataclass
from typing import Optional

from .enum import CallbackType


@dataclass
class Request:
    """Request base data class"""

    callback_type: Optional[CallbackType]
    callback_location: Optional[str]
    callback_token: Optional[str]
    err_callback_type: Optional[CallbackType]
    err_callback_location: Optional[str]
    err_callback_token: Optional[str]
    process_id: Optional[str]
    job_id: Optional[str]
    job_ref_creation_id: Optional[str]
    task_parent_ref: Optional[int]


@dataclass
class Response:
    code: int


@dataclass
class ResponseStatus(Response):
    status: str
    message: str


@dataclass
class ResponseError(Response):
    error: str
    code: int


@dataclass
class CallbackCreation:
    type: Optional[CallbackType]
    location: Optional[str]
    token: Optional[str]
