import asyncio
import logging

from fastapi import status
from httpx import AsyncClient, ConnectError

logger = logging.getLogger(__name__)


async def wait_for_api_ready(
    api_url: str = "http://fastapi:80",
    api_version: int = 1,
    max_retries: int = 3,
    retry_interval: int = 2,
    client: AsyncClient | None = None,
) -> bool:
    """Wait for the API to be ready by checking the health endpoint."""
    logger.info("Waiting for FastAPI to be ready...")

    # Build base API URL
    if api_version == 1:
        base_url = api_url + "/api/v1"
    else:
        msg = f"Invalid API version provided: {api_version}"
        raise ValueError(msg)

    if not client:
        client = AsyncClient(base_url=base_url)

    # URLs to check
    urls = ["/health/ping"]

    for endpoint in urls:
        current_url = base_url + endpoint

        for attempt in range(max_retries):
            try:
                response = await client.get(current_url, timeout=5)

                if response.status_code == status.HTTP_200_OK:
                    logger.info("FastAPI is ready!")
                    return True

            except (ConnectError, asyncio.TimeoutError) as e:
                logger.debug(
                    "FastAPI not ready yet (attempt %s/%s): %s",
                    attempt + 1,
                    max_retries,
                    str(e),
                )

            logger.debug("Waiting %s seconds before next attempt...", retry_interval)
            await asyncio.sleep(retry_interval)

    logger.error("FastAPI not ready after %s attempts", max_retries)
    return False


if __name__ == "__main__":
    asyncio.run(
        wait_for_api_ready(
            api_url="http://fastapi:80", api_version=1, max_retries=5, retry_interval=2
        )
    )
