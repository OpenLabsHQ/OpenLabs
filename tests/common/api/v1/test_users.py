import copy

import pytest
from fastapi import status
from httpx import AsyncClient

from tests.api_test_utils import (
    authenticate_client,
    login_user,
    logout_user,
    register_user,
)
from tests.common.api.v1.config import (
    API_CLIENT_PARAMS,
    AUTH_API_CLIENT_PARAMS,
    BASE_ROUTE,
    aws_secrets_payload,
    azure_secrets_payload,
    password_update_payload,
)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_get_user_info(api_client: AsyncClient) -> None:
    """Test retrieving the current user's information."""
    # Set the authorization header with the token
    _, email, password, name = await register_user(api_client)
    assert await login_user(api_client, email, password)

    # Get user info
    response = await api_client.get(f"{BASE_ROUTE}/users/me")
    assert response.status_code == status.HTTP_200_OK

    # Verify the response contains the expected user information
    user_info = response.json()
    assert user_info["email"] == email
    assert user_info["name"] == name


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_update_password_flow(api_client: AsyncClient) -> None:
    """Test the complete password update flow."""
    _, email, password, name = await register_user(api_client)
    assert await login_user(api_client, email, password)

    # Set old password
    password_update_payload["current_password"] = password

    # Update password
    update_response = await api_client.post(
        f"{BASE_ROUTE}/users/me/password", json=password_update_payload
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["message"] == "Password updated successfully"

    # Logout
    assert await logout_user(api_client)

    # Try to login with new password
    assert await login_user(api_client, email, password_update_payload["new_password"])


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_update_password_with_incorrect_current(
    auth_api_client: AsyncClient,
) -> None:
    """Test password update with incorrect current password."""
    # Try update with wrong current password
    invalid_payload = copy.deepcopy(password_update_payload)
    # Using an incorrect password to test validation - not a security risk
    invalid_payload["current_password"] = "incorrect-password-for-testing"  # noqa: S105

    update_response = await auth_api_client.post(
        f"{BASE_ROUTE}/users/me/password", json=invalid_payload
    )
    assert update_response.status_code == status.HTTP_400_BAD_REQUEST
    assert update_response.json()["detail"] == "Current password is incorrect"


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_get_initial_secrets_status(api_client: AsyncClient) -> None:
    """Test getting the initial secrets status."""
    assert await authenticate_client(api_client)

    # Check initial secrets status
    status_response = await api_client.get(f"{BASE_ROUTE}/users/me/secrets")
    assert status_response.status_code == status.HTTP_200_OK

    # Check the status response is valid JSON
    assert status_response.json()


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_update_aws_credentials(auth_api_client: AsyncClient) -> None:
    """Test updating AWS credentials."""
    # Add AWS credentials
    aws_response = await auth_api_client.post(
        f"{BASE_ROUTE}/users/me/secrets/aws", json=aws_secrets_payload
    )
    assert aws_response.status_code == status.HTTP_200_OK
    assert aws_response.json()["message"] == "AWS credentials updated successfully"

    # Check updated status
    updated_status_response = await auth_api_client.get(
        f"{BASE_ROUTE}/users/me/secrets"
    )
    assert updated_status_response.status_code == status.HTTP_200_OK

    aws_status = updated_status_response.json()
    assert aws_status["aws"]["has_credentials"] is True
    assert "created_at" in aws_status["aws"]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_update_azure_credentials(auth_api_client: AsyncClient) -> None:
    """Test updating Azure credentials."""
    # Add Azure credentials
    azure_response = await auth_api_client.post(
        f"{BASE_ROUTE}/users/me/secrets/azure", json=azure_secrets_payload
    )
    assert azure_response.status_code == status.HTTP_200_OK
    assert azure_response.json()["message"] == "Azure credentials updated successfully"

    # Check updated status
    status_response = await auth_api_client.get(f"{BASE_ROUTE}/users/me/secrets")
    assert status_response.status_code == status.HTTP_200_OK

    azure_status = status_response.json()
    assert azure_status["azure"]["has_credentials"] is True
    assert "created_at" in azure_status["azure"]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_both_provider_credentials_status(auth_api_client: AsyncClient) -> None:
    """Test that status shows both provider credentials when set."""
    # Add AWS credentials
    aws_response = await auth_api_client.post(
        f"{BASE_ROUTE}/users/me/secrets/aws", json=aws_secrets_payload
    )
    assert aws_response.status_code == status.HTTP_200_OK
    assert aws_response.json()["message"] == "AWS credentials updated successfully"

    # Add Azure credentials
    azure_response = await auth_api_client.post(
        f"{BASE_ROUTE}/users/me/secrets/azure", json=azure_secrets_payload
    )
    assert azure_response.status_code == status.HTTP_200_OK
    assert azure_response.json()["message"] == "Azure credentials updated successfully"

    # Check final status with both credentials
    status_response = await auth_api_client.get(f"{BASE_ROUTE}/users/me/secrets")
    assert status_response.status_code == status.HTTP_200_OK

    provider_status = status_response.json()
    assert provider_status["aws"]["has_credentials"] is True
    assert provider_status["azure"]["has_credentials"] is True
    assert "created_at" in provider_status["aws"]
    assert "created_at" in provider_status["azure"]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_unauthenticated_access(api_client: AsyncClient) -> None:
    """Test that unauthenticated users cannot access protected endpoints."""
    # Preemptively logout incase client has leftover credentials
    assert await logout_user(api_client)

    # Try to access user info without authentication
    response = await api_client.get(f"{BASE_ROUTE}/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Try to update password without authentication
    response = await api_client.post(
        f"{BASE_ROUTE}/users/me/password", json=password_update_payload
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Try to get secrets status without authentication
    response = await api_client.get(f"{BASE_ROUTE}/users/me/secrets")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Try to update AWS secrets without authentication
    response = await api_client.post(
        f"{BASE_ROUTE}/users/me/secrets/aws", json=aws_secrets_payload
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Try to update Azure secrets without authentication
    response = await api_client.post(
        f"{BASE_ROUTE}/users/me/secrets/azure", json=azure_secrets_payload
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_user_login_and_check_profile_flow_not_admin(
    api_client: AsyncClient,
) -> None:
    """Test the user flow where a non-admin user registers/logs in and then checks their profile information."""
    _, email, password, name = await register_user(api_client)
    assert await login_user(api_client, email, password)

    # Get user info
    response = await api_client.get(f"{BASE_ROUTE}/users/me")
    assert response.status_code == status.HTTP_200_OK

    # Verify the response contains the expected user information
    user_info = response.json()
    assert user_info["email"] == email
    assert user_info["name"] == name
    assert user_info["admin"] is False
