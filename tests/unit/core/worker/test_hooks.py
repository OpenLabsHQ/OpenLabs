import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from arq import ArqRedis
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from src.app.core.worker.hooks import after_job_end, on_job_start, shutdown, startup
from src.app.enums.job_status import OpenLabsJobStatus
from src.app.models.job_models import JobModel
from src.app.schemas.job_schemas import JobSchema
from tests.unit.api.v1.config import in_progress_job_payload, queued_job_payload

pytestmark = pytest.mark.unit


@pytest.fixture
def arq_hook_path() -> str:
    """Return dot path of ARQ worker hook functions."""
    return "src.app.core.worker.hooks"


@pytest.fixture
def mock_context() -> dict[str, Any]:
    """Generate a randomized ARQ context dictionary."""
    arq_job_id = str(uuid.uuid4()).replace("-", "")
    job_try = random.randint(1, 100)  # noqa: S311
    fake_redis = AsyncMock(spec=ArqRedis)
    return {"job_id": arq_job_id, "job_try": job_try, "redis": fake_redis}


@pytest.fixture
def mock_arq_hook_on_job_start_success(
    mocker: MockerFixture, arq_hook_path: str
) -> dict[str, MagicMock | AsyncMock]:
    """Patch over all external dependencies to ensure that the on_job_start hook returns as if successful."""
    # Patch database connection
    mocker.patch(f"{arq_hook_path}.get_db_session_context")

    # Force return of a job
    existing_job = JobSchema.model_validate(queued_job_payload)
    existing_job_model = JobModel(
        **existing_job.model_dump(exclude={"id"}), owner_id=420
    )
    existing_job_model.id = existing_job.id
    mock_get_job = mocker.patch(
        f"{arq_hook_path}._arq_get_job_by_arq_id",
        return_value=existing_job_model,
    )

    # Force update to be successful
    mock_update_job = mocker.patch(
        f"{arq_hook_path}._arq_update_job",
        return_value=existing_job_model,  # Just need a truthy return value
    )

    return {
        "get_job": mock_get_job,
        "update_job": mock_update_job,
    }


@pytest.fixture
def mock_arq_hook_after_job_end_success(
    mocker: MockerFixture, arq_hook_path: str
) -> dict[str, MagicMock | AsyncMock]:
    """Patches all external dependencies for the after_job_end hook.

    Returns:
        dict[str, Any]: Dictionary containing the core mocks for further configuration.

    """
    # Patch database
    mocker.patch(f"{arq_hook_path}.get_db_session_context")

    # Mock fake redis results
    mock_result_info = MagicMock()
    mock_result_info.success = True
    mock_result_info.finish_time = datetime.now(tz=timezone.utc)
    mock_result_info.result = {"status": "awesome"}

    # Mock fake ARQ Job instance
    mock_arq_job_instance = AsyncMock()
    mock_arq_job_instance.result_info.return_value = mock_result_info
    mocker.patch(f"{arq_hook_path}.Job", return_value=mock_arq_job_instance)

    # Force return of a job
    existing_job = JobSchema.model_validate(in_progress_job_payload)
    existing_job_model = JobModel(
        **existing_job.model_dump(exclude={"id"}), owner_id=420
    )
    existing_job_model.id = existing_job.id
    mock_get_job = mocker.patch(
        f"{arq_hook_path}._arq_get_job_by_arq_id",
        return_value=existing_job_model,
    )

    # Force update to be successful
    mock_update_job = mocker.patch(
        f"{arq_hook_path}._arq_update_job",
        return_value=existing_job_model,
    )

    return {
        "get_job": mock_get_job,
        "update_job": mock_update_job,
        "result_info": mock_result_info,
        "arq_job_instance": mock_arq_job_instance,
    }


