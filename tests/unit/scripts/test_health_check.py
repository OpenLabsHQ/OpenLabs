import asyncio

import pytest
from httpx import AsyncClient

from src.scripts.health_check import wait_for_api_ready


def test_health_check_script_works(client: AsyncClient) -> None:
    """Test that the health_check.py script works."""
    # Mimic args of script but replace client with fixture
    assert asyncio.run(
        wait_for_api_ready(
            api_url="http://fastapi:80",
            api_version=1,
            max_retries=5,
            retry_interval=2,
            client=client,
        )
    )


def test_health_check_script_invalid_api_version() -> None:
    """Test that the health_check.py script raises a ValueError for an invalid API version."""
    with pytest.raises(ValueError):
        assert asyncio.run(
            wait_for_api_ready(
                api_url="http://fastapi:80",
                api_version=-1,
                max_retries=5,
                retry_interval=2,
            )
        )


def test_health_check_script_timeout() -> None:
    """Test that the health_check.py script returns False when checks timeout."""
    assert (
        asyncio.run(
            wait_for_api_ready(
                api_url="http://fastapi:80",
                api_version=1,
                max_retries=1,
                retry_interval=1,
            )
        )
        is False
    )
