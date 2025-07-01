from datetime import datetime, timezone
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..enums.job_status import OpenLabsJobStatus


class JobCommonSchema(BaseModel):
    """ARQ job common attributes."""

    arq_job_id: str = Field(
        ..., description="ID of the job in ARQ and Redis.", min_length=1
    )
    job_name: str = Field(..., description="Name of the job executed.", min_length=1)
    job_try: int | None = Field(
        default=None, ge=0, description="Number of times task has been attempted."
    )
    enqueue_time: datetime = Field(..., description="When the task was enqueued.")
    start_time: datetime | None = Field(
        default=None, description="Start time of the task."
    )
    finish_time: datetime | None = Field(
        default=None, description="Finish time of the task."
    )
    status: OpenLabsJobStatus = Field(
        ...,
        description="Current status of the task.",
        examples=[
            OpenLabsJobStatus.QUEUED,
            OpenLabsJobStatus.IN_PROGRESS,
            OpenLabsJobStatus.COMPLETE,
            OpenLabsJobStatus.FAILED,
        ],
    )
    result: dict[str, Any] | None = Field(
        default=None, description="Return value of the task, if available."
    )
    error_message: str | None = Field(
        default=None, description="Error message if available."
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
                "must_exist": ["start_time"],
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

    model_config = ConfigDict(from_attributes=True)


class JobSchema(JobCommonSchema):
    """Schema with database ID attribute for ARQ jobs."""

    id: int = Field(..., description="Job unique identifier.")

    model_config = ConfigDict(from_attributes=True)

    def mark_as_in_progress(self, start_time: datetime, job_try: int) -> Self:
        """Return a new Job instance marked as in progress."""
        if self.status != OpenLabsJobStatus.QUEUED:
            msg = f"Cannot mark a '{self.status.value}' job as in progress. Must be queued first!"
            raise ValueError(msg)

        # Dump and instantiate a new model to ensure
        # the new instance is validated
        update_data = self.model_dump()
        update_data.update(
            {
                "status": OpenLabsJobStatus.IN_PROGRESS,
                "start_time": start_time,
                "job_try": job_try,
            }
        )

        return self.model_validate(update_data)

    def mark_as_complete(self, finish_time: datetime, result: dict[str, Any]) -> Self:
        """Return a new Job instance marked as complete."""
        if self.status != OpenLabsJobStatus.IN_PROGRESS:
            msg = f"Cannot mark a '{self.status.value}' job as complete. Must be in progress first!"
            raise ValueError(msg)

        # Dump and instantiate a new model to ensure
        # the new instance is validated
        update_data = self.model_dump()
        update_data.update(
            {
                "status": OpenLabsJobStatus.COMPLETE,
                "finish_time": finish_time,
                "result": result,
            }
        )

        return self.model_validate(update_data)

    def mark_as_failed(self, finish_time: datetime, error_message: str) -> Self:
        """Return a new Job instance marked as failed."""
        if self.status != OpenLabsJobStatus.IN_PROGRESS:
            msg = f"Cannot mark a '{self.status.value}' job as failed. Must be in progress first!"
            raise ValueError(msg)

        # Dump and instantiate a new model to ensure
        # the new instance is validated
        update_data = self.model_dump()
        update_data.update(
            {
                "status": OpenLabsJobStatus.FAILED,
                "finish_time": finish_time,
                "error_message": error_message,
            }
        )

        return self.model_validate(update_data)
