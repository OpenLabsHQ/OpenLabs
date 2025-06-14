import pytest
from fastapi import status
from httpx import AsyncClient

from .config import API_CLIENT_PARAMS, BASE_ROUTE


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_ping_check(api_client: AsyncClient) -> None:
    """Test that the /health/ping endpoint returns pong response."""
    response = await api_client.get(f"{BASE_ROUTE}/health/ping")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"msg": "pong"}
