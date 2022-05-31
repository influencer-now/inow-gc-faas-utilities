from marshmallow_dataclass import dataclass
from typing import Optional, Any

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
    """name of FaaS Job"""
    process_id: Optional[str]
    """tag for a process the FaaS Job is part of"""
    parent_job_id: Optional[str]
    """operation id of the FaaS Job triggered this (via callback)"""
    args: Optional[Any]
    """arguments given to FaaS Job when it is triggered"""
    result: Optional[Any]
    op_id: Optional[str]
    """operational id, to identify a FaaS Job or sub FaaS Job operation"""
    state: FaasOpState
    """completion state"""
    start_date: int
    """epoch of when the operation stated"""
    end_date: Optional[int]
    """epoch of when the operation ended"""
    total_jobs: int
    """total of operations (this job plus children) the FaaS Job has"""
    ended: Optional[bool]
    """whether the whole job (this job and every operation in 
        the tree) has ended"""


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
