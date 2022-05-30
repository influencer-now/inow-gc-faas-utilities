from marshmallow_dataclass import dataclass
from typing import List, Optional


@dataclass
class Request:
    """Request base data class"""
    user_id: Optional[int]
    username: Optional[str]
    process_id: Optional[str]
    parent_job_id: Optional[str]
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

