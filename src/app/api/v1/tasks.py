import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.app.crud.crud_jobs import add_job
from src.app.enums.job_status import JobSubmissionDetail

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...models.user_model import UserModel
from ...schemas.job_schemas import JobCreateSchema, JobSubmissionResponseSchema
from ...utils.job_utils import enqueue_arq_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/cleanup-old-jobs", status_code=status.HTTP_202_ACCEPTED)
async def cleanup_old_jobs_endpoint(
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> JobSubmissionResponseSchema:
    """Cleanup old jobs in the database.

    What this does:

        - Delete completed jobs older than `COMPLETED_JOB_MAX_AGE_DAYS`. Defined in `.env`. Defaults to 14.

        - Delete failed jobs older than `FAILED_JOB_MAX_AGE_DAYS`. Defined in `.env`. Defaults to 30.

    Returns
    -------
        JobSubmissionResponseSchema: Job tracking ID and submission details.

    """
    job_name = "cleanup_old_jobs"

    arq_job_id = await enqueue_arq_job(job_name, user_id=current_user.id)
    if not arq_job_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed queue up job! Try again later.",
        )

    # Pre-fetch/save data for logging incase of a database error
    current_user_email = current_user.email
    current_user_id = current_user.id

    try:
        job_to_add = JobCreateSchema.create_queued(
            arq_job_id=arq_job_id, job_name=job_name
        )
        await add_job(db, job_to_add, current_user.id)
        detail_message = JobSubmissionDetail.DB_SAVE_SUCCESS
    except Exception:
        logger.warning(
            "Failed to save %s job with ARQ ID: %s to database on behalf of user: %s (%s)!",
            job_name,
            arq_job_id,
            current_user_email,
            current_user_id,
        )
        detail_message = JobSubmissionDetail.DB_SAVE_FAILURE

    return JobSubmissionResponseSchema(
        arq_job_id=arq_job_id, detail=detail_message.value
    )
