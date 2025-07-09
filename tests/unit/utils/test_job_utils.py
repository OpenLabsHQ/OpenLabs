import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from arq import ArqRedis
from arq.jobs import JobDef, JobResult
from arq.jobs import JobStatus as ArqJobStatus
from pytest_mock import MockerFixture

from src.app.enums.job_status import OpenLabsJobStatus
from src.app.schemas.job_schemas import JobCreateSchema
from src.app.utils.job_utils import (
    arq_to_openlabs_job_status,
    enqueue_arq_job,
    get_job_from_redis,
    track_job_status,
    update_job_in_db,
)
from tests.unit.api.v1.config import complete_job_payload


@pytest.fixture
def arq_job_util_path() -> str:
    """Return dot path of ARQ job utility functions."""
    return "src.app.utils.job_utils"


@pytest.fixture
def mock_redis_queue_pool_no_connection(
    monkeypatch: pytest.MonkeyPatch, arq_job_util_path: str
) -> None:
    """Patch the queue.pool object to be None to simulate no connection te Redis."""
    monkeypatch.setattr(f"{arq_job_util_path}.queue.pool", None)


@pytest.fixture
def mock_redis_queue_pool_successful_job_queue(
    monkeypatch: pytest.MonkeyPatch, arq_job_util_path: str
) -> None:
    """Patch the queue.pool object to ensure it passes as a real Redis connection and queues a fake job."""
    fake_redis = AsyncMock(spec=ArqRedis)

    class FakeJob:
        job_id: str = str(uuid.uuid4()).replace("-", "")

    fake_redis.enqueue_job.return_value = FakeJob()

    monkeypatch.setattr(f"{arq_job_util_path}.queue.pool", fake_redis)


@pytest.fixture
def mock_redis_queue_pool_failed_job_queue(
    monkeypatch: pytest.MonkeyPatch, arq_job_util_path: str
) -> None:
    """Patch the queue.pool object to ensure it passes as a real Redis connection and but fails to queue a job."""
    fake_redis = AsyncMock(spec=ArqRedis)

    fake_redis.enqueue_job.return_value = None

    monkeypatch.setattr(f"{arq_job_util_path}.queue.pool", fake_redis)


@pytest.fixture
def mock_successful_fetch_job_info(
    monkeypatch: pytest.MonkeyPatch, arq_job_util_path: str
) -> JobCreateSchema:
    """Patch over the redis job info retrieval utlity function to return a valid job schema."""
    # Mock return value
    mock_job_schema = JobCreateSchema.model_validate(complete_job_payload)

    # Mock function
    mock_get_info_from_redis = AsyncMock()
    mock_get_info_from_redis.return_value = mock_job_schema

    monkeypatch.setattr(
        f"{arq_job_util_path}.get_job_from_redis", mock_get_info_from_redis
    )

    # Patch crud function
    monkeypatch.setattr(f"{arq_job_util_path}._arq_upsert_job", AsyncMock())

    return mock_job_schema


@pytest.fixture
def mock_failed_fetch_job_info(
    monkeypatch: pytest.MonkeyPatch, arq_job_util_path: str
) -> None:
    """Patch over the redis job info retrieval utlity function to return no data."""
    # Mock function failure
    mock_get_info_from_redis = AsyncMock()
    mock_get_info_from_redis.return_value = None

    monkeypatch.setattr(
        f"{arq_job_util_path}.get_job_from_redis", mock_get_info_from_redis
    )


@pytest.fixture
def mock_ctx_dict() -> dict[str, Any]:
    """Return a mock ARQ context dictionary."""
    return {"job_id": uuid.uuid4().hex, "redis": AsyncMock()}


