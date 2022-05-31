from __future__ import annotations

import datetime
import uuid
import os
import json

from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

from inowfaasutils.comm.pubsub import PubSubClient

from ..misc.dataclass_helper import asdict
from ..misc.enum import FaasOpState
from ..misc.model import Request
from .model import FaasError, FaasJob, FaasJobTrigger
from ..storage.firestore import FireStoreClient

from google.cloud.firestore import (
    DocumentReference,
)

_INIT_JOBS_TOTAL = 1


class FaasJobManager:
    """Job completion metadata manager. It is a singleton class used for storing information of nested
    executed FaaS operations, and help to implement architectures like Fan-in and Fan-out.

    Usage:
        >>> from inow-gc-faas-utilities.faasjob import FaasJobManager
        >>> from inow-gc-faas-utilities.misc.model import Request
        >>> job_name = "my_job_1"
        >>> req = Request
        >>> with FaasJobManager().job_init(req, job_name) as fjm:
        >>>     logger.info("An initial metadata is created at this point with current job")
        >>>     fjm.add_job()
        >>>     call_faas_async_op("cool_operator")
        >>> logger.info("Metadata is updated once with block ends")

    Once all related jobs are finished, end_date is updated with epoch representation (in seconds)
    """

    def __init__(self):
        self.job_collection_name: str = ""
        """job collection name in firestore"""
        self.remaining_job_collection_name: str = ""
        """remaining job metadata collection name in firestore"""
        self.failed_job_collection_name: str = ""
        """failed job metadata collection name in firestore"""

        self._init_envs()
        self.firestore: FireStoreClient = FireStoreClient(self.GC_PROJECT_ID)
        self.new_jobs_cnt = 0
        self.diff_increment = 0
        self.job_id: Optional[str] = None
        self.op_id: Optional[str] = None
        self.faas_trigger_queue: List[FaasJobTrigger] = []
        self.job_parent_idx_list: List[int] = []
        self.job_done_collection: Optional[str] = None
        self.user_id = None
        self.username = None
        self.job_result = None
        self.process_id = None
        self.parent_job_id = None

    def _init_envs(self):
        """Init all environment variables needed to initialize this class

        Raises:
            KeyError: key error if environment not found
        """

        if os.environ.get("FAAS_JOB_COLLECTION_NAME"):
            self.job_collection_name = os.environ.get("FAAS_JOB_COLLECTION_NAME")
        else:
            raise KeyError(
                "FAAS_JOB_COLLECTION_NAME not found in environment variables"
            )
        if os.environ.get("FAAS_JOB_COLLECTION_NAME"):
            self.failed_job_collection_name = os.environ.get(
                "FAAS_FAILED_JOB_COLLECTION_NAME"
            )
        else:
            raise KeyError(
                "FAAS_FAILED_JOB_COLLECTION_NAME not found in environment variables"
            )
        if os.environ.get("FAAS_JOB_COLLECTION_NAME"):
            self.remaining_job_collection_name = os.environ.get(
                "FAAS_REMAINING_JOB_COLLECTION_NAME"
            )
        else:
            raise KeyError(
                "FAAS_REMAINING_JOB_COLLECTION_NAME not found in environment variables"
            )
        if os.environ.get("GC_PROJECT_ID"):
            self.GC_PROJECT_ID = os.environ.get("GC_PROJECT_ID")
        else:
            raise KeyError("GC_PROJECT_ID not found in environment variables")

    def _generate_faas_error(self, job_name: str, err: Exception) -> FaasError:
        """Generate FaaS error metadata representation

        Args:
            job_name: name of the job for traceability option
            err (Exception, optional): Exception raised on execution

        Returns:
            FaasError: FaaS error metadata representation
        """

        return FaasError(
            job_name=job_name,
            date=self._epoch_now(),
            job_id=self.job_id,
            exception_class=err.__class__.__name__,
            exception_message=str(err),
            exception_file=err.__traceback__.tb_frame.f_code.co_filename,
            exception_line=err.__traceback__.tb_lineno,
        )

    def _trigger_faas_queue(self):
        """Enqueue all FaaS calls in the corresponding topics"""

        queue_msgs: Dict[str, List[str]] = dict()
        while len(self.faas_trigger_queue):
            faas_trigger = self.faas_trigger_queue.pop()
            faas_trigger._collection.document(faas_trigger._job_id).set(
                asdict(faas_trigger._job)
            )
            if not queue_msgs.get(faas_trigger.queue):
                queue_msgs[faas_trigger.queue] = []
            queue_msgs[faas_trigger.queue].append(json.dumps(faas_trigger.message))
        for queue, msgs in queue_msgs.items():
            pubsub = PubSubClient(self.GC_PROJECT_ID, queue)
            pubsub.send_messages(msgs)

    def _job_close(
        self,
        job_name: str,
        req: Request,
        curr_state: FaasOpState,
        err: Exception = None,
    ):
        """Action after job has been executed

        Args:
            job_name (str): name assigned to job
            req (Request): base Faas Job request
            curr_state (FaasOpState): current state of job execution
            err (Exception, optional): Exception raised on execution. Defaults to None.
        """

        state = FaasOpState.SCCS if curr_state != FaasOpState.ERR else FaasOpState.ERR

        root_doc: FaasJob = FaasJob.Schema().load(
            self.firestore.get_document_snapshot(
                self.job_collection_name, self.job_id
            ).to_dict()
        )

        root_doc_ref = self.firestore.get_document_ref(
            self.job_collection_name, self.job_id
        )

        job_data: FaasJob
        upsert_job_id: str
        if len(self.job_parent_idx_list) > 0:
            parent_doc_ref = self.firestore.get_document_ref(
                self.job_collection_name,
                self.job_id,
                shard_collection_name=self.job_collection_name,
                shard_idx_list=self.job_parent_idx_list[:-1],
            )
            job_data = FaasJob.Schema().load(
                self.firestore.increment_cnt_with_id(
                    self.job_collection_name,
                    self.job_id,
                    "total_jobs",
                    self.new_jobs_cnt,
                    shard_collection_name=self.job_collection_name,
                    shard_idx_list=self.job_parent_idx_list,
                ).to_dict()
            )
            upsert_job_id = str(self.job_parent_idx_list[-1]) 
        else:
            parent_doc_ref = None
            root_doc.total_jobs += self.new_jobs_cnt
            job_data = root_doc
            upsert_job_id = self.job_id

        job_data.state = state
        job_data.result = self.job_result

        if state == FaasOpState.ERR:
            err_data = self._generate_faas_error(job_name, err)
            self._insert_failed(self.job_id, self.op_id, err_data)
            self.finish_job(req, root_doc, FaasOpState.ERR)
        elif len(self.faas_trigger_queue) > 0:
            self._trigger_faas_queue()

        self._delete_remaining(self.job_id, self.op_id)

        if (
            not root_doc.ended
            and not self.firestore.has_documents(
                self.remaining_job_collection_name, root_doc_ref
            )
            and not self.firestore.has_documents(
                self.failed_job_collection_name, root_doc_ref
            )
        ):
            self.finish_job(req, root_doc, FaasOpState.SCCS)

        job_data.end_date = self._epoch_now()
        self._upsert_job(data=job_data, job_id=upsert_job_id, parent_document=parent_doc_ref, result=self.job_result)

    def _get_or_default_job(
        self,
        data: FaasJob = None,
        name: str = None,
        args: Any = None,
        result: Any = None,
        op_id: str = None,
    ) -> FaasJob:
        """Get FaasJob object given its data. if no data is provideed, then a
        default new FaaSJob is retured.

        Args:
            data (FaasJob, optional): FaasJob data. Defaults to None.
            name (str, optional): name to set on default FaasJob. Defaults to None.
            args (Any, optional): faas job request input. Defaults to None.
            result (Any, optional): faas job request result. Defaults to None.
            op_id (str, optional): operation id. Used to check remaining and failed jobs.
            Defaults to None.
        Returns:
            FaasJob: Description of FaaS Job execution
        """

        default_op_id = op_id if op_id is not None else self.op_id
        job = (
            FaasJob(
                name=name,
                state=FaasOpState.CRTD,
                start_date=self._epoch_now(),
                op_id=default_op_id,
                end_date=None,
                ended=None,
                total_jobs=_INIT_JOBS_TOTAL,
                args=args,
                result=result,
                process_id=self.process_id,
                parent_job_id=self.parent_job_id,
            )
            if data is None
            else data
        )
        return job

    def _upsert_job(
        self,
        data: FaasJob = None,
        name: str = None,
        args: Any = None,
        result: Any = None,
        job_id: str = None,
        parent_document: Optional[DocumentReference] = None,
    ) -> Tuple[str, FaasJob]:
        """Upsert faas job execution metadata into FireStore `job` collection

        Args:
            data (Job, optional): faas job execution metadata to be override.
            Defaults to None.
            name (str, optional): faas job first job name. Defaults to None.
            args (Any, optional): faas job request input. Defaults to None.
            result (Any, optional): faas job request result. Defaults to None.
            parent_document (Optional[DocumentReference]): parent document for nested collections.
            Defaults to None.
        Returns:
            Tuple[str, FaasJob]: id and faas job execution metadata
        """

        job = self._get_or_default_job(data, name, args, result)
        job_dict = asdict(job)
        self.firestore.upsert(
            self.job_collection_name,
            job_id,
            job_dict,
            parent_document=parent_document,
        )
        return (job_id, job)

    def _insert_remaining(self, job_id: str, op_id: str) -> Tuple[str, dict]:
        """Insert faas job remaining execution metadata into FireStore `job.remaining` collection

        Args:
            job_id (str): faas job root job_id
            op_id (str): current faas job op_id
        Returns:
            Tuple[str, dict]: id and faas job remaining execution metadata
        """

        doc_ref = self.firestore.get_document_ref(self.job_collection_name, job_id)
        self.firestore.upsert(self.remaining_job_collection_name, op_id, {}, doc_ref)
        return (self.op_id, {})

    def _insert_job_done(self, job_done_collection: str, job_args: dict, job_result: dict, status: FaasOpState) -> Tuple[str, dict]:
        data = {"args": job_args, "result": job_result, "status": status.value}
        self.firestore.upsert(job_done_collection, self.job_id, data, None)
        return (self.op_id, data)


    def _delete_remaining(self, job_id: str, op_id: Optional[str]) -> bool:
        """Deletes metadata of remaining job to be executed

        Args:
            job_id (str): faas job root job_id
            op_id (str): current faas job op_id

        Returns:
            bool: True if deleted
        """

        if op_id is not None:
            doc_ref = self.firestore.get_document_ref(self.job_collection_name, job_id)
            remaining_ref: DocumentReference = doc_ref.collection(
                self.remaining_job_collection_name
            ).document(op_id)
            self.firestore.delete_document(remaining_ref)
        return True

    def _insert_failed(
        self, job_id: str, op_id: str, data: FaasError
    ) -> Tuple[str, FaasJob]:
        """Upsert faas job execution metadata into FireStore `job` collection

        Args:
            job_id (str): faas job root job_id.
            op_id (str): current faas job op_id.
            data (Job, optional): faas job execution metadata to be override.
            Defaults to None.
            Tuple[str, FaasError]: id and faas job execution metadata
        """

        doc_ref = self.firestore.get_document_ref(self.job_collection_name, job_id)
        self.firestore.upsert(
            self.failed_job_collection_name, op_id, data.Schema().dump(data), doc_ref
        )

        return (op_id, data)

    @staticmethod
    def _epoch_now() -> int:
        """Seconds since epoch (time zero)

        Returns:
            int: time elapsed since epoch
        """

        return (int)(datetime.datetime.now().timestamp())

    @contextmanager
    def job_init(
        self,
        req: Request = None,
        job_name: Optional[str] = "default",
    ):
        """Initialize a FaaS job metadata saving into FireStore storage

        Args:
            req (Request): base Faas Job request.
            job_name: name of the job for traceability option. Defaults to 'default'.

        Yields:
            FaasJobManager
        """

        _job_state = FaasOpState.CRTD
        _err_exception = None

        try:
            if req.job_id is None:
                self.job_id = (str)(uuid.uuid4())
                self.op_id = None
                self.user_id = req.user_id
                self.username = req.username
                # process id and parent job id must be init
                # before upsert
                self.process_id = req.process_id
                self.parent_job_id = req.parent_job_id
                self._upsert_job(name=job_name, job_id=self.job_id, args=req)
                self.job_parent_idx_list = []
                self.job_done_collection = req.job_done_collection
            else:
                self.job_id = req.job_id
                self.op_id = req.op_id
                self.user_id = req.user_id
                self.username = req.username
                self.process_id = req.process_id
                self.parent_job_id = req.parent_job_id
                self.job_parent_idx_list = req.job_child_idx_list
                self.job_done_collection = req.job_done_collection
            yield self
        except Exception as ex:
            _err_exception = ex
            _job_state = FaasOpState.ERR
        finally:
            self._job_close(job_name, req, _job_state, _err_exception)

    def finish_job(self, req: Request, root_job: FaasJob, status: FaasOpState):
        """Save a job done information in a firestore collection
        """

        if req.job_done_collection is not None:
            self._insert_job_done(req.job_done_collection, root_job.args, root_job.result, status)

    def add_job(self, trigger: FaasJobTrigger):
        """Increments total jobs counter on FaasJob metadata, add
        sub job execution tree reference and push a new trigger of FaaSJob
        into a queue

        Args:
            trigger (FaasJobTrigger): FaaS job trigger metadata
        """

        new_idx_list = self.job_parent_idx_list.copy()
        new_idx_list.append(self.new_jobs_cnt)
        trigger.message["process_id"] = self.process_id
        trigger.message["parent_job_id"] = self.parent_job_id
        trigger.message["job_id"] = self.job_id
        trigger.message["op_id"] = (str)(uuid.uuid4())
        trigger.message["job_child_idx_list"] = new_idx_list
        trigger.message["user_id"] = self.user_id
        trigger.message["username"] = self.username
        if self.job_done_collection is not None:
            trigger.message["job_done_collection"] = self.job_done_collection
        self.new_jobs_cnt += 1
        self._insert_remaining(self.job_id, trigger.message["op_id"])
        job_ref = self.firestore.get_document_ref(
            self.job_collection_name,
            self.job_id,
            shard_collection_name=self.job_collection_name,
            shard_idx_list=self.job_parent_idx_list,
        )
        trigger._collection = job_ref.collection(
            self.job_collection_name
        )
        trigger._job = self._get_or_default_job(
            name=trigger.name, op_id=trigger.message["op_id"], args=trigger.message
        )
        trigger._job_id = str(new_idx_list[-1])
        self.faas_trigger_queue.append(trigger)
        
    def set_result(self, result: Any):
        """Set a result of FaaS Job

        Args:
            result (Any): result of FaaS Job
        """
        self.job_result = result