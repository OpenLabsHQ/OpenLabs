import contextlib
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
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
    db: AsyncSession, identifier: int | str, user_id: int, is_admin: bool = False
) -> JobSchema | None:
    """Get job by ID.

    Args:
    ----
        db (Session): Database connection.
        identifier (int | str): The `id` integer or `arq_job_id` string.
        user_id (int): ID of the user requesting data.
        is_admin (bool): Admins can see other user's jobs.

    Returns:
    -------
        Optional[JobSchema]: Job data if it exists in the database.

    """
    with contextlib.suppress(Exception):
        identifier = int(identifier)

    if isinstance(identifier, int):
        logger.debug("Retrieving job by integer ID: %s", identifier)
        job_model = await db.get(JobModel, identifier)
    else:
        logger.debug("Retrieving job ARQ ID: %s", identifier)
        stmt = select(JobModel).where(JobModel.arq_job_id == identifier)
        result = await db.execute(stmt)
        job_model = result.scalar_one_or_none()

    if not job_model:
        logger.info("Failed to fetch job: %s. Not found in database!", identifier)
        return None

    if is_admin or job_model.owner_id == user_id:
        logger.debug("Fetched job: %s for user: %s.", identifier, user_id)
        return JobSchema.model_validate(job_model)

    logger.warning("User: %s is not authorized to fetch job: %s.", user_id, identifier)
    return None


async def add_new_job(
    db: AsyncSession, job_to_add: JobCreateSchema, user_id: int
) -> None:
    """Add a new job to the database.

    **Note:** This function only adds jobs to the database session. It is the responsibility
    of the caller to commit the changes to the database or rollback in the event of
    a failure.

    Args:
    ----
        db (AsyncSession): The database session.
        job_to_add (JobSchema | JobCreateSchema): Pydantic model of job data.
        user_id (int): User who owns the job.

    Returns:
    -------
        None

    """
    insert_data = {**job_to_add.model_dump(), "owner_id": user_id}

    do_nothing_stmt = (
        insert(JobModel)
        .values(insert_data)
        .on_conflict_do_nothing(index_elements=["arq_job_id"])
    )

    await db.execute(do_nothing_stmt)
    logger.debug(
        "Attempted insert for job with arq_job_id: %s.",
        job_to_add.arq_job_id,
    )


async def _arq_upsert_job(
    db: AsyncSession, job_data: JobSchema | JobCreateSchema, user_id: int
) -> JobModel:
    """Insert a new job or update an existing one based on arq_job_id.

    **NOTE:** This is only supposed to be used by the ARQ hooks for automatic
    job tracking and updates. It is the responsibility of the caller to commit
    the transaction or rollback in the event of a failure.

    Args:
    ----
        db (AsyncSession): The database session.
        job_data (JobSchema | JobCreateSchema): The job data to insert or update.
        user_id (int): ID of the user who owns the job.

    Returns:
    -------
        JobModel: The inserted or updated job model.

    """
    insert_data = job_data.model_dump()
    update_data = job_data.model_dump(exclude_unset=True)

    # Build initial insert
    insert_stmt = insert(JobModel).values(**insert_data, owner_id=user_id)

    # Build the full "upsert" statement
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["arq_job_id"],
        set_=update_data,
    ).returning(JobModel)

    try:
        logger.debug("Upserting job with arq_job_id: %s", job_data.arq_job_id)
        result = await db.execute(upsert_stmt)
        job_model = result.scalar_one()
        logger.debug("Successfully upserted and flushed job: %s.", job_model.id)
        return job_model
    except SQLAlchemyError:
        logger.exception(
            "Database error while upserting job with arq_job_id: %s",
            job_data.arq_job_id,
        )
        raise
    except Exception:
        logger.exception(
            "Unexpected error while upserting job with arq_job_id: %s.",
            job_data.arq_job_id,
        )
        raise
