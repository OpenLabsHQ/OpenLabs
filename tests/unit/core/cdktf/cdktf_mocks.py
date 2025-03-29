import io
import subprocess
from typing import Any
from unittest.mock import MagicMock


class DummyPath:
    """Dummy path object class for testing."""

    def __init__(self) -> None:
        """Initialize dummy path object class."""
        self.exists = MagicMock()


def fake_open(*args: Any, **kwargs: Any) -> io.StringIO:  # noqa: ANN401
    """Fake open function that returns fake file data."""
    # This fake open returns a StringIO containing valid JSON content
    return io.StringIO('{"dummy": "data"}')


def fake_subprocess_run_cpe(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
    """Fake subprocess.run() function that raises a CalledProcessError() exception."""
    raise subprocess.CalledProcessError(returncode=1, cmd=args[0])


def fake_run_exception(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
    """Fake function that raises a generic Exception."""
    msg = "Forced testing exception."
    raise Exception(msg)
