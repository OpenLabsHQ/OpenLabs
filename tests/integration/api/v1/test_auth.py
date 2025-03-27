import copy
import uuid

import pytest
from fastapi import status
from httpx import AsyncClient

from .config import BASE_ROUTE, base_user_login_payload, base_user_register_payload

user_register_payload = copy.deepcopy(base_user_register_payload)
user_login_payload = copy.deepcopy(base_user_login_payload)

user_register_payload["email"] = "test-auth@ufsit.club"
user_login_payload["email"] = user_register_payload["email"]


@pytest.mark.asyncio(loop_scope="session")
async def test_new_user_register_login_flow(integration_client: AsyncClient) -> None:
    """Test the user flow where a new user registers and then logs in."""
    # Register new user
    response = await integration_client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )
    assert response.status_code == status.HTTP_200_OK

    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response

    # Login as new user
    response = await integration_client.post(
        f"{BASE_ROUTE}/auth/login", json=user_login_payload
    )
    assert response.status_code == status.HTTP_200_OK

    # Check that the response contains a success message
    assert response.json()["success"] is True

    # Check that the cookie is set
    assert "token" in response.cookies
    assert "enc_key" in response.cookies
