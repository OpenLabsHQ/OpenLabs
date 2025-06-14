import copy
import uuid

import pytest
from fastapi import status
from httpx import AsyncClient

from tests.common.api.v1.config import (
    API_CLIENT_PARAMS,
    BASE_ROUTE,
    base_user_login_payload,
    base_user_register_payload,
)

user_register_payload = copy.deepcopy(base_user_register_payload)
user_login_payload = copy.deepcopy(base_user_login_payload)

user_register_payload["email"] = "test-auth@ufsit.club"
user_login_payload["email"] = user_register_payload["email"]


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_user_register(api_client: AsyncClient) -> None:
    """Test that we get a 200 response when registering a user."""
    response = await api_client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )
    assert response.status_code == status.HTTP_200_OK

    assert int(response.json()["id"])


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_user_register_bad_email(api_client: AsyncClient) -> None:
    """Test that we get a 422 response when registering a user with an invalid email."""
    invalid_payload = copy.deepcopy(user_register_payload)
    invalid_payload["email"] = "invalidemail"

    response = await api_client.post(
        f"{BASE_ROUTE}/auth/register", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_duplicate_user_register(api_client: AsyncClient) -> None:
    """Test that we get a 400 response when registering a user with the same email."""
    response = await api_client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response_json = response.json()
    assert response_json["detail"] == "User already exists"


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_duplicate_user_diff_name_pass_register(api_client: AsyncClient) -> None:
    """Test that we get a 400 response when registering a user with the same email but a different password and name."""
    new_user_register_payload = copy.deepcopy(user_register_payload)
    new_user_register_payload["password"] = "newpassword123"  # noqa: S105 (Testing)
    new_user_register_payload["name"] = "New Name"

    response = await api_client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )
    assert response.status_code == status.HTTP_409_CONFLICT

    response_json = response.json()
    assert response_json["detail"] == "User already exists"


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_user_register_invalid_payload(api_client: AsyncClient) -> None:
    """Test that we get a 422 response when registering a user with an invalid payload."""
    invalid_payload = copy.deepcopy(user_register_payload)
    invalid_payload.pop("email")

    response = await api_client.post(
        f"{BASE_ROUTE}/auth/register", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    invalid_payload = copy.deepcopy(user_register_payload)
    invalid_payload.pop("password")

    response = await api_client.post(
        f"{BASE_ROUTE}/auth/register", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    invalid_payload = copy.deepcopy(user_register_payload)
    invalid_payload.pop("name")

    response = await api_client.post(
        f"{BASE_ROUTE}/auth/register", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_user_login_correct_pass(api_client: AsyncClient) -> None:
    """Test that we get a 200 response when logging in a user and get a valid JWT cookie."""
    response = await api_client.post(
        f"{BASE_ROUTE}/auth/login", json=user_login_payload
    )
    assert response.status_code == status.HTTP_200_OK

    # Check that the response contains a success message
    assert response.json()["success"] is True

    # Check that the cookie is set
    assert "token" in response.cookies


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_user_login_incorrect_pass(api_client: AsyncClient) -> None:
    """Test that we get a 401 response when logging in a user with an incorrect password."""
    invalid_payload = copy.deepcopy(user_login_payload)
    invalid_payload["password"] = "incorrectpassword"  # noqa: S105 (Testing)

    response = await api_client.post(f"{BASE_ROUTE}/auth/login", json=invalid_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_nonexistent_user_login(api_client: AsyncClient) -> None:
    """Test that we get a 401 response when logging in a user that doesn't exist."""
    invalid_payload = copy.deepcopy(user_login_payload)
    invalid_payload["email"] = "alex@ufsit.club"

    response = await api_client.post(f"{BASE_ROUTE}/auth/login", json=invalid_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_user_logout(api_client: AsyncClient) -> None:
    """Test that we can successfully logout a user."""
    # First login to get the cookie
    login_response = await api_client.post(
        f"{BASE_ROUTE}/auth/login", json=user_login_payload
    )
    assert login_response.status_code == status.HTTP_200_OK
    assert "token" in login_response.cookies

    # Now logout
    logout_response = await api_client.post(f"{BASE_ROUTE}/auth/logout")
    assert logout_response.status_code == status.HTTP_200_OK

    # Verify the response content
    assert logout_response.json()["success"] is True

    # Note: We cannot verify cookie deletion in tests because HttpX doesn't support
    # direct inspection of Set-Cookie headers that clear cookies. In a real browser,
    # this would clear the cookie.


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_new_user_register_login_logout_flow(
    api_client: AsyncClient,
) -> None:
    """Test the user flow where a new user registers and then logs in followed by logout."""
    user_register_payload = copy.deepcopy(base_user_register_payload)
    user_login_payload = copy.deepcopy(base_user_login_payload)

    user_register_payload["email"] = f"test-auth-{uuid.uuid4()}@ufsit.club"
    user_login_payload["email"] = user_register_payload["email"]

    # Register new user
    response = await api_client.post(
        f"{BASE_ROUTE}/auth/register", json=user_register_payload
    )
    assert response.status_code == status.HTTP_200_OK

    # Capture user ID
    user_id = int(response.json()["id"])
    assert user_id

    # Login as new user
    response = await api_client.post(
        f"{BASE_ROUTE}/auth/login", json=user_login_payload
    )
    assert response.status_code == status.HTTP_200_OK

    # Check that the response contains a success message
    assert response.json()["success"] is True

    # Check that the cookie is set
    assert "token" in response.cookies
    assert "enc_key" in response.cookies

    # Logout
    response = await api_client.post(f"{BASE_ROUTE}/auth/logout")
    assert response.status_code == status.HTTP_200_OK
