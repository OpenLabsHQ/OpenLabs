from pathlib import Path


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
