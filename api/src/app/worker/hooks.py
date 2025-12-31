import logging
from typing import Any

from ..core.db.database import async_engine

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Start worker."""
    logger.info("Worker starting...")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Shutdown worker."""
    logger.info("Worker stopping...")

    # Dispose of database engine
    logger.info("Disposing of database engine...")
    await async_engine.dispose()
    logger.info("Database engine disposed.")
