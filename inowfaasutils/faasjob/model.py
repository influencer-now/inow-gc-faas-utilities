from marshmallow_dataclass import dataclass
from typing import List, Optional, Any

from ..misc.enum import FaasOpState

from google.cloud.firestore import CollectionReference


@dataclass
class FaasProcess:
    """A Job excution group, usually used for batch processing"""

    jobs_state: str  # Dict[str, FaasOpState]


@dataclass
class FaasJob:
    """State of execution of nested FaaS functions, where each function operation
    execution is called job"""

    name: str
    args: Optional[Any]
    op_id: Optional[str]
    state: FaasOpState
    start_date: int
    end_date: Optional[int]
    total_jobs: int
    ended: Optional[bool]


@dataclass
class FaasError:
    """Error data used to send on an error callback event"""

    job_name: Optional[str]
    date: int
    job_id: Optional[str]
    exception_class: str
    exception_message: str
    exception_file: str
    exception_line: int


@dataclass
class FaasJobTrigger:
    """FaaS job trigger for"""

    name: str
    message: dict
    queue: str
    _job: Optional[FaasJob] = None
    """FaasJob added when the job is triggered"""
    _collection: Optional[CollectionReference] = None
    """Firestore collection reference"""
    _job_id: Optional[str] = None
    """Job id in job subcollection"""
