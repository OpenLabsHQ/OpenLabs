from fastapi import status
from httpx import AsyncClient

from .config import BASE_ROUTE


async def test_ping_check(client: AsyncClient) -> None:
    """Test that the /health/ping endpoint returns pong response."""
    response = await client.get(f"{BASE_ROUTE}/health/ping")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"msg": "pong"}
