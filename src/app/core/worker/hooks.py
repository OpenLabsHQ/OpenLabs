import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import uvloop
from arq.jobs import Job

from ...crud.crud_jobs import (
    _arq_get_job_by_arq_id,
    _arq_update_job,
)
from ...schemas.job_schemas import JobSchema
from ..db.database import async_engine, get_db_session_context

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Start worker."""
    logger.info("Worker starting...")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Shutdown worker."""
    logger.info("Worker stopping...")

    # Dispose of database engine
    logger.info("Disposing of database engine...")
    await async_engine.dispose()
    logger.info("Database engine disposed.")


async def on_job_start(
    ctx: dict[str, Any],
) -> None:
    """Mark a job as IN_PROGRESS in the database."""
    # For clarity
    arq_job_id = ctx["job_id"]

    async with get_db_session_context() as db:
        job_model = await _arq_get_job_by_arq_id(db, arq_job_id)
        if not job_model:
            logger.error(
                "Failed to fetch job with ARQ ID: %s from database in on start job hook. Was it added to database before queuing job?",
                arq_job_id,
            )
            return

        # Update job
        job_schema = JobSchema.model_validate(job_model)
        start_time = datetime.now(tz=timezone.utc)
        job_update = job_schema.mark_as_in_progress(
            start_time=start_time, job_try=ctx["job_try"]
        )

        try:
            update_success = await _arq_update_job(db, job_update)
        except Exception as e:
            logger.exception(
                "Error updating job: %s as %s", job_schema.id, job_schema.status.value
            )
            # To ensure rollback
            raise e

        if not update_success:
            logger.error(
                "Failed to update job: %s and mark as %s",
                job_schema.id,
                job_schema.status.value,
            )
            return

    logger.info(
        "Marked job %s (ARQ ID: %s) as %s.",
        job_schema.id,
        job_schema.arq_job_id,
        job_schema.status.value,
    )


async def after_job_end(
    ctx: dict[str, Any],
) -> None:
    """Mark a job as COMPLETE or FAILED in the database."""
    # For clarity
    arq_job_id = ctx["job_id"]

    # Get job details from Redis
    job = Job(arq_job_id, ctx["redis"])
    result_info = await job.result_info()

    if not result_info:
        logger.error(
            "Could not retrieve result info for completed job with ARQ ID: %s from redis.",
            arq_job_id,
        )
        # Return early as throwing exceptions
        # will only clog logs
        return

    # Fetch job from database
    async with get_db_session_context() as db:
        job_model = await _arq_get_job_by_arq_id(db, arq_job_id)
        if not job_model:
            logger.error(
                "Failed to fetch job with ARQ ID: %s from database in after job hook!",
                arq_job_id,
            )
            return

        # Update job
        job_schema = JobSchema.model_validate(job_model)
        if result_info.success:
            job_update = job_schema.mark_as_complete(
                finish_time=result_info.finish_time, result=result_info.result
            )
        else:
            job_update = job_schema.mark_as_failed(
                finish_time=result_info.finish_time,
                error_message=str(result_info.result),
            )

        try:
            update_success = await _arq_update_job(db, job_update)
        except Exception as e:
            logger.exception(
                "Error updating job: %s as %s", job_schema.id, job_schema.status.value
            )
            # To ensure rollback
            raise e

        if not update_success:
            logger.error(
                "Failed to update job: %s and mark as %s",
                job_schema.id,
                job_schema.status.value,
            )
            return

    logger.info(
        "Marked job %s (ARQ ID: %s) as %s.",
        job_schema.id,
        arq_job_id,
        job_update.status.value,
    )
