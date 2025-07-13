import random
import re

import pytest
from fastapi import status
from httpx import AsyncClient

from tests.api_test_utils import authenticate_client
from tests.common.api.v1.config import (
    API_CLIENT_PARAMS,
    AUTH_API_CLIENT_PARAMS,
    BASE_ROUTE,
)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
class TestJobsAuth:
    """Test suite for /jobs endpoints using the authenticated client fixture."""

    async def test_jobs_get_non_existent(self, auth_api_client: AsyncClient) -> None:
        """Test that we get a 404 error when we request a non-existent job."""
        invalid_job_id = random.randint(-100, -1)  # noqa: S311
        response = await auth_api_client.get(f"{BASE_ROUTE}/jobs/{invalid_job_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Error message
        error_pattern = re.compile(f"{invalid_job_id}.*not found", re.IGNORECASE)
        assert re.search(error_pattern, response.json()["detail"])


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
class TestJobsNoAuth:
    """Test suite for /jobs endpoints using the UNauthenticated client fixture."""

    async def test_jobs_get_empty_list(self, api_client: AsyncClient) -> None:
        """Test that we get a 404 when error when try to list out all jobs and have none."""
        assert await authenticate_client(api_client)

        response = await api_client.get(f"{BASE_ROUTE}/jobs")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Error message
        assert "jobs" in response.json()["detail"].lower()
