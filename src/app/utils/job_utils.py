import logging

from arq import ArqRedis
from arq.jobs import Job, JobResult
from arq.jobs import JobStatus as ArqJobStatus

from ..enums.job_status import OpenLabsJobStatus
from ..schemas.job_schemas import JobCreateSchema

logger = logging.getLogger(__name__)


def arq_to_openlabs_job_status(
    arq_status: ArqJobStatus,
    arq_job_result: JobResult | None = None,
) -> OpenLabsJobStatus:
    """Translate an ARQ job's status into a OpenLabsJobStatus.

    Args:
    ----
        arq_status (ArqJobStatus): The raw status enum obtained from an `arq.jobs.Job.status()` call.
        arq_job_result (Optional[JobResult]): The result data object from an `arq.jobs.Job.result_info()` call. Only requried when job status is complete to determine if the job succeeded or failed.

    Returns:
    -------
        OpenLabsJobStatus: The corresponding OpenLabs application status enum member.

    Example:
    -------
        ```python
        job = Job(job_id, redis)

        status = await job.status()

        result_info = None
        if status == JobStatus.complete:
            result_info = await job.result_info()

        arq_to_openlabs_job_status(status, result_info)
        ```

    """
    if arq_status == ArqJobStatus.complete:
        if arq_job_result and arq_job_result.success:
            return OpenLabsJobStatus.COMPLETE
        # else
        return OpenLabsJobStatus.FAILED

    status_map = {
        ArqJobStatus.deferred: OpenLabsJobStatus.QUEUED,
        ArqJobStatus.queued: OpenLabsJobStatus.QUEUED,
        ArqJobStatus.in_progress: OpenLabsJobStatus.IN_PROGRESS,
        ArqJobStatus.not_found: OpenLabsJobStatus.NOT_FOUND,
    }
    return status_map.get(arq_status, OpenLabsJobStatus.NOT_FOUND)


async def get_job_from_redis(
    arq_job_id: str,
    redis: ArqRedis,
) -> JobCreateSchema | None:
    """Fetch an ARQ job's details and build a JobCreateSchema.

    This function retrieves all available information for a given job ID
    from Redis and uses it to populate the application's job schema.

    Args:
    ----
        arq_job_id (str): The unique identifier of the ARQ job.
        redis (ArqRedis): The ARQ Redis connection pool.

    Returns:
    -------
        Optional[JobCreateSchema]: A populated schema instance if the job is found, otherwise None.

    """
    job = Job(job_id=arq_job_id, redis=redis)
    arq_status = await job.status()

    if arq_status == ArqJobStatus.not_found:
        return None

    # A job definition should always exist if the job
    # is not not_found
    definition = await job.info()
    if not definition:
        return None

    # We include the in_progress status because in progress
    # jobs always have a start_time which is only accesible
    # with a result_info() call.
    result_info: JobResult | None = None
    result_info_statuses = [ArqJobStatus.complete, ArqJobStatus.in_progress]
    if arq_status in result_info_statuses:
        result_info = await job.result_info()

    status = arq_to_openlabs_job_status(arq_status, result_info)

    job_result = None
    error_message = None

    if result_info:
        if result_info.success is True:
            job_result = result_info.result
        elif arq_status == ArqJobStatus.complete and result_info.success is False:
            error_message = str(result_info.result)

    job_data = {
        "arq_job_id": arq_job_id,
        "job_name": definition.function,
        "job_try": definition.job_try,
        "enqueue_time": definition.enqueue_time,
        "start_time": result_info.start_time if result_info else None,
        "finish_time": result_info.finish_time if result_info else None,
        "status": status,
        "result": job_result,
        "error_message": error_message,
    }

    return JobCreateSchema.model_validate(job_data)
