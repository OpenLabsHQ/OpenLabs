from fastapi import status
from httpx import AsyncClient
import pytest

from .config import BASE_ROUTE


@pytest.mark.asyncio(loop_scope="session")
async def test_ping_check(integration_client: AsyncClient) -> None:
    """Test that the /health/ping endpoint returns pong response."""
    response = await integration_client.get(f"{BASE_ROUTE}/health/ping")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"msg": "pong"}
