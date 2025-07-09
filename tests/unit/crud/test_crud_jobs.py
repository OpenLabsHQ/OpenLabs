import logging
import uuid
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from src.app.crud.crud_jobs import (
    _arq_upsert_job,
    add_job,
    get_job,
    get_jobs,
)
from src.app.enums.job_status import OpenLabsJobStatus
from src.app.models.job_models import JobModel
from src.app.schemas.job_schemas import JobCreateSchema, JobSchema

from .crud_mocks import DummyDB, DummyJob

pytestmark = pytest.mark.unit


@pytest.fixture
def crud_jobs_path() -> str:
    """Return the dot path of the tested crud jobs file."""
    return "src.app.crud.crud_jobs"


@pytest.mark.parametrize(
    "is_admin, expect_owner_filter",
    [
        (False, True),  # Non-admins
        (True, False),  # Admins
    ],
)
async def test_get_all_jobs_permission_filters(
    is_admin: bool, expect_owner_filter: bool
) -> None:
    """Tests that job queries are correctly filtered by owner based on admin status.

    Non-admins filtered by their user ID. Admins see all jobs without the owner filter.
    """
    dummy_db = DummyDB()

    # Configure database return values
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    dummy_db.execute.return_value = mock_result

    user_id = 123
    await get_jobs(dummy_db, user_id=user_id, is_admin=is_admin, status=None)

    stmt = dummy_db.execute.call_args[0][0]
    where_clause = str(stmt.whereclause)
    owner_clause = str(JobModel.owner_id == user_id)

    assert (owner_clause in where_clause) == expect_owner_filter


@pytest.mark.parametrize(
    "status, expect_status_filter",
    [
        (OpenLabsJobStatus.IN_PROGRESS, True),
        (None, False),
    ],
)
async def test_get_all_jobs_status_filter(
    status: OpenLabsJobStatus | None, expect_status_filter: bool
) -> None:
    """Tests that job queries are correctly filtered by status."""
    dummy_db = DummyDB()

    # Configure database return values
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    dummy_db.execute.return_value = mock_result

    # Call the function with is_admin=True to isolate the status filter logic
    await get_jobs(dummy_db, user_id=123, is_admin=True, status=status)

    stmt = dummy_db.execute.call_args[0][0]
    where_clause = str(stmt.whereclause)

    if expect_status_filter:
        status_clause = str(JobModel.status == status)
        assert status_clause in where_clause
    else:
        assert "status" not in where_clause


async def test_no_get_unauthorized_jobs() -> None:
    """Test that the crud function returns none when the user doesn't own the job."""
    dummy_db = DummyDB()
    dummy_job = DummyJob()

    # Ensure that User's ID doesn't match the job's owner
    user_id = 1
    dummy_job.owner_id = user_id + 1
    assert user_id != dummy_job.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_job

    assert await get_job(dummy_db, 1, user_id, is_admin=False) is None


@pytest.mark.parametrize(
    "is_admin, is_owner",
    [
        (False, True),  # User access owned job
        (True, False),  # Admin access another user's job
        (True, True),  # Admin access their own job
    ],
)
async def test_get_job_range_permissions(
    mocker: MockerFixture, is_admin: bool, is_owner: bool
) -> None:
    """Tests that a job is returned when access is allowed.

    Access only allowed when the user owns the job or is an admin.
    """
    dummy_db = DummyDB()
    dummy_job = DummyJob()
    user_id = 1

    # Set the owner ID based on scenario
    dummy_job.owner_id = user_id if is_owner else user_id + 1

    dummy_db.get.return_value = dummy_job
    mock_model_validate = mocker.patch.object(
        JobSchema, "model_validate", return_value=dummy_job
    )

    result = await get_job(dummy_db, 1, user_id, is_admin=is_admin)

    assert result is not None, "The function should return the job"
    mock_model_validate.assert_called_once_with(dummy_job)


