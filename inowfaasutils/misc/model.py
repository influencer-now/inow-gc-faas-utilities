from marshmallow_dataclass import dataclass
from typing import Optional


@dataclass
class Request:
    job_id: Optional[str]


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
