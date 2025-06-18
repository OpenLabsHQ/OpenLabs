import pytest
from fastapi import status
from httpx import AsyncClient

from src.app.core.config import settings
from tests.api_test_utils import (
    login_user,
    register_user,
)
from tests.unit.api.v1.config import (
    BASE_ROUTE,
    valid_blueprint_range_create_payload,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_can_view_all_blueprints(
    auth_integration_client: AsyncClient,
    integration_client: AsyncClient,
) -> None:
    """Test that an admin is able to see blueprints for all users."""
    response = await auth_integration_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    response = await auth_integration_client.get(f"{BASE_ROUTE}/blueprints/ranges")
    assert response.status_code == status.HTTP_200_OK
    user1_blueprint_ids = {blueprint_range["id"] for blueprint_range in response.json()}

    # Login as new user
    _, email, password, _ = await register_user(integration_client)
    assert await login_user(integration_client, email, password)

    response = await integration_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    response = await integration_client.get(f"{BASE_ROUTE}/blueprints/ranges")
    user2_blueprint_ids = {blueprint_range["id"] for blueprint_range in response.json()}

    # Login as admin
    assert await login_user(
        integration_client, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD
    )
    response = await integration_client.get(f"{BASE_ROUTE}/blueprints/ranges")
    assert response.status_code == status.HTTP_200_OK
    admin_blueprint_ids = {blueprint_range["id"] for blueprint_range in response.json()}

    combined_user_blueprint_ids = user1_blueprint_ids.union(user2_blueprint_ids)
    assert admin_blueprint_ids.issuperset(combined_user_blueprint_ids)
