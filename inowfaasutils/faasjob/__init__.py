from __future__ import annotations

import datetime
import math
import uuid
import os
import json

from typing import Callable, Optional, Tuple
from contextlib import contextmanager
from google.cloud.datastore.entity import Entity

from ..misc.dataclass_helper import asdict

from ..callback.base import BaseCallback

from ..callback import get_callback, get_err_callback
from ..misc.enum import FaasOpState

from ..misc.model import Request

from ..misc.singleton import Singleton

from .model import FaasError, FaasJob, FaasTaskState
from ..storage.datastore import DataStoreClient

_INIT_TASKS_TOTAL = 1
_INIT_TASKS_ENDED = 0
_INIT_REF_POW = 1
_INIT_REF_POW_DIFF = 2


class FaasJobManager(metaclass=Singleton):
    """Job completion metadata manager. It is a singleton class used for storing, no creo que Tania me suba el sueldo a 4 palos, que es lo que podría ganar en algo afuera
        >>>     call_faas_async_op("cool_operator")
        >>> logger.info("Metadata is updated once with block ends")

    Once all related tasks are finished, end_date is updated with epoch representation (in seconds)
    """

    datastore: DataStoreClient
    job_entity: str = ""
    """job entity name in datastore"""
    process_entity: str = ""
    """process entity name in datastore"""
    job_id: str
    process_id: str

    def __init__(self):
        if os.environ.get("FAAS_JOB_ENTITY_NAME"):
            self.job_entity = os.environ.get("FAAS_JOB_ENTITY_NAME")
        else:
            raise KeyError("FAAS_JOB_ENTITY_NAME not found in environment variables")
        if os.environ.get("FAAS_PROCESS_ENTITY_NAME"):
            self.process_entity = os.environ.get("FAAS_PROCESS_ENTITY_NAME")
        else:
            raise KeyError(
                "FAAS_PROCESS_ENTITY_NAME not found in environment variables"
            )
        GC_PROJECT_ID: str
        if os.environ.get("GC_PROJECT_ID"):
            GC_PROJECT_ID = os.environ.get("GC_PROJECT_ID")
        else:
            raise KeyError("GC_PROJECT_ID not found in environment variables")
        self.datastore = DataStoreClient(GC_PROJECT_ID)
        self.new_tasks_cnt = 0
        self.diff_increment = 0
        self.job_id = None
        self.process_id = None

    @contextmanager
    def job_init(
        self,
        req: Request = None,
        trace_states: bool = True,
        task_name: Optional[str] = "default",
    ):
        """Initialize job metadata execution storage

        Args:
            req (str, Request): base Faas Job request.
            trace_states (bool, optional): wether success or error states of each execution
            should be saved. Defaults to True.
            task_name: name of the task for traceability option. Defaults to 'default'.

        Yields:
            FaasJobManager: [description]
        """

        _task_state = FaasOpState.CRTD
        _end_job: Callable[[Entity], None]
        _err_exception: Exception

        err_callback: BaseCallback

        if req.callback_type:

            callback = get_callback(req)

            @callback.add_callback
            def _end_job(job_data: Entity):
                job_data["end_date"] = self._epoch_now()
                return job_data

        else:

            def _end_job(job_data: Entity):
                job_data["end_date"] = self._epoch_now()
                return job_data

        try:
            if req.job_id is None:
                self.job_id = (str)(uuid.uuid4())
                self._upsert(
                    self.job_id,
                    process_id=req.process_id,
                    ref_creation_id=req.job_ref_creation_id,
                    trace=trace_states,
                    tasks_state=FaasTaskState(
                        state=_task_state,
                        parent_ref=req.task_parent_ref,
                        name=task_name,
                    ),
                )
                self.ref_pow = _INIT_REF_POW
                self.diff_increment = _INIT_REF_POW_DIFF
            else:
                self.job_id = req.job_id
                with self.datastore.client.transaction():
                    job_data = self.datastore.increment_cnt_with_id(
                        self.job_entity, self.job_id, "ref_pow", 1
                    )
                    self.ref_pow = job_data["ref_pow"]
                    self.diff_increment = math.pow(2, self.ref_pow)
                    self.datastore.increment_cnt_with_entity(
                        job_data, "ref_pow_diff", self.diff_increment
                    )
                    self.datastore.client.put(job_data)
            yield self
        except Exception as ex:
            _err_exception = ex
            _task_state = FaasOpState.ERR
            err_callback = get_err_callback(req)
        finally:
            if _task_state != FaasOpState.ERR:
                _task_state = FaasOpState.SCCS

            with self.datastore.client.transaction():

                _multi_data = list()
                process_data: Optional[Entity]

                job_data = self.datastore.increment_cnt_with_id(
                    self.job_entity, self.job_id, "total_tasks", self.new_tasks_cnt
                )
                if _task_state != FaasOpState.ERR:
                    job_data = self.datastore.increment_cnt_with_entity(
                        job_data, "ended_tasks", 1
                    )
                else:
                    job_data = self.datastore.increment_cnt_with_entity(
                        job_data, "error_tasks", 1
                    )
                job_data = self.datastore.increment_cnt_with_entity(
                    job_data, "ref_pow_diff", -self.diff_increment
                )

                if job_data["ref_pow_diff"] == 0 and (
                    job_data["ended_tasks"] + job_data["error_tasks"]
                    == job_data["total_tasks"]
                ):
                    _end_job(job_data)

                    if self.process_id is not None and process_data is None and trace_states:
                        process_data = self.datastore.get_entity(
                            self.process_entity, self.process_id
                        )
                        process_data["jobs_state"][self.job_id] = (
                            FaasOpState.SCCS
                            if job_data["error_tasks"] == 0
                            else FaasOpState.ERR
                        )
                        _multi_data.append(process_data)

                job_data["tasks_info"][str(self.ref_pow)]["state"] = _task_state.name

                _multi_data.append(job_data)

                self.datastore.client.put_multi(_multi_data)

        if _task_state == FaasOpState.ERR and err_callback is not None:
            err_data = FaasError(
                task_ref=self.ref_pow,
                task_name=task_name,
                err_date=self._epoch_now(),
                job_id=self.job_id,
                process_id=self.process_id,
                exception_class=_err_exception.__class__.__name__,
                exception_message=str(_err_exception),
            )
            err_callback.callback_function(FaasError.Schema().dump(err_data))

    def add_task(self):
        """Increments total tasks counter on FaasJob metadata"""
        self.new_tasks_cnt += 1

    def _upsert(
        self,
        data: FaasJob = None,
        process_id: str = None,
        ref_creation_id: str = None,
        trace: bool = True,
        tasks_state: FaasTaskState = None,
    ) -> Tuple[str, FaasJob]:
        """Upsert faas job execution metadata into DataStore `job` entity

        Args:
            data (Job, optional): faas job execution metadata to be override.
            Defaults to None.
            process_id (str, optional): faas job process id, None if there
            is none. Defaults to None.
            ref_creation_id (str, optional): reference creation id, for external
            source integration. Defaults to None.
            trace (bool, optional): True if traceability is required.
            Defaults to True
            tasks_state (FaasOpState, optional): set task state if trace is active.
            Defaults to None.
        Returns:
            Tuple[str, Job]: id and faas job execution metadata
        """
        job = (
            FaasJob(
                ref_creation_id=ref_creation_id,
                process_id=process_id,
                start_date=self._epoch_now(),
                end_date=None,
                total_tasks=_INIT_TASKS_TOTAL,
                error_tasks=0,
                ended_tasks=_INIT_TASKS_ENDED,
                ref_pow=_INIT_REF_POW,
                ref_pow_diff=_INIT_REF_POW_DIFF,
                tasks_info=Entity(),
            )
            if data is not None
            else data
        )
        if trace:
            task_state_dict: dict = asdict(tasks_state)
            task_state_entity = Entity(
                exclude_from_indexes=tuple(task_state_dict.keys())
            )
            task_state_entity.update(task_state_dict)
            job.tasks_info[str(job.ref_pow)] = task_state_entity
            tasks_info_entity = Entity(
                exclude_from_indexes=tuple(job.tasks_info.keys())
            )
            tasks_info_entity.update(job.tasks_info)
            job_dict = asdict(job)
            job_dict["tasks_info"] = tasks_info_entity
        self.datastore.upsert(self.job_entity, self.job_id, job_dict)
        return (self.job_id, job)

    @staticmethod
    def _epoch_now() -> int:
        """Seconds since epoch (time zero)

        Returns:
            int: time elapsed since epoch
        """
        return (int)(datetime.datetime.now().timestamp())
