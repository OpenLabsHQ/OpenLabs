import logging
import uuid

# Configure logging
logger = logging.getLogger(__name__)


def is_valid_uuid4(uuid_str: str) -> bool:
    """Check if the string is a valid UUID4.

    Args:
    ----
        uuid_str (str): String to validate as UUID.

    Return:
    ------
        bool: True if string is valid UUID4. False otherwise.

    """
    try:
        # Attempt to create a UUID object from the string.
        u = uuid.UUID(uuid_str)
    except ValueError as e:
        logger.error("Failed to parse UUID: %s. Error: %s", uuid_str, e)
        return False

    # Check if the parsed UUID is version 4.
    uuid_version_4 = 4
    if u.version != uuid_version_4:
        logger.error(
            "UUID version mismatch: expected 4, got %s for UUID: %s",
            u.version,
            uuid_str,
        )
        return False

    return True
