from marshmallow_dataclass import dataclass
from typing import List, Optional


@dataclass
class Request:
    """Request base data class"""
    job_id: Optional[str]
    op_id: Optional[str]
    job_child_idx_list: Optional[List[int]]
    job_done_collection: Optional[str]

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

