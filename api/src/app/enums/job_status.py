from enum import Enum


class OpenLabsJobStatus(Enum):
    """OpenLabs ARQ job states."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    NOT_FOUND = "not_found"


class JobSubmissionDetail(Enum):
    """Job submission detail messages."""

    DB_SAVE_SUCCESS = "Job accepted and initial status recorded."
    DB_SAVE_FAILURE = "Job accepted, status will be available shortly."
