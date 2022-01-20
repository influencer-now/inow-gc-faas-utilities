from marshmallow_dataclass import dataclass
from typing import Optional


@dataclass
class FaasJob:
    """State of execution of nested FaaS functions, where each function execution is called task"""

    start_date: int
    end_date: Optional[int]
    total_tasks: int
    ended_tasks: int
    ref_pow_diff: int
    ref_pow: int
