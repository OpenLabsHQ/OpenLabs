import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..enums.job_status import OpenLabsJobStatus
from ..models.job_models import JobModel
from ..schemas.job_schemas import JobCreateSchema, JobSchema

logger = logging.getLogger(__name__)


async def get_jobs(
    db: AsyncSession,
    user_id: int,
    is_admin: bool = False,
    status: OpenLabsJobStatus | None = None,
) -> list[JobSchema]:
    """Get a list of jobs.

    Args:
    ----
        db (Session): Database connection.
        user_id (int): ID of user.
        is_admin (bool): Admins can see other user's jobs.
        status (OpenLabsJobStatus): Filter jobs by status.

    Returns:
    -------
        list[JobSchema]: List of job schemas.

    """
    stmt = select(JobModel)

    if not is_admin:
        stmt = stmt.filter(JobModel.owner_id == user_id)

    if status:
        stmt = stmt.filter(JobModel.status == status)

    result = await db.execute(stmt)

    job_models = result.scalars().all()
    job_schemas = [JobSchema.model_validate(model) for model in job_models]

    logger.info(
        "Fetched %s jobs for user: %s.",
        len(job_schemas),
        user_id,
    )
    return job_schemas


async def get_job(
    db: AsyncSession, job_id: int, user_id: int, is_admin: bool = False
) -> JobSchema | None:
    """Get job by ID.

    Args:
    ----
        db (Session): Database connection.
        job_id (int): ID of the job.
        user_id (int): ID of the user requesting data.
        is_admin (bool): Admins can see other user's jobs.

    Returns:
    -------
        Optional[JobSchema]: Job data if it exists in the database.

    """
    job_model = await db.get(JobModel, job_id)

    if not job_model:
        logger.info("Failed to fetch job: %s. Not found in database!", job_id)
        return None

    if is_admin or job_model.owner_id == user_id:
        logger.debug("Fetched job: %s for user: %s.", job_id, user_id)
        return JobSchema.model_validate(job_model)

    logger.warning("User: %s is not authorized to fetch job: %s.", user_id, job_id)
    return None


async def create_job(db: AsyncSession, job: JobCreateSchema, user_id: int) -> JobSchema:
    """Create and add a new job to the database session.

    **Note:** This function only adds jobs to the database session. It is the responsibility
    of the caller to commit the changes to the database or rollback in the event of
    a failure.

    Args:
    ----
        db (Session): Database connection.
        job (JobCreateSchema): Pydantic model of job data without IDs.
        user_id (int): User who owns the new job.

    Returns:
    -------
        JobSchema: The newly created job data with it's ID.

    """
    job_model = JobModel(**job.model_dump(), owner_id=user_id)

    db.add(job_model)
    logger.debug(
        "Added job model with name: %s to database session.",
        job.job_name,
    )

    try:
        await db.flush()
        await db.refresh(job_model)
        logger.debug(
            "Successfully flushed job: %s owned by user: %s.",
            job_model.id,
            user_id,
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Database error while flushing job to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while flushing job to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise

    return JobSchema.model_validate(job_model)


async def _arq_get_job_by_arq_id(
    db: AsyncSession,
    arq_job_id: str,
) -> JobModel | None:
    """Get job by it's ARQ job ID.

    **NOTE:** This is only supposed to be used by the ARQ hooks for automatic
    job tracking and updates.

    Args:
    ----
        db (Session): Database connection.
        arq_job_id (str): ARQ job ID of the job.

    Returns:
    -------
        Optional[JobModel]: Job data if it exists in the database.

    """
    stmt = select(JobModel).where(JobModel.arq_job_id == arq_job_id)

    result = await db.execute(stmt)
    job_model = result.scalar_one_or_none()

    if not job_model:
        logger.info(
            "Failed to fetch job with arq_job_id: %s. Not found in database!",
            arq_job_id,
        )
        return None

    return job_model


async def _arq_update_job(
    db: AsyncSession,
    job_update: JobSchema | JobCreateSchema,
) -> JobModel | None:
    """Update existing job.

    **NOTE:** This is only supposed to be used by the ARQ hooks for automatic
    job tracking and updates.

    **NOTE 2:** It is the responsibility of the caller to commit the transaction
    or rollback in the event of a failure.

    Args:
    ----
        db (AsyncSession): The database session.
        job_update (JobSchema | JobCreateSchema): The updated job.

    Returns:
    -------
        Optional[JobModel]: The updated job model, or None if the job was not found.

    """
    job_model = await _arq_get_job_by_arq_id(db, job_update.arq_job_id)
    if not job_model:
        msg = f"Failed to update job with ARQ ID: {job_update.arq_job_id}!"
        logger.error(msg)
        raise ValueError(msg)

    # Exclude unset fields
    update_data = job_update.model_dump(exclude_unset=True)

    logger.debug("Updating job model %s with new data.", job_model.id)

    for field, value in update_data.items():
        setattr(job_model, field, value)

    try:
        await db.flush()
        await db.refresh(job_model)
        logger.debug("Successfully flushed updated job: %s.", job_model.id)
    except SQLAlchemyError as e:
        logger.exception(
            "Database error while flushing updated job: %s. Exception: %s.",
            job_model.id,
            e,
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while flushing updated job: %s. Exception: %s.",
            job_model.id,
            e,
        )
        raise

    return job_model
