from datetime import datetime, timezone


def is_utc_timezone_aware(dt_object: datetime) -> bool:
    """Check if a datetime object is UTC timezone aware.

    Args:
        dt_object: The datetime object to check.

    Returns:
        True if the datetime object is UTC timezone aware, False otherwise.

    """
    return dt_object.tzinfo is not None and dt_object.tzinfo == timezone.utc