@pytest.fixture
def mock_arq_job(mocker: MockerFixture, arq_job_util_path: str) -> dict[str, Any]:
    """Fixture to mock the ARQ Job class and its info methods."""
    mock_job_instance = AsyncMock()
    mock_job_class = mocker.patch(
        f"{arq_job_util_path}.Job", return_value=mock_job_instance
    )

    # Shared attributes
    function = "test_function"
    job_try = 1
    enqueue_time = datetime.now(timezone.utc)

    # Mock JobDef from job.info()
    mock_job_def = MagicMock(spec=JobDef)
    mock_job_def.function = function
    mock_job_def.job_try = job_try
    mock_job_def.enqueue_time = enqueue_time
    mock_job_instance.info.return_value = mock_job_def

    # Mock JobResult from job.result_info()
    # JobResult inherits from JobDef
    mock_job_result = MagicMock(spec=JobResult)
    mock_job_result.function = function
    mock_job_result.job_try = job_try
    mock_job_result.enqueue_time = enqueue_time
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


async def test_enqueue_arq_job_no_queue_pool_connection(
    mock_redis_queue_pool_no_connection: None,
) -> None:
    """Test that we get nothing back when the worker is not connected to the redis pool."""
    assert await enqueue_arq_job("test_job", user_id=-1) is None


async def test_enqueue_arq_job_fail_to_queue(
    mock_redis_queue_pool_failed_job_queue: None,
) -> None:
    """Test that we get nothing back when it fails to queue the job with ARQ."""
    assert await enqueue_arq_job("test_job", user_id=-1) is None


async def test_enqueue_arq_job_success(
    mock_redis_queue_pool_successful_job_queue: None,
) -> None:
    """Test that we get back a ARQ job ID string when the function exits successfully."""
    assert await enqueue_arq_job("test_job", user_id=-1) is not None


async def test_get_job_from_redis_not_found(
    mock_ctx_dict: dict[str, Any],
    mock_arq_job: dict[str, Any],
) -> None:
    """Test that get_job_from_redis returns None when the job is not found."""
    mock_job_instance = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.not_found

    result = await get_job_from_redis(mock_ctx_dict)
    assert result is None


async def test_get_job_from_redis_no_job_def(
    mock_ctx_dict: dict[str, Any],
    mock_arq_job: dict[str, Any],
) -> None:
    """Test that get_job_from_redis returns None if the job definition is missing."""
    mock_job_instance = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.queued
    mock_job_instance.info.return_value = None  # Simulate missing job definition

    result = await get_job_from_redis(mock_ctx_dict)
    assert result is None


async def test_get_job_from_redis_queued_job(
    mock_ctx_dict: dict[str, Any],
    mock_arq_job: dict[str, Any],
) -> None:
    """Test fetching a queued job from Redis."""
    mock_job_instance: AsyncMock = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.queued

    result = await get_job_from_redis(mock_ctx_dict)

    assert isinstance(result, JobCreateSchema)
    assert result.arq_job_id == mock_ctx_dict["job_id"]

    # Check that we don't call result_info() since the job is not complete yet
    mock_job_instance.result_info.assert_not_awaited()

    # Rely on pydantic to enforce correct queued job state
    assert result.status == OpenLabsJobStatus.QUEUED


async def test_get_job_from_redis_in_progress_job(
    mock_ctx_dict: dict[str, Any],
    mock_arq_job: dict[str, Any],
) -> None:
    """Test fetching an in-progress job from Redis."""
    mock_job_instance: AsyncMock = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.in_progress

    result = await get_job_from_redis(mock_ctx_dict)

    assert isinstance(result, JobCreateSchema)
    assert result.arq_job_id == mock_ctx_dict["job_id"]

    # Check that we don't call result_info() since the job is not complete yet
    mock_job_instance.result_info.assert_not_awaited()

    # Rely on pydantic to enforce correct in_progress job state
    assert result.status == OpenLabsJobStatus.IN_PROGRESS


async def test_get_job_from_redis_completed_successfully(
    mock_ctx_dict: dict[str, Any],
    mock_arq_job: dict[str, Any],
) -> None:
    """Test fetching a successfully completed job from Redis."""
    mock_job_instance: AsyncMock = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.complete

    result = await get_job_from_redis(mock_ctx_dict)

    assert isinstance(result, JobCreateSchema)
    assert result.arq_job_id == mock_ctx_dict["job_id"]

    # Check that we call result_info() since job is complete
    mock_job_instance.result_info.assert_awaited_once()

    # Rely on pydantic to enforce correct complete job state
    assert result.status == OpenLabsJobStatus.COMPLETE


