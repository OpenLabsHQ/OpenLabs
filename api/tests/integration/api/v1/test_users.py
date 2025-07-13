import pytest
from fastapi import status
from httpx import AsyncClient

from src.app.core.config import settings
from tests.api_test_utils import login_user
from tests.unit.api.v1.config import BASE_ROUTE


@pytest.mark.asyncio(loop_scope="session")
async def test_user_login_check_user_admin(
    integration_client: AsyncClient,
) -> None:
    """Test that the admin user is able to log in and shows as admin."""
    # Log in as the admin user
    assert await login_user(
        integration_client, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD
    )

    # Get user info
    response = await integration_client.get(f"{BASE_ROUTE}/users/me")
    assert response.status_code == status.HTTP_200_OK

    # Verify the response shows user being an admin
    user_info = response.json()
    assert user_info["admin"] is True
