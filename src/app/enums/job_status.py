from enum import Enum


class OpenLabsJobStatus(Enum):
    """OpenLabs ARQ job states."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    NOT_FOUND = "not_found"
