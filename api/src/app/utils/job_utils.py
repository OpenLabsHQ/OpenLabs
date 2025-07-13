import asyncio
import functools
import logging
from typing import Any, Callable, Coroutine

from arq.jobs import Job, JobResult
from arq.jobs import JobStatus as ArqJobStatus
from redis.asyncio import Redis
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

from ..core.db.database import get_db_session_context
from ..core.utils import queue
from ..crud.crud_jobs import _arq_upsert_job
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


async def _arq_get_job_from_redis(ctx: dict[str, Any]) -> JobCreateSchema | None:
    """Fetch an ARQ job's details and build a JobCreateSchema."""
    job = Job(job_id=ctx["job_id"], redis=ctx["redis"])
    arq_status = await job.status()

    if arq_status == ArqJobStatus.not_found:
        return None

    # Will exist if job exists in ARQ
    job_info = await job.info()
    if not job_info:
        return None

    # Attempt to fetch result
    result_info: JobResult | None = None
    if arq_status in ArqJobStatus.complete:
        result_info = await job.result_info()

    # Update job info with result
    if result_info:
        # Result info is a superset of job info
        job_info = result_info

    status = arq_to_openlabs_job_status(arq_status, result_info)

    # Handle results/errors
    job_result = None
    error_message = None

    if result_info:
        if result_info.success is True:
            job_result = result_info.result
        elif arq_status == ArqJobStatus.complete and result_info.success is False:
            error_message = str(result_info.result)

    # Get job try count
    job_try = ctx.get("job_try")
    if not job_try:
        job_try = job_info.job_try

    # Get job start time
    start_time = ctx.get("start_time")
    if not start_time:
        start_time = getattr(job_info, "start_time", None)

    # Get job finish time
    finish_time = ctx.get("finish_time")
    if not finish_time:
        finish_time = getattr(job_info, "finish_time", None)

    job_data = {
        "arq_job_id": ctx["job_id"],
        "job_name": job_info.function,
        "job_try": job_try,
        "enqueue_time": job_info.enqueue_time,
        "start_time": start_time,
        "finish_time": finish_time,
        "status": status,
        "result": job_result,
        "error_message": error_message,
    }

    return JobCreateSchema.model_validate(job_data)


# Approximately 1 minute of total wait time
@retry(
    stop=stop_after_attempt(6),
    wait=wait_random_exponential(multiplier=1, max=30),
    before_sleep=before_sleep_log(logger, logging.DEBUG),
)
async def update_job_in_db(ctx: dict[str, Any], user_id: int) -> None:
    """Update a job in the database."""
    # For clarity
    arq_job_id = ctx["job_id"]

    job_update = await _arq_get_job_from_redis(ctx)
    if not job_update:
        msg = f"Failed to update job: {arq_job_id}. Not found in Redis!"
        raise RuntimeError(msg)

    async with get_db_session_context() as db:
        await _arq_upsert_job(db, job_update, user_id)

    logger.info(
        "Marked job %s as %s.",
        job_update.arq_job_id,
        job_update.status.value,
    )


def track_job_status(
    func: Callable[..., Coroutine[Any, Any, Any]],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Track a job in Redis and update the database automatically."""

    @functools.wraps(func)
    async def wrapper(
        ctx: dict[str, Any], *args: Any, **kwargs: Any  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        background_tasks: set[asyncio.Task[None]] = set()

        user_id = kwargs.get("user_id")
        if not user_id:
            msg = "Failed to update job status. Keyword arg 'user_id' not found!"
            logger.error(msg)
            raise ValueError(msg)

        def update_task_callback(task: asyncio.Task[None]) -> None:
            """Log and discard database update task."""
            try:
                task.result()  # Reraise exception if present
                logger.info(
                    "Updated job with ARQ ID: %s in database successfully.",
                    ctx.get("job_id", "unknown_id"),
                )
            except Exception:
                logger.exception(
                    "Failed to update job with ARQ ID: %s in database.",
                    ctx.get("job_id", "unknown_id"),
                )
            finally:
                background_tasks.discard(task)  # Always remove the task

        # Run database updates in background
        def create_update_task() -> None:
            """Create and stores a background task for updating the DB."""
            task = asyncio.create_task(update_job_in_db(ctx, user_id))
            background_tasks.add(task)
            task.add_done_callback(update_task_callback)

        create_update_task()

        try:
            return await func(ctx, *args, **kwargs)
        finally:
            await asyncio.sleep(1)  # Yield control to let ARQ update Redis.
            create_update_task()

    return wrapper


async def enqueue_arq_job(
    job_name: str, *job_args: Any, user_id: int  # noqa: ANN401
) -> str | None:
    """Queue a job in ARQ.

    Args:
        job_name: Name of function to be executed by ARQ.
        *job_args: Positional arguments to be passed to ARQ function.
        user_id: ID of user who triggered/associated with job.

    Returns:
        str: ARQ job ID if enqueue was successful. Otherwise, None.

    """
    if not isinstance(queue.pool, Redis):
        logger.critical(
            "Failed to queue %s job on behalf of user: %s. Failed to connect to the Redis task queue!",
            job_name,
            user_id,
        )
        return None

    job = await queue.pool.enqueue_job(job_name, *job_args, user_id=user_id)
    if not job:
        logger.error(
            "Failed to queue %s job on behalf of user: %s. ARQ rejected the job!",
            job_name,
            user_id,
        )
        return None

    logger.info(
        "Successfully queued %s job on behalf of user: %s. ARQ ID: %s.",
        job_name,
        job.job_id,
        user_id,
    )

    return job.job_id
