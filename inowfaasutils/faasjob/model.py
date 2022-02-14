from marshmallow_dataclass import dataclass

from typing import Optional, Dict

from ..misc.enum import FaasOpState


@dataclass
class FaasProcess:
    """A Job excution group, usually used for batch processing"""

    jobs_state: str  # Dict[str, FaasOpState]


@dataclass
class FaasTaskState:
    """State of running task, using as reference the `ref_pow` values, which
    is a contiguous incremental index"""

    state: FaasOpState
    parent_ref: Optional[int]
    name: str


@dataclass
class FaasJob:
    """State of execution of nested FaaS functions, where each function operation
    execution is called task"""

    ref_creation_id: Optional[str]
    """creation reference id, for callback response body message"""
    process_id: Optional[str]
    start_date: int
    end_date: Optional[int]
    total_tasks: int
    error_tasks: int
    ended_tasks: int
    ref_pow_diff: int
    ref_pow: int
    tasks_info: Dict[str, FaasTaskState]


@dataclass
class FaasError:
    """Error data used to send on an error callback event"""

    task_ref: int
    task_name: Optional[str]
    err_date: int
    job_id: Optional[str]
    process_id: Optional[str]
    exception_class: str
    exception_message: str