async def test_arq_hook_startup_log(caplog: pytest.LogCaptureFixture) -> None:
    """Test that something gets logged when an ARQ worker starts."""
    fake_context = {"blah": "Blah"}

    await startup(fake_context)

    # Look for something that says "start"
    startup_msg = "start"

    assert any(
        record.levelno == logging.INFO and startup_msg in record.message.lower()
        for record in caplog.records
    ), "Nothing was logged in the ARQ startup function."


async def test_arq_hook_shutdown_log(caplog: pytest.LogCaptureFixture) -> None:
    """Test that something gets logged when an ARQ worker shutsdown."""
    fake_context = {"blah": "Blah"}

    await shutdown(fake_context)

    # Look for something that says "stop"
    shutdown_msg = "stop"

    assert any(
        record.levelno == logging.INFO and shutdown_msg in record.message.lower()
        for record in caplog.records
    ), "Nothing was logged in the ARQ shutdown function."


async def test_arq_hook_shutdown_dispose_db(
    monkeypatch: pytest.MonkeyPatch, arq_hook_path: str
) -> None:
    """Test that the shutdown hook disposes of the database engine."""
    fake_context = {"blah": "Blah"}

    # Patch over real engine
    mock_async_engine = AsyncMock(spec=AsyncEngine)
    mock_dispose = AsyncMock()
    mock_async_engine.dispose = mock_dispose
    monkeypatch.setattr(f"{arq_hook_path}.async_engine", mock_async_engine)

    await shutdown(fake_context)

    # Ensure we dispose
    mock_dispose.assert_awaited_once()