async def test_get_job_from_redis_completed_with_failure(
    mock_ctx_dict: dict[str, Any],
    mock_arq_job: dict[str, Any],
) -> None:
    """Test fetching a failed job from Redis."""
    mock_job_instance = mock_arq_job["job_instance"]
    mock_job_instance.status.return_value = ArqJobStatus.complete

    mock_job_result = mock_arq_job["job_result"]
    mock_job_result.success = False
    error_message = "Something went wrong"
    mock_job_result.result = ValueError(error_message)

    result = await get_job_from_redis(mock_ctx_dict)

    assert isinstance(result, JobCreateSchema)
    assert result.arq_job_id == mock_ctx_dict["job_id"]

    # When there is a failed job (an exception is returned) we return
    # the string representation of the exception
    assert result.error_message == str(mock_job_result.result)

    # Check that we call result_info() since job is complete
    mock_job_instance.result_info.assert_awaited_once()

    # Rely on pydantic to enforce correct failed job state
    assert result.status == OpenLabsJobStatus.FAILED


async def test_update_job_in_db_no_job(
    mock_ctx_dict: dict[str, Any], mock_failed_fetch_job_info: None
) -> None:
    """Test that update job function raises a RuntimeError exception when it fails to fetch a job."""
    with pytest.raises(RuntimeError, match="update job"):
        # We can call the function without the decorator using __wrapped__
        await update_job_in_db.__wrapped__(mock_ctx_dict, user_id=-1)  # type: ignore


async def test_update_job_in_db_success(
    mock_ctx_dict: dict[str, Any],
    mock_successful_fetch_job_info: JobCreateSchema,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that we log the job status update when the function succeeds."""
    # Function should not return any values when it succeeds
    assert await update_job_in_db.__wrapped__(mock_ctx_dict, user_id=-1) is None  # type: ignore

    assert any(
        mock_successful_fetch_job_info.arq_job_id in record.message.lower()
        and mock_successful_fetch_job_info.status.value in record.message.lower()
        for record in caplog.records
    )


async def test_track_job_status_no_user_id(mock_ctx_dict: dict[str, Any]) -> None:
    """Test that the wrapper raises a value error if a user_id is not passed as a kwarg."""

    @track_job_status
    async def dummy_func(ctx: dict[str, Any]) -> None:
        """Fake function for testing the track_job_status wrapper."""
        return

    with pytest.raises(ValueError, match="user_id"):
        await dummy_func(
            mock_ctx_dict,
        )


async def test_track_job_status_success(
    arq_job_util_path: str, mocker: MockerFixture, mock_ctx_dict: dict[str, Any]
) -> None:
    """Test successful excution of track_job_status decorator."""
    # Mock all dependencies
    mock_update_job = mocker.patch(
        f"{arq_job_util_path}.update_job_in_db", new_callable=AsyncMock
    )
    mock_create_task = mocker.patch(f"{arq_job_util_path}.asyncio.create_task")
    mock_sleep = mocker.patch(
        f"{arq_job_util_path}.asyncio.sleep", new_callable=AsyncMock
    )

    expected_result = "Function Result"
    user_id = 123

    @track_job_status
    async def dummy_func(ctx: dict[str, Any], user_id: int) -> str:
        """I should be called and my result returned."""
        return expected_result

    # Call decorated function
    result = await dummy_func(mock_ctx_dict, user_id=user_id)
    assert result == expected_result

    # Two updates for jobs in database
    # 1) Job start --> In progress
    # ~~ Job runs ~~
    # 2) Job end --> Complete/Failed
    assert mock_create_task.call_count == 2  # noqa: PLR2004

    # Check that update_job_in_db was the target of the tasks
    # The ANY is for the captured 'ctx' dict
    mock_update_job.assert_has_calls(
        [
            mocker.call(ANY, user_id),
            mocker.call(ANY, user_id),
        ]
    )

    # Check that the finally block's sleep was called
    mock_sleep.assert_awaited_once_with(1)
