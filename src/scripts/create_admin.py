#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
from http import HTTPStatus

import aiohttp

# Add the parent directory to sys.path to allow relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.db.database import async_get_db
from app.crud.crud_users import create_user, get_user
from app.schemas.user_schema import UserCreateBaseSchema

logger = logging.getLogger(__name__)

# Health check settings
HEALTH_CHECK_URL = os.environ.get(
    "HEALTH_CHECK_URL", "http://localhost:80/api/v1/health/ping"
)
MAX_RETRIES = 100
RETRY_INTERVAL = 2


async def wait_for_api_ready() -> bool:
    """Wait for the API to be ready by checking the health endpoint."""
    logger.info("Waiting for FastAPI to be ready...")

    for attempt in range(MAX_RETRIES):
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    HEALTH_CHECK_URL, timeout=aiohttp.ClientTimeout(total=5)
                ) as response,
            ):
                if response.status == HTTPStatus.OK:
                    logger.info("FastAPI is ready!")
                    return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.debug(
                "FastAPI not ready yet (attempt %s/%s): %s",
                attempt + 1,
                MAX_RETRIES,
                str(e),
            )

        logger.debug("Waiting %s seconds before next attempt...", RETRY_INTERVAL)
        await asyncio.sleep(RETRY_INTERVAL)

    logger.error("FastAPI not ready after %s attempts", MAX_RETRIES)
    return False


async def initialize_admin_user() -> None:
    """Create admin user if it doesn't exist assuming the DB is already set up."""
    # First wait for the API to be ready
    api_ready = await wait_for_api_ready()
    if not api_ready:
        logger.error("Could not connect to the API. Exiting.")
        sys.exit(1)

    try:
        async for session in async_get_db():
            # Create a UserCreateBaseSchema with the admin details
            admin_schema = UserCreateBaseSchema(
                email=settings.ADMIN_EMAIL,
                password=settings.ADMIN_PASSWORD,
                name=settings.ADMIN_NAME,
            )

            admin_user = await get_user(session, settings.ADMIN_EMAIL)

            if not admin_user:
                # This will create the user with RSA keys and proper encryption
                await create_user(session, admin_schema, is_admin=True)
                logger.info("Admin user %s created successfully.", settings.ADMIN_EMAIL)
            else:
                logger.info("Admin user %s already exists.", settings.ADMIN_EMAIL)

            # Only need to process one session
            break

    except Exception as e:
        logger.error("Failed to create admin user: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(initialize_admin_user())