async def test_arq_hook_on_job_start_successful(
    mock_arq_hook_on_job_start_success: dict[str, Any],
    mock_context: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that on_job_start hook returns successfully and logs the in_progress job update."""
    await on_job_start(mock_context)

    status_update_msg = OpenLabsJobStatus.IN_PROGRESS.value.lower()

    assert any(
        record.levelno == logging.INFO and status_update_msg in record.message.lower()
        for record in caplog.records
    ), "Job status update was not logged in the on_start_job ARQ hook."


async def test_arq_hook_on_job_start_non_existent_job_in_db(
    mock_arq_hook_on_job_start_success: dict[str, Any],
    mocker: MockerFixture,
    mock_context: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
    arq_hook_path: str,
) -> None:
    """Test that on_job_start hook logs when the job doesn't exist in the database."""
    # Force no job found in database
    get_job_mock = mock_arq_hook_on_job_start_success["get_job"]
    get_job_mock.return_value = None

    await on_job_start(mock_context)

    arq_job_id = mock_context["job_id"]

    assert any(
        record.levelno == logging.ERROR and arq_job_id in record.message.lower()
        for record in caplog.records
    ), "Non-existent job failure was not logged in the on_start_job ARQ hook."


async def test_arq_hook_on_job_start_update_db_exception(
    mock_arq_hook_on_job_start_success: dict[str, Any],
    mocker: MockerFixture,
    mock_context: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
    arq_hook_path: str,
) -> None:
    """Test that on_job_start hook logs and re-raises the database exception."""
    exception_type = SQLAlchemyError
    exception_msg = "Fake DB error."

    # Force a database exception
    update_job_mock = mock_arq_hook_on_job_start_success["update_job"]
    update_job_mock.side_effect = exception_type(exception_msg)

    with pytest.raises(exception_type, match=exception_msg):
        await on_job_start(mock_context)

    # Ensure that we properly log db exceptions
    assert any(
        record.levelno == logging.ERROR and record.exc_info is not None
        for record in caplog.records
    ), "Database exception was not logged in on_job_start."


async def test_arq_hook_on_job_start_update_db_failed(
    mock_arq_hook_on_job_start_success: dict[str, Any],
    mocker: MockerFixture,
    mock_context: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
    arq_hook_path: str,
) -> None:
    """Test that on_job_start hook logs when the job update fails."""
    update_job_mock = mock_arq_hook_on_job_start_success["update_job"]
    update_job_mock.return_value = None

    await on_job_start(mock_context)

    expected_msg = "update"
    assert any(
        record.levelno == logging.ERROR and expected_msg in record.message.lower()
        for record in caplog.records
    )


async def test_arq_hook_after_job_end_successful_completion(
    mock_arq_hook_after_job_end_success: dict[str, Any],
    mock_context: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that after_job_end hook marks a job as complete and logs the update."""
    await after_job_end(mock_context)

    status_update_msg = OpenLabsJobStatus.COMPLETE.value.lower()
    assert any(
        record.levelno == logging.INFO and status_update_msg in record.message.lower()
        for record in caplog.records
    ), "Successful job completion was not logged in after_job_end."


async def test_arq_hook_after_job_end_successful_failure(
    mock_arq_hook_after_job_end_success: dict[str, Any],
    mock_context: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that after_job_end hook marks a job as failed when the job fails."""
    # Force job failed result
    result_info_mock = mock_arq_hook_after_job_end_success["result_info"]
    result_info_mock.success = False
    result_info_mock.result = "Something went very wrong during execution"

    await after_job_end(mock_context)

    status_update_msg = OpenLabsJobStatus.FAILED.value.lower()
    assert any(
        record.levelno == logging.INFO and status_update_msg in record.message.lower()
        for record in caplog.records
    ), "Failed job status was not logged correctly in after_job_end."


async def test_arq_hook_after_job_end_no_result_info(
    mock_arq_hook_after_job_end_success: dict[str, Any],
    mock_context: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that after_job_end hook logs an error if job info is not in Redis."""
    # Force job missing in redis
    arq_job_instance_mock = mock_arq_hook_after_job_end_success["arq_job_instance"]
    arq_job_instance_mock.result_info.return_value = None
    arq_job_id = mock_context["job_id"]

    await after_job_end(mock_context)

    expected_msg = "result info"
    assert any(
        record.levelno == logging.ERROR
        and expected_msg in record.message.lower()
        and arq_job_id in record.message
        for record in caplog.records
    ), "Missing Redis job info error was not logged in after_job_end."


async def test_arq_hook_after_job_end_non_existent_job_in_db(
    mock_arq_hook_after_job_end_success: dict[str, Any],
    mock_context: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that after_job_end hook logs an error if the job is not in the database."""
    # Force job not found in database
    get_job_mock = mock_arq_hook_after_job_end_success["get_job"]
    get_job_mock.return_value = None
    arq_job_id = mock_context["job_id"]

    await after_job_end(mock_context)

    expected_msg = "fetch job"
    assert any(
        record.levelno == logging.ERROR
        and expected_msg in record.message.lower()
        and arq_job_id in record.message
        for record in caplog.records
    ), "Missing database job error was not logged in after_job_end."


async def test_arq_hook_after_job_end_update_db_exception(
    mock_arq_hook_after_job_end_success: dict[str, Any],
    mock_context: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that after_job_end hook logs and re-raises a database exception."""
    # Force database exception when updating job
    exception_type = SQLAlchemyError
    exception_msg = "Fake DB error on update."

    update_job_mock = mock_arq_hook_after_job_end_success["update_job"]
    update_job_mock.side_effect = exception_type(exception_msg)

    with pytest.raises(exception_type, match=exception_msg):
        await after_job_end(mock_context)

    assert any(
        record.levelno == logging.ERROR and record.exc_info is not None
        for record in caplog.records
    ), "Database exception was not logged in after_job_end."


async def test_arq_hook_after_job_end_update_db_failed(
    mock_arq_hook_after_job_end_success: dict[str, Any],
    mock_context: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that after_job_end hook logs an error when the job update fails (returns None)."""
    # Force failed update
    update_job_mock = mock_arq_hook_after_job_end_success["update_job"]
    update_job_mock.return_value = None

    await after_job_end(mock_context)

    expected_msg = "update"
    assert any(
        record.levelno == logging.ERROR and expected_msg in record.message.lower()
        for record in caplog.records
    ), "A failed database update was not logged in after_job_end."
