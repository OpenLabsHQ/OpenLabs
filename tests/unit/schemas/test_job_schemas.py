import copy
import re
from datetime import datetime, timedelta, timezone
from typing import Any, get_args, get_origin

import pytest
from pydantic import ValidationError

from src.app.enums.job_status import OpenLabsJobStatus
from src.app.schemas.job_schemas import JobCommonSchema
from tests.unit.api.v1.config import (
    complete_job_payload,
    failed_job_payload,
    in_progress_job_payload,
    queued_job_payload,
)

ARQ_TIMESTAMPS = ["enqueue_time", "start_time", "finish_time"]

JOB_STATE_MUST_EXIST_PARAMS = [
    (OpenLabsJobStatus.COMPLETE, "start_time"),
    (OpenLabsJobStatus.COMPLETE, "finish_time"),
    (OpenLabsJobStatus.COMPLETE, "result"),
    (OpenLabsJobStatus.FAILED, "start_time"),
    (OpenLabsJobStatus.FAILED, "finish_time"),
    (OpenLabsJobStatus.FAILED, "error_message"),
]

JOB_STATE_MUST_BE_NONE_PARAMS = [
    (OpenLabsJobStatus.QUEUED, "start_time"),
    (OpenLabsJobStatus.QUEUED, "finish_time"),
    (OpenLabsJobStatus.QUEUED, "result"),
    (OpenLabsJobStatus.QUEUED, "error_message"),
    (OpenLabsJobStatus.IN_PROGRESS, "finish_time"),
    (OpenLabsJobStatus.IN_PROGRESS, "result"),
    (OpenLabsJobStatus.IN_PROGRESS, "error_message"),
    (OpenLabsJobStatus.COMPLETE, "error_message"),
    (OpenLabsJobStatus.FAILED, "result"),
]

VALID_JOB_PAYLOADS: dict[OpenLabsJobStatus, dict[str, Any]] = {
    OpenLabsJobStatus.QUEUED: queued_job_payload,
    OpenLabsJobStatus.IN_PROGRESS: in_progress_job_payload,
    OpenLabsJobStatus.COMPLETE: complete_job_payload,
    OpenLabsJobStatus.FAILED: failed_job_payload,
}


@pytest.mark.parametrize("attr", ARQ_TIMESTAMPS)
def test_job_common_schema_timestamp_has_timezone(attr: str) -> None:
    """Test that the timestamp datetime attributes are enforced to be timezone aware."""
    job_dict = copy.deepcopy(complete_job_payload)

    # Update attribute
    non_timezone_datetime = datetime.now()  # noqa: DTZ005
    job_dict[attr] = non_timezone_datetime.isoformat()

    with pytest.raises(ValidationError, match="timezone-aware"):
        JobCommonSchema.model_validate(job_dict)


@pytest.mark.parametrize("attr", ARQ_TIMESTAMPS)
def test_job_common_schema_timestamp_utc_timezone(attr: str) -> None:
    """Test that the timestamp datetime attributes are enforced to be UTC timezone."""
    job_dict = copy.deepcopy(complete_job_payload)

    # Hello from europe ;)
    cet_offset = timedelta(hours=1)
    cet_tz = timezone(cet_offset, name="CET")

    # Update attribute
    non_utc_datetime = datetime.now(tz=cet_tz)
    job_dict[attr] = non_utc_datetime.isoformat()

    with pytest.raises(ValidationError, match="UTC"):
        JobCommonSchema.model_validate(job_dict)


@pytest.mark.parametrize(
    "invalid_time_attr, base_time_attr",
    [
        ("start_time", "enqueue_time"),
        ("finish_time", "start_time"),
    ],
)
def test_job_common_schema_invalid_time_order(
    invalid_time_attr: str, base_time_attr: str
) -> None:
    """Test that job timestamps follow a logical order."""
    job_dict = copy.deepcopy(complete_job_payload)

    # Check base timestamp exists
    assert job_dict.get(base_time_attr) is not None

    # Build the invalid timestamp (1 sec earlier)
    base_time = datetime.fromisoformat(job_dict[base_time_attr])  # type: ignore
    invalid_time = base_time - timedelta(seconds=1)

    job_dict[invalid_time_attr] = invalid_time.isoformat()

    with pytest.raises(ValidationError):
        JobCommonSchema.model_validate(job_dict)


@pytest.mark.parametrize("invalid_job_try", [None, 0])
@pytest.mark.parametrize(
    "status",
    [
        OpenLabsJobStatus.IN_PROGRESS,
        OpenLabsJobStatus.COMPLETE,
        OpenLabsJobStatus.FAILED,
    ],
)
def test_job_common_schema_invalid_job_tries(
    status: OpenLabsJobStatus, invalid_job_try: int | None
) -> None:
    """Test that job tries are integer values and at least 1 when a job has one of the follow statuses."""
    job_dict = copy.deepcopy(complete_job_payload)

    job_dict["job_try"] = invalid_job_try

    with pytest.raises(ValidationError, match="try count"):
        JobCommonSchema.model_validate(job_dict)


@pytest.mark.parametrize("status, field", JOB_STATE_MUST_EXIST_PARAMS)
def test_job_common_schema_invalid_state_must_exist(
    status: OpenLabsJobStatus, field: str
) -> None:
    """Test that a validation error is raised when a required field is missing for a given job status."""
    job_dict = copy.deepcopy(VALID_JOB_PAYLOADS[status])

    # Remove required field
    job_dict[field] = None

    # Check status and field are mentioned
    error_pattern = f"{re.escape(status.value)}.*{re.escape(field)}"

    with pytest.raises(ValidationError, match=error_pattern):
        JobCommonSchema.model_validate(job_dict)


@pytest.mark.parametrize("status, field", JOB_STATE_MUST_BE_NONE_PARAMS)
def test_job_common_schema_invalid_state_must_be_none(
    status: OpenLabsJobStatus, field: str
) -> None:
    """Test that a validation error is raised when a forbidden field is present for specific job status."""
    job_dict = copy.deepcopy(VALID_JOB_PAYLOADS[status])

    # Get the fields type
    field_annotation = JobCommonSchema.model_fields[field].annotation

    # Handle the union field types (type1 | type2)
    base_types = get_args(field_annotation)
    if not base_types:  # Non-union types
        base_types = (field_annotation,)

    is_datetime = any(t is datetime for t in base_types)
    is_dict = any(t is dict or get_origin(t) is dict for t in base_types)
    is_str = any(t is str for t in base_types)

    # Add data to required none fields
    if is_datetime:
        job_dict[field] = datetime.now(timezone.utc).isoformat()
    elif is_dict:
        job_dict[field] = {"data": "some forbidden result"}
    elif is_str:
        job_dict[field] = "forbidden string"
    else:
        pytest.fail(f"Test case not configured for type: {field_annotation}")

    # Check that status and field are mentioned
    error_pattern = f"{re.escape(status.value)}.*{re.escape(field)}"

    with pytest.raises(ValidationError, match=error_pattern):
        JobCommonSchema.model_validate(job_dict)
