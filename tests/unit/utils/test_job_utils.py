import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from arq.jobs import JobDef, JobResult
from arq.jobs import JobStatus as ArqJobStatus
from pytest_mock import MockerFixture

from src.app.enums.job_status import OpenLabsJobStatus
from src.app.schemas.job_schemas import JobCreateSchema
from src.app.utils.job_utils import (
    arq_to_openlabs_job_status,
    get_job_from_redis,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def arq_job_util_path() -> str:
    """Return dot path of ARQ job utility functions."""
    return "src.app.utils.job_utils"


@pytest.fixture
def mock_arq_job(mocker: MockerFixture, arq_job_util_path: str) -> dict[str, Any]:
    """Fixture to mock the ARQ Job class and its info methods."""
    mock_job_instance = AsyncMock()
    mock_job_class = mocker.patch(
        f"{arq_job_util_path}.Job", return_value=mock_job_instance
    )

    # Mock JobDef from job.info()
    mock_job_def = MagicMock(spec=JobDef)
    mock_job_def.function = "test_function"
    mock_job_def.job_try = 1
    mock_job_def.enqueue_time = datetime.now(timezone.utc)
    mock_job_instance.info.return_value = mock_job_def

    # Mock JobResult from job.result_info()
    mock_job_result = MagicMock(spec=JobResult)
    mock_job_result.success = True
    mock_job_result.start_time = datetime.now(timezone.utc)
    mock_job_result.finish_time = datetime.now(timezone.utc)
    mock_job_result.result = {"detail": "Job completed successfully"}
    mock_job_instance.result_info.return_value = mock_job_result

    return {
        "job_class": mock_job_class,
        "job_instance": mock_job_instance,
        "job_def": mock_job_def,
        "job_result": mock_job_result,
    }


@pytest.mark.parametrize(
    "arq_status, openlabs_status",
    [
        (ArqJobStatus.deferred, OpenLabsJobStatus.QUEUED),
        (ArqJobStatus.queued, OpenLabsJobStatus.QUEUED),
        (ArqJobStatus.in_progress, OpenLabsJobStatus.IN_PROGRESS),
        (ArqJobStatus.not_found, OpenLabsJobStatus.NOT_FOUND),
        ("unknown_status", OpenLabsJobStatus.NOT_FOUND),
    ],
)
def test_arq_to_openlabs_job_status_mapping(
    arq_status: ArqJobStatus | str, openlabs_status: OpenLabsJobStatus
) -> None:
    """Test the mapping of ARQ statuses to OpenLabs statuses."""
    assert arq_to_openlabs_job_status(arq_status) == openlabs_status  # type: ignore


def test_arq_to_openlabs_job_status_complete_success() -> None:
    """Test that a complete and successful ARQ job maps to COMPLETE."""
    mock_result = MagicMock(spec=JobResult)
    mock_result.success = True
    status = arq_to_openlabs_job_status(ArqJobStatus.complete, mock_result)
    assert status == OpenLabsJobStatus.COMPLETE


def test_arq_to_openlabs_job_status_complete_failed() -> None:
    """Test that a complete and non-successful ARQ job maps to FAILED."""
    mock_result = MagicMock(spec=JobResult)
    mock_result.success = False
    status = arq_to_openlabs_job_status(ArqJobStatus.complete, mock_result)
    assert status == OpenLabsJobStatus.FAILED


def test_arq_to_openlabs_job_status_complete_no_result() -> None:
    """Test that a complete ARQ job without a result maps to FAILED."""
    status = arq_to_openlabs_job_status(ArqJobStatus.complete)
    assert status == OpenLabsJobStatus.FAILED


async def test_get_job_from_redis_not_found(
    mock_arq_job: dict[str, Any],
) -> None:
    """Test that get_job_from_redis returns None when the job is not found."""
    mock_job_instance = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.not_found

    result = await get_job_from_redis("non_existent_id", AsyncMock())
    assert result is None


async def test_get_job_from_redis_no_job_def(
    mock_arq_job: dict[str, Any],
) -> None:
    """Test that get_job_from_redis returns None if the job definition is missing."""
    mock_job_instance = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.queued
    mock_job_instance.info.return_value = None  # Simulate missing job definition

    result = await get_job_from_redis("some_id", AsyncMock())
    assert result is None


async def test_get_job_from_redis_queued_job(
    mock_arq_job: dict[str, Any],
) -> None:
    """Test fetching a queued job from Redis."""
    arq_job_id = str(uuid.uuid4())
    mock_job_instance = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.queued

    result = await get_job_from_redis(arq_job_id, AsyncMock())

    assert isinstance(result, JobCreateSchema)
    assert result.arq_job_id == arq_job_id

    # Rely on pydantic to enforce correct queued job state
    assert result.status == OpenLabsJobStatus.QUEUED


async def test_get_job_from_redis_in_progress_job(
    mock_arq_job: dict[str, Any],
) -> None:
    """Test fetching an in-progress job from Redis."""
    arq_job_id = str(uuid.uuid4())
    mock_job_instance = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.in_progress

    # Clear mocked result values to simulate in_progress job
    mock_arq_job["job_result"].finish_time = None
    mock_arq_job["job_result"].success = None
    mock_arq_job["job_result"].result = None

    result = await get_job_from_redis(arq_job_id, AsyncMock())

    assert isinstance(result, JobCreateSchema)
    assert result.arq_job_id == arq_job_id

    # Rely on pydantic to enforce correct in_progress job state
    assert result.status == OpenLabsJobStatus.IN_PROGRESS


async def test_get_job_from_redis_completed_successfully(
    mock_arq_job: dict[str, Any],
) -> None:
    """Test fetching a successfully completed job from Redis."""
    arq_job_id = str(uuid.uuid4())
    mock_job_instance = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.complete

    result = await get_job_from_redis(arq_job_id, AsyncMock())

    assert isinstance(result, JobCreateSchema)
    assert result.arq_job_id == arq_job_id

    # Rely on pydantic to enforce correct complete job state
    assert result.status == OpenLabsJobStatus.COMPLETE


async def test_get_job_from_redis_completed_with_failure(
    mock_arq_job: dict[str, Any],
) -> None:
    """Test fetching a failed job from Redis."""
    arq_job_id = str(uuid.uuid4())
    error_message = "Something went wrong"
    mock_job_instance = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.complete

    mock_job_result = mock_arq_job["job_result"]
    mock_job_result.success = False
    mock_job_result.result = ValueError(error_message)

    result = await get_job_from_redis(arq_job_id, AsyncMock())

    assert isinstance(result, JobCreateSchema)
    assert result.arq_job_id == arq_job_id

    # When there is a failed job (an exception is returned) we return
    # the string representation of the exception
    assert result.error_message == str(mock_job_result.result)

    # Rely on pydantic to enforce correct failed job state
    assert result.status == OpenLabsJobStatus.FAILED
