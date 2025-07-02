import logging
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError

from src.app.crud.crud_jobs import (
    _arq_get_job_by_arq_id,
    _arq_update_job,
    create_job,
    get_job,
    get_jobs,
)
from src.app.enums.job_status import OpenLabsJobStatus
from src.app.models.job_models import JobModel
from src.app.schemas.job_schemas import JobCreateSchema, JobSchema
from tests.unit.api.v1.config import complete_job_payload, failed_job_payload

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

    assert await get_job(dummy_db, job_id=1, user_id=user_id, is_admin=False) is None


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

    result = await get_job(dummy_db, job_id=1, user_id=user_id, is_admin=is_admin)

    assert result is not None, "The function should return the job"
    mock_model_validate.assert_called_once_with(dummy_job)


async def test_get_non_existent_job() -> None:
    """Test that the crud function returns None when the job doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the job doesn't exist
    dummy_db.get.return_value = None

    assert await get_job(dummy_db, job_id=1, user_id=-1) is None


@pytest.mark.parametrize(
    "exception_type",
    [
        SQLAlchemyError,  # DB specific error
        RuntimeError,  # Generic error
    ],
)
async def test_create_job_raises_and_logs_exceptions(
    caplog: pytest.LogCaptureFixture, exception_type: type[Exception]
) -> None:
    """Test that the job creation crud function passes on exceptions and logs them correctly."""
    # 1. Arrange: Set up mocks and test data
    dummy_db = DummyDB()
    schema = JobCreateSchema.model_validate(complete_job_payload)

    # Force a db exception
    error_msg = f"Fake {exception_type.__name__}!"
    dummy_db.flush.side_effect = exception_type(error_msg)

    with pytest.raises(exception_type, match=error_msg):
        await create_job(dummy_db, schema, user_id=1)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and error_msg in record.message
        for record in caplog.records
    ), "The exception was not logged as an error."


async def test_create_job_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the job creation crud function returns a schema when successful."""
    # 1. Arrange: Set up mocks and test data
    dummy_db = DummyDB()
    schema = JobCreateSchema.model_validate(complete_job_payload)

    # Patch over JobSchema validate
    monkeypatch.setattr(JobSchema, "model_validate", lambda *args, **kwargs: schema)

    assert await create_job(dummy_db, schema, user_id=1)

    # Check that the crud function updates the model
    dummy_db.flush.assert_awaited_once()
    dummy_db.refresh.assert_awaited_once()


async def test_get_job_by_arq_id_success() -> None:
    """Tests that a JobModel is returned when the job exists in the database."""
    dummy_db = DummyDB()
    dummy_job = DummyJob()
    arq_job_id = "test-arq-job-id-123"

    # Mock the database execution to return the dummy job
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = dummy_job
    dummy_db.execute.return_value = mock_result

    assert await _arq_get_job_by_arq_id(db=dummy_db, arq_job_id=arq_job_id)

    # Verify filters are correct
    stmt = dummy_db.execute.call_args[0][0]
    where_clause = str(stmt.whereclause)
    expected_clause = str(JobModel.arq_job_id == arq_job_id)
    assert expected_clause in where_clause


async def test_get_job_by_arq_id_non_existent_job() -> None:
    """Tests that None is returned when job is not found in database."""
    dummy_db = DummyDB()
    arq_job_id = "non-existent-arq-id"

    # Force no result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    dummy_db.execute.return_value = mock_result

    assert await _arq_get_job_by_arq_id(db=dummy_db, arq_job_id=arq_job_id) is None


async def test_arq_update_job_success(
    mocker: MockerFixture, crud_jobs_path: str
) -> None:
    """Tests that a job is successfully updated when found."""
    dummy_db = DummyDB()
    existing_job = JobCreateSchema.model_validate(complete_job_payload)
    existing_job_model = JobModel(**existing_job.model_dump(), owner_id=420)

    # Mock the dependency to return the existing job
    mocker.patch(
        f"{crud_jobs_path}._arq_get_job_by_arq_id",
        return_value=existing_job_model,
    )

    job_update_schema = JobSchema.model_validate(failed_job_payload)

    # Simulate updating job to a failed state
    updated_job = await _arq_update_job(db=dummy_db, job_update=job_update_schema)
    assert updated_job

    # Check that the job now has failed job attributes
    assert updated_job.status == job_update_schema.status
    assert not updated_job.result
    assert updated_job.error_message

    dummy_db.flush.assert_awaited_once()
    dummy_db.refresh.assert_awaited_once()


async def test_arq_update_job_not_found_raises_error(
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
    crud_jobs_path: str,
) -> None:
    """Tests that a ValueError is raised if the job to update is not found."""
    dummy_db = DummyDB()

    # Force nothing returned
    mocker.patch(
        f"{crud_jobs_path}._arq_get_job_by_arq_id",
        return_value=None,
    )

    job_update_schema = JobSchema.model_validate(failed_job_payload)

    with pytest.raises(ValueError, match="update job"):
        await _arq_update_job(db=dummy_db, job_update=job_update_schema)


@pytest.mark.parametrize(
    "exception_type",
    [
        SQLAlchemyError,  # DB specific error
        RuntimeError,  # Generic error
    ],
)
async def test_arq_update_job_raises_and_logs_db_exceptions(
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
    exception_type: type[Exception],
    crud_jobs_path: str,
) -> None:
    """Test that the arq job update crud function passes on database exceptions and logs them correctly."""
    dummy_db = DummyDB()
    existing_job = JobCreateSchema.model_validate(complete_job_payload)
    existing_job_model = JobModel(**existing_job.model_dump(), owner_id=420)
    error_msg = f"Fake {exception_type.__name__}!"

    # Force return of job
    mocker.patch(
        f"{crud_jobs_path}._arq_get_job_by_arq_id",
        return_value=existing_job_model,
    )
    job_update_schema = JobSchema.model_validate(failed_job_payload)

    # Force a db exception on flush
    dummy_db.flush.side_effect = exception_type(error_msg)

    # 2. Act & Assert
    with pytest.raises(exception_type, match=error_msg):
        await _arq_update_job(db=dummy_db, job_update=job_update_schema)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and error_msg in record.message
        for record in caplog.records
    ), "The exception was not logged as an error."