async def test_get_non_existent_job() -> None:
    """Test that the crud function returns None when the job doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the job doesn't exist
    dummy_db.get.return_value = None

    assert await get_job(dummy_db, 1, user_id=-1) is None


async def test_get_job_by_primary_key(mocker: MockerFixture) -> None:
    """Test getting a job by its integer primary key."""
    dummy_db = DummyDB()
    dummy_job = DummyJob()
    user_id = 54
    job_id = 45
    dummy_job.owner_id = user_id
    dummy_db.get.return_value = dummy_job

    mock_model_validate = mocker.patch.object(
        JobSchema, "model_validate", return_value=dummy_job
    )

    result = await get_job(dummy_db, job_id, user_id)

    # Check we are retrieving with .get()
    assert result is not None
    mock_model_validate.assert_called_once_with(dummy_job)
    dummy_db.get.assert_awaited_once_with(JobModel, job_id)


async def test_get_job_by_arq_id(mocker: MockerFixture) -> None:
    """Test getting a job by its ARQ job ID."""
    dummy_db = DummyDB()
    dummy_job = DummyJob()
    user_id = 54
    arq_job_id = uuid.uuid4().hex
    dummy_job.owner_id = user_id

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = dummy_job
    dummy_db.execute.return_value = mock_result

    mock_model_validate = mocker.patch.object(
        JobSchema, "model_validate", return_value=dummy_job
    )

    result = await get_job(dummy_db, arq_job_id, user_id)

    assert result is not None
    mock_model_validate.assert_called_once_with(dummy_job)
    dummy_db.execute.assert_awaited_once()

    # Check the query is filtering by ARQ job ID
    stmt = dummy_db.execute.call_args[0][0]
    where_clause = str(stmt.whereclause)
    assert "arq_job_id" in where_clause


async def test_add_job_defers_on_conflict() -> None:
    """Test that the add job crud function defers on a conflict when inserting."""
    dummy_db = DummyDB()
    user_id = 123
    job_to_add = JobCreateSchema.create_queued(
        job_name="test_job", arq_job_id=uuid.uuid4().hex
    )

    await add_job(dummy_db, job_to_add, user_id)

    dummy_db.execute.assert_called_once()
    stmt = dummy_db.execute.call_args[0][0]

    stmt_str = str(stmt.compile(dialect=postgresql.dialect())).lower()  # type: ignore

    # Check the function defers on conflict
    assert "on conflict" in stmt_str
    assert "do nothing" in stmt_str


async def test_arq_upsert_job_updates_on_conflict() -> None:
    """Test that the ARQ upsert crud function updates on conflict."""
    dummy_db = DummyDB()
    dummy_job = DummyJob()
    dummy_job.id = 456

    # Mock db interaction
    mock_result = dummy_db.execute.return_value
    mock_result.scalar_one = MagicMock(return_value=dummy_job)

    user_id = 123
    job_data = JobCreateSchema.create_queued(
        job_name="test_job", arq_job_id=uuid.uuid4().hex
    )

    await _arq_upsert_job(dummy_db, job_data, user_id)

    # 3. Verification
    dummy_db.execute.assert_called_once()
    stmt = dummy_db.execute.call_args[0][0]
    stmt_str = str(stmt.compile(dialect=postgresql.dialect())).lower()  # type: ignore

    # Check we are updating on conflict
    assert "on conflict" in stmt_str
    assert "do update" in stmt_str


@pytest.mark.parametrize(
    "exception_to_raise",
    [
        SQLAlchemyError("Database connection failed"),
        RuntimeError("An unexpected runtime error"),
    ],
    ids=["sqlalchemy_error", "generic_error"],
)
async def test_arq_upsert_job_logs_and_raises_exceptions(
    caplog: pytest.LogCaptureFixture,
    exception_to_raise: Exception,
) -> None:
    """Test that the ARQ upsert crud function properly logs exceptions."""
    dummy_db = DummyDB()
    job_data = JobCreateSchema.create_queued(
        job_name="test_job", arq_job_id=uuid.uuid4().hex
    )
    user_id = 456

    # Raise an exception
    dummy_db.execute.side_effect = exception_to_raise

    # Check that it properly reraises the exception
    with pytest.raises(type(exception_to_raise), match=str(exception_to_raise)):
        await _arq_upsert_job(db=dummy_db, job_data=job_data, user_id=user_id)

    # Get the exception log
    error_log = next((r for r in caplog.records if r.levelno == logging.ERROR), None)

    # Verify that the logging was done correctly
    assert error_log is not None, "An error should have been logged."
    assert job_data.arq_job_id in error_log.message
    assert error_log.exc_info is not None, "Error log is missing exception trackback."
