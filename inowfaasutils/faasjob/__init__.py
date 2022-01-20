from __future__ import annotations

import datetime
import math
import uuid
import os

from typing import Tuple
from contextlib import contextmanager

from ..misc.singleton import Singleton

from .model import FaasJob
from ..storage.datastore import DataStoreClient

_INIT_TASKS_TOTAL = 1
_INIT_TASKS_ENDED = 0
_INIT_REF_POW = 1
_INIT_REF_POW_DIFF = 2


class FaasJobManager(metaclass=Singleton):
    """Job completion metadata manager. It is a singleton class used for storing information of nested
    executed FaaS operations, and help to implement architectures like Fan-in and Fan-out.

    Usage:
        >>> from inowfaasutils.faasjob import FaasJobManager
        >>> job_id = input_job_id # None if it is new one
        >>> with FaasJobManager().job_init(job_id) as fjm:
        >>>     logger.info("An initial metadata is created at this point with current task")
        >>>     fjm.add_task()
        >>>     call_faas_async_op("cool_operator")
        >>> logger.info("Metadata is updated once with block ends")

    Once all related tasks are finished, end_date is updated with epoch representation (in seconds)
    """

    datastore: DataStoreClient
    entity: str = ""
    job_id: str

    def __init__(self):
        if os.environ.get("FAAS_JOB_ENTITY_NAME"):
            self.entity = os.environ.get("FAAS_JOB_ENTITY_NAME")
        else:
            raise KeyError("FAAS_JOB_ENTITY_NAME not found in environment variables")
        GC_PROJECT_ID: str
        if os.environ.get("GC_PROJECT_ID"):
            GC_PROJECT_ID = os.environ.get("GC_PROJECT_ID")
        else:
            raise KeyError("GC_PROJECT_ID not found in environment variables")
        self.datastore = DataStoreClient(GC_PROJECT_ID)
        self.new_tasks_cnt = 0
        self.diff_increment = 0
        self.job_id = None

    @contextmanager
    def job_init(self, job_id: str = None):
        """Initialize job metadata execution storage

        Args:
            job_id (str, optional): job id in DataStore, only used for already existing jobs. Defaults to None.

        Yields:
            FaasJobManager: [description]
        """
        try:
            if job_id is None:
                self.job_id = (str)(uuid.uuid4())
                self._upsert(self.job_id)
                self.ref_pow = _INIT_REF_POW
                self.diff_increment = _INIT_REF_POW_DIFF
            else:
                self.job_id = job_id
                with self.datastore.client.transaction():
                    data = self.datastore.increment_cnt_with_id(
                        self.entity, self.job_id, "ref_pow", 1
                    )
                    self.ref_pow = data["ref_pow"]
                    self.diff_increment = math.pow(2, self.ref_pow)
                    self.datastore.increment_cnt_with_entity(
                        data, "ref_pow_diff", self.diff_increment
                    )
                    self.datastore.client.put(data)
            yield self
        finally:
            with self.datastore.client.transaction():
                data = self.datastore.increment_cnt_with_id(
                    self.entity, self.job_id, "total_tasks", self.new_tasks_cnt
                )
                data = self.datastore.increment_cnt_with_entity(data, "ended_tasks", 1)
                data = self.datastore.increment_cnt_with_entity(
                    data, "ref_pow_diff", -self.diff_increment
                )
                if (
                    data["ref_pow_diff"] == 0
                    and data["ended_tasks"] == data["total_tasks"]
                ):
                    data["end_date"] = self._epoch_now()
                self.datastore.client.put(data)

    def add_task(self):
        """Increments total tasks counter on FaasJob metadata"""
        self.new_tasks_cnt += 1

    def _upsert(self, data: FaasJob = None) -> Tuple[str, FaasJob]:
        """Upsert faas job execution metadata into DataStore `job` entity

        Args:
            data (Job, optional): faas job execution metadata to be override. Defaults to None.

        Returns:
            Tuple[str, Job]: id and faas job execution metadata
        """
        job = (
            FaasJob(
                start_date=self._epoch_now(),
                end_date=None,
                total_tasks=_INIT_TASKS_TOTAL,
                ended_tasks=_INIT_TASKS_ENDED,
                ref_pow=_INIT_REF_POW,
                ref_pow_diff=_INIT_REF_POW_DIFF,
            )
            if data is not None
            else data
        )
        self.datastore.upsert(self.entity, self.job_id, job.Schema().dump(job))
        return (self.job_id, job)

    @staticmethod
    def _epoch_now() -> int:
        """Seconds since epoch (time zero)

        Returns:
            int: time elapsed since epoch
        """
        return (int)(datetime.datetime.now().timestamp())
