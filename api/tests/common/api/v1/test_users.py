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
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
class TestUsersAuth:
    """Test suite for user API endpoints using the authenticated client fixture."""

    async def test_update_password_with_incorrect_current(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test password update with incorrect current password."""
        # Try update with wrong current password
        invalid_payload = copy.deepcopy(password_update_payload)
        # Using an incorrect password to test validation - not a security risk
        invalid_payload["current_password"] = (
            "incorrect-password-for-testing"  # noqa: S105
        )

        update_response = await auth_api_client.post(
            f"{BASE_ROUTE}/users/me/password", json=invalid_payload
        )
        assert update_response.status_code == status.HTTP_400_BAD_REQUEST
        assert update_response.json()["detail"] == "Current password is incorrect"

    async def test_update_secrets_with_invalid_payload(self, auth_api_client: AsyncClient) -> None:
        """Test updating user secrets with invalid credentials format"""
        # Try update with invalid secrets format - Use AWS secrets specifically for this test
        invalid_payload = copy.deepcopy(aws_secrets_payload)
        # Using incorrect credentials to test validation - not a security risk
        invalid_payload["credentials"]["aws_access_key"] = (
            "string"  # noqa: S105
        )

        update_response = await auth_api_client.post(
            f"{BASE_ROUTE}/users/me/secrets", json=invalid_payload
        )
        assert update_response.status_code == status.HTTP_400_BAD_REQUEST
        assert update_response.json()["detail"] == "Invalid AWS credentials payload."

    async def test_update_secrets_with_invalid_credentials(self, auth_api_client: AsyncClient) -> None:
        """Test updating user secrets with invalid credentials that do not authenticate"""
        # Try update with invalid secrets - Use AWS secrets specifically for this test
        invalid_payload = copy.deepcopy(aws_secrets_payload) # Example secrets correct format but do not authenticate

        update_response = await auth_api_client.post(
            f"{BASE_ROUTE}/users/me/secrets", json=invalid_payload
        )
        assert update_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert update_response.json()["detail"] == "AWS credentials could not be authenticated. Please ensure you are providing credentials that are linked to a valid AWS account." 

@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
class TestUsersNoAuth:
    """Test suite for user API endpoings using the UNauthenticaed client fixture."""

    async def test_get_user_info(self, api_client: AsyncClient) -> None:
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

    async def test_get_initial_secrets_status(self, api_client: AsyncClient) -> None:
        """Test getting the initial secrets status."""
        assert await authenticate_client(api_client)

        # Check initial secrets status
        status_response = await api_client.get(f"{BASE_ROUTE}/users/me/secrets")
        assert status_response.status_code == status.HTTP_200_OK

        # Check the status response is valid JSON
        assert status_response.json()

    async def test_update_password_flow(self, api_client: AsyncClient) -> None:
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
        assert await login_user(
            api_client, email, password_update_payload["new_password"]
        )

    async def test_unauthenticated_access(self, api_client: AsyncClient) -> None:
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
            f"{BASE_ROUTE}/users/me/secrets", json=aws_secrets_payload
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_user_login_and_check_profile_flow_not_admin(
        self,
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
