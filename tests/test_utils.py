import logging
import random
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


def rotate_docker_compose_test_log_files(test_output_dir: str) -> None:
    """Rotate and cleanup docker_compose_test_*.log files."""
    logs_to_keep = 5
    log_prefix = "docker_compose_test_"
    logger.info(
        "--- Log Cleanup ---\nRunning log rotation. Keeping the newest %d log(s).",
        logs_to_keep,
    )

    try:
        log_dir = Path(test_output_dir)
        log_files = sorted(
            log_dir.glob(f"{log_prefix}*.log"), reverse=True
        )  # Logs named with YYYY-MM-DD_HH-MM-SS format

        files_to_delete = log_files[logs_to_keep:]

        if not files_to_delete:
            logger.info("No old logs to delete.")
            return

        logger.info("Found %d old log(s) to delete.", len(files_to_delete))
        for log_file in files_to_delete:
            try:
                log_file.unlink()
                logger.debug("Deleted old log file: %s", log_file)
            except OSError as e:
                logger.error("Error deleting file %s: %s", log_file, e)

    except Exception as e:
        logger.error("An unexpected error occurred during log cleanup: %s", e)


def remove_key_recursively(
    data_structure: dict[Any, Any] | list[Any], key_to_remove: str
) -> None:
    """Recursively removes all instances of a specific key from a nested data structure (dictionaries and lists of dictionaries).

    The function modifies the 'data_structure' in-place.

    Args:
    ----
        data_structure: The dictionary or list to process. This could be
                        your main nested dictionary.
        key_to_remove: The string key to search for and remove from
                       any dictionaries found within the structure.

    Returns:
    -------
        None

    """
    if isinstance(data_structure, dict):
        for key in list(data_structure.keys()):
            if key == key_to_remove:
                del data_structure[key]
            else:
                remove_key_recursively(data_structure[key], key_to_remove)
    elif isinstance(data_structure, list):
        for item in data_structure:
            remove_key_recursively(item, key_to_remove)


def add_key_recursively(
    data_structure: dict[Any, Any] | list[Any],
    key_to_add: str,
    value_generator: Callable[[], Any],
) -> None:
    """Recursively adds a specific key with a generated value to all dictionaries within a nested data structure (dictionaries and lists of dictionaries).

    The function modifies the 'data_structure' in-place.

    Args:
    ----
        data_structure: The dictionary or list to process.
        key_to_add: The string key to add to any dictionaries found within the structure.
        value_generator: A function that will be called to generate the value for the new key each time it's added.

    Returns:
    -------
        None

    """
    if isinstance(data_structure, dict):
        data_structure[key_to_add] = value_generator()
        for key in data_structure:
            # Avoid adding the key to the value we just added if it's also a dict
            if key != key_to_add or not isinstance(data_structure[key], dict):
                add_key_recursively(data_structure[key], key_to_add, value_generator)
    elif isinstance(data_structure, list):
        for item in data_structure:
            add_key_recursively(item, key_to_add, value_generator)


def generate_random_int(lower_bound: int = 1, upper_bound: int = 100) -> int:
    """Generate random ints `lower_bound` <= int <= `upper_bound`.

    Args:
    ----
        lower_bound (int): Lower bound of random ints generated.
        upper_bound (int): Upper bound of random ints generated.

    Returns:
    -------
        int: Randomly generated `lower_bound` <= int <= `upper_bound`.

    """
    return random.randint(lower_bound, upper_bound)  # noqa: S311
