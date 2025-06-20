import atexit
import os
import signal
import sys
from typing import Any, Never

if "COVERAGE_PROCESS_START" in os.environ:
    try:
        import coverage

        cov = coverage.Coverage(
            data_suffix=True,
            concurrency=["gevent"],
        )

        atexit.register(cov.stop)
        atexit.register(cov.save)

        cov.start()
        print(f"[Coverage] Tracking started in process {os.getpid()}")

    except ImportError:
        print("[Coverage] Error: 'coverage' library not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[Coverage] Error during coverage setup: {e}", file=sys.stderr)
        sys.exit(1)


def shutdown_handler(signum: Any, frame: Any) -> Never:  # type: ignore # noqa: ANN401
    """Trigger a graceful exit."""
    print(f"[Coverage] Shutdown signal received in process {os.getpid()}. Exiting.")
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

from src.app.main import app  # noqa: F401
