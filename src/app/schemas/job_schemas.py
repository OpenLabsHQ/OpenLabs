from datetime import datetime, timezone
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..enums.job_status import OpenLabsJobStatus


class JobCommonSchema(BaseModel):
    """ARQ job common attributes."""

    arq_job_id: str = Field(
        ..., description="ID of the job in ARQ and Redis.", min_length=1
    )
    job_name: str = Field(
        ..., description="Name of the ARQ job executed.", min_length=1
    )
    job_try: int | None = Field(
        default=None, ge=0, description="Number of times job has been attempted."
    )
    enqueue_time: datetime = Field(..., description="When the job was queued.")
    start_time: datetime | None = Field(
        default=None, description="Start time of the job."
    )
    finish_time: datetime | None = Field(
        default=None, description="Finish time of the job."
    )
    status: OpenLabsJobStatus = Field(
        ...,
        description="Current status of the job.",
        examples=[
            OpenLabsJobStatus.QUEUED,
            OpenLabsJobStatus.IN_PROGRESS,
            OpenLabsJobStatus.COMPLETE,
            OpenLabsJobStatus.FAILED,
        ],
    )
    result: dict[str, Any] | None = Field(
        default=None,
        description="Return value of the job. Only available for complete jobs.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if job failed. Only available for failed jobs.",
    )

    @field_validator("enqueue_time", "start_time", "finish_time")
    @classmethod
    def ensure_utc(cls, timestamp: datetime | None) -> datetime | None:
        """Ensure datetime timestamp fields are timezone-aware and in UTC."""
        if timestamp is None:
            # Allow optional fields to be None
            return timestamp

        if timestamp.tzinfo is None:
            msg = "Datetime must be timezone-aware"
            raise ValueError(msg)

        if timestamp.utcoffset() != timezone.utc.utcoffset(None):
            msg = "Datetime must be in UTC"
            raise ValueError(msg)

        return timestamp

    @model_validator(mode="after")
    def validate_time_order(self) -> Self:
        """Verify logical ordering of enqueue, start, and finish times."""
        if (self.start_time and self.enqueue_time) and (
            self.start_time < self.enqueue_time
        ):
            msg = "Job start time cannot be before enqueue time."
            raise ValueError(msg)
        if (self.finish_time and self.start_time) and (
            self.finish_time < self.start_time
        ):
            msg = "Job finish time cannot be before start time."
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_job_tries(self) -> Self:
        """Validate that the job tries are logically valid with job status."""
        if self.status in {
            OpenLabsJobStatus.IN_PROGRESS,
            OpenLabsJobStatus.COMPLETE,
            OpenLabsJobStatus.FAILED,
        } and (self.job_try is None or self.job_try < 1):
            msg = f"'{self.status.value}' jobs must have a try count of 1 or greater."
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def validate_job_state(self) -> Self:
        """Verify that the job is in a valid state.

        Ensures consistency between job status and other dependent values.
        """
        validation_matrix = {
            OpenLabsJobStatus.QUEUED: {
                "must_be_none": [
                    "start_time",
                    "finish_time",
                    "result",
                    "error_message",
                ],
            },
            OpenLabsJobStatus.IN_PROGRESS: {
                "must_be_none": ["finish_time", "result", "error_message"],
            },
            OpenLabsJobStatus.COMPLETE: {
                "must_exist": ["start_time", "finish_time", "result"],
                "must_be_none": ["error_message"],
            },
            OpenLabsJobStatus.FAILED: {
                "must_exist": ["start_time", "finish_time", "error_message"],
                "must_be_none": ["result"],
            },
        }

        rules = validation_matrix.get(self.status)
        if rules:
            # Must have values
            for field in rules.get("must_exist", []):
                if getattr(self, field) is None:
                    msg = f"'{self.status.value}' jobs must have a '{field}'."
                    raise ValueError(msg)

            # Can't exist values
            for field in rules.get("must_be_none", []):
                if getattr(self, field) is not None:
                    msg = f"'{self.status.value}' jobs cannot have a '{field}'."
                    raise ValueError(msg)

        return self


class JobCreateSchema(JobCommonSchema):
    """Schema for inserting ARQ jobs into the database.

    Lacks database ID attribute.
    """

    @classmethod
    def create_queued(cls, *, arq_job_id: str, job_name: str) -> Self:
        """Create a new job instance with a 'queued' status.

        Args:
        ----
            arq_job_id (str): The job ID from ARQ.
            job_name (str): The name of the job function.

        Returns:
        -------
            Self: A new, validated JobCreateSchema instance.

        """
        return cls(
            arq_job_id=arq_job_id,
            job_name=job_name,
            enqueue_time=datetime.now(timezone.utc),
            status=OpenLabsJobStatus.QUEUED,
        )

    model_config = ConfigDict(from_attributes=True)


class JobSchema(JobCommonSchema):
    """Schema with database ID attribute for ARQ jobs."""

    id: int = Field(..., description="Job unique identifier.")

    model_config = ConfigDict(from_attributes=True)


class JobSubmissionResponseSchema(BaseModel):
    """Response schema for endpoints that submit ARQ job."""

    arq_job_id: str = Field(
        ..., description="ID of the job in ARQ and Redis.", min_length=1
    )
    detail: str = Field(..., description="Details about job submission.", min_length=1)
