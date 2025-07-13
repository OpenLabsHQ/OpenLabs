import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_jobs import get_job, get_jobs
from ...enums.job_status import OpenLabsJobStatus
from ...models.user_model import UserModel
from ...schemas.job_schemas import JobSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def get_all_jobs_endpoint(
    job_status: OpenLabsJobStatus | None = Query(  # noqa: B008
        default=None, description="Job status filter."
    ),
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[JobSchema]:
    """Get all owned jobs.

    Args:
    ----
        job_status (OpenLabsJobStatus | None): Filter results by status.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[JobSchema]: Information about, including status and results, of the requested job.

    """
    jobs = await get_jobs(db, current_user.id, current_user.is_admin, status=job_status)
    if not jobs:
        logger.info(
            "No jobs found for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        status_text = f" {job_status.value}" if job_status else ""
        msg = (
            f"No{status_text} jobs found!"
            if current_user.is_admin
            else f"Unable to find any{status_text} jobs that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )

    logger.info(
        "Sucessfully retrieved %s jobs for user: %s (%s).",
        len(jobs),
        current_user.email,
        current_user.id,
    )

    return jobs


@router.get("/{identifier}")
async def get_job_endpoint(
    identifier: int | str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> JobSchema:
    """Get job information, including the results if available.

    Args:
    ----
        identifier (int | str): The `id` integer or `arq_job_id` string.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        JobSchema: Information about, including status and results, of the requested job.

    """
    job = await get_job(db, identifier, current_user.id, current_user.is_admin)
    if not job:
        logger.info(
            "Failed to retrieve job: %s for user: %s (%s).",
            identifier,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID: {identifier} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully retrieved job: %s (ARQ ID: %s) for user: %s (%s).",
        job.id,
        job.arq_job_id,
        current_user.email,
        current_user.id,
    )

    return job
