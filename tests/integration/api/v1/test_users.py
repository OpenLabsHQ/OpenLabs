import uuid

import pytest
from fastapi import status
from httpx import AsyncClient

from tests.conftest import login_user, logout_user, register_user

from .config import (
    BASE_ROUTE,
    aws_secrets_payload,
    azure_secrets_payload,
    password_update_payload,
)


@pytest.mark.asyncio(loop_scope="session")
async def test_user_change_password_flow(integration_client: AsyncClient) -> None:
    """Test the user flow where a user logs in and changes their password with new password verification."""
    # Ensure unauthenticated client
    assert await logout_user(integration_client)

    # Create/login new user
    _, email, password, _ = await register_user(integration_client)
    assert await login_user(integration_client, email=email, password=password)

    # Create new password
    new_password = f"password-{uuid.uuid4()}"

    password_update_payload["current_password"] = password
    password_update_payload["new_password"] = new_password

    # Change password
    response = await integration_client.post(
        f"{BASE_ROUTE}/users/me/password", json=password_update_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Password updated successfully"

    # Logout
    assert await logout_user(integration_client)

    # Try to login with new password
    assert await login_user(integration_client, email, new_password)


@pytest.mark.asyncio(loop_scope="session")
async def test_user_add_aws_credentials(auth_integration_client: AsyncClient) -> None:
    """Test the user flow where a user adds their AWS credentials and then checks they have been updated."""
    # Add AWS credentials
    aws_response = await auth_integration_client.post(
        f"{BASE_ROUTE}/users/me/secrets/aws", json=aws_secrets_payload
    )
    assert aws_response.status_code == status.HTTP_200_OK
    assert aws_response.json()["message"] == "AWS credentials updated successfully"

    # Check updated status
    updated_status_response = await auth_integration_client.get(
        f"{BASE_ROUTE}/users/me/secrets"
    )
    assert updated_status_response.status_code == status.HTTP_200_OK

    aws_status = updated_status_response.json()
    assert aws_status["aws"]["has_credentials"] is True
    assert "created_at" in aws_status["aws"]


@pytest.mark.asyncio(loop_scope="session")
async def test_user_add_azure_credentials(auth_integration_client: AsyncClient) -> None:
    """Test the user flow where a user adds their Azure credentials and then checks they have been updated."""
    # Add Azure credentials
    azure_response = await auth_integration_client.post(
        f"{BASE_ROUTE}/users/me/secrets/azure", json=azure_secrets_payload
    )
    assert azure_response.status_code == status.HTTP_200_OK
    assert azure_response.json()["message"] == "Azure credentials updated successfully"

    # Check updated status
    status_response = await auth_integration_client.get(
        f"{BASE_ROUTE}/users/me/secrets"
    )
    assert status_response.status_code == status.HTTP_200_OK

    azure_status = status_response.json()
    assert azure_status["azure"]["has_credentials"] is True
    assert "created_at" in azure_status["azure"]


@pytest.mark.asyncio(loop_scope="session")
async def test_user_login_and_check_profile_flow_not_admin(
    integration_client: AsyncClient,
) -> None:
    """Test the user flow where a non-admin user registers/logs in and then checks their profile information."""
    _, email, password, name = await register_user(integration_client)
    assert await login_user(integration_client, email, password)

    # Get user info
    response = await integration_client.get(f"{BASE_ROUTE}/users/me")
    assert response.status_code == status.HTTP_200_OK

    # Verify the response contains the expected user information
    user_info = response.json()
    assert user_info["email"] == email
    assert user_info["name"] == name
    assert user_info["admin"] is False


@pytest.mark.asyncio(loop_scope="session")
async def test_user_login_check_user_admin(
    integration_client: AsyncClient,
) -> None:
    """Test that the admin user is able to log in and shows as admin."""
    # Log in as the admin user
    assert await login_user(integration_client, "admin@test.com", "admin123")

    # Get user info
    response = await integration_client.get(f"{BASE_ROUTE}/users/me")
    assert response.status_code == status.HTTP_200_OK

    # Verify the response shows user being an admin
    user_info = response.json()
    assert user_info["admin"] is True
