import pytest
from fastapi import status
from httpx import AsyncClient

from tests.unit.api.v1.config import BASE_ROUTE

pytestmark = pytest.mark.integration


@pytest.mark.asyncio(loop_scope="session")
async def test_ping_check(integration_client: AsyncClient) -> None:
    """Test that the /health/ping endpoint returns pong response."""
    response = await integration_client.get(f"{BASE_ROUTE}/health/ping")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"msg": "pong"}
