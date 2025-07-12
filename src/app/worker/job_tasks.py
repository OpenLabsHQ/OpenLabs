import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import uvloop

from ..core.config import settings
from ..core.db.database import get_db_session_context
from ..crud.crud_jobs import delete_completed_jobs_before, delete_failed_jobs_before
from ..schemas.message_schema import MessageSchema
from ..utils.job_utils import track_job_status

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)


@track_job_status
async def cleanup_old_jobs(ctx: dict[str, Any], user_id: int) -> dict[str, Any]:
    """Cleanup old job records."""
    logger.info("Starting old job record cleanup. Triggered by user: %d.", user_id)

    now = datetime.now(tz=timezone.utc)
    complete_cutoff_date = now - timedelta(days=settings.COMPLETED_JOB_MAX_AGE_DAYS)
    failed_cutoff_date = now - timedelta(days=settings.FAILED_JOB_MAX_AGE_DAYS)

    async with get_db_session_context() as db:
        complete_deleted = await delete_completed_jobs_before(db, complete_cutoff_date)
        logger.info("Successfully deleted %d complete status jobs.", complete_deleted)

        failed_deleted = await delete_failed_jobs_before(db, failed_cutoff_date)
        logger.info("Successfully deleted %s failed status jobs.", failed_deleted)

    msg = MessageSchema(
        message=f"Successfully deleted {complete_deleted} completed jobs and {failed_deleted} failed jobs."
    )

    return msg.model_dump(mode="json")
