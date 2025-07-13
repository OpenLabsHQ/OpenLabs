from typing import Any, Callable, ClassVar

from arq.connections import RedisSettings

from ..core.config import settings

# Import logger to ensure workers log messages properly
from ..core.logger import LOG_DIR  # noqa: F401
from .hooks import shutdown, startup
from .ranges import deploy_range, destroy_range


class WorkerSettings:
    """Remote worker settings."""

    functions: ClassVar[list[Callable[..., Any]]] = [deploy_range, destroy_range]
    redis_settings = RedisSettings(
        host=settings.REDIS_QUEUE_HOST,
        port=settings.REDIS_QUEUE_PORT,
        password=settings.REDIS_QUEUE_PASSWORD,
    )

    # Hook functions
    on_startup = startup
    on_shutdown = shutdown

    handle_signals = False

    job_results_ttl = 86400  # 24 hours
    job_timeout = 1200  # 20 minutes (for large ranges)
