import logging
import socket
from pathlib import Path

logger = logging.getLogger(__name__)


def get_free_port() -> int:
    """Get an unused port on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


def find_git_root(marker: str = ".git") -> Path:
    """Find the absolute path of a git repo.

    Starts from the current file's directory and travels up the tree looking for a '.git' or marker directory.

    Returns:
        The absolute Path object for the Git root.

    Raises:
        RuntimeError: If the traversal reaches the filesystem root without finding the .git directory.

    """
    # Start at current directory of this util file which
    # should prevent walking out of the OpenLabs repo unless
    # something goes very very wrong
    current_path = Path(__file__).resolve().parent

    # Move up one directory tree
    while current_path.parent != current_path:
        if (current_path / marker).exists():
            return current_path
        current_path = current_path.parent

    # Check the final path as well
    if (current_path / marker).exists():
        return current_path

    msg = f"Could not find the root of the Git repository containing marker: {marker}."
    raise RuntimeError(msg)


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
