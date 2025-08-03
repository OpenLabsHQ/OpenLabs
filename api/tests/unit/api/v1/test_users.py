from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi import status
from httpx import AsyncClient
from pytest_mock import MockerFixture

from src.app.core.auth.auth import get_current_user
from src.app.main import app
from src.app.models.user_model import UserModel
from src.app.schemas.message_schema import MessageSchema
from src.app.schemas.secret_schema import SecretSchema
from tests.common.api.v1.config import BASE_ROUTE, aws_secrets_payload


@pytest.fixture
def users_api_v1_endpoints_path() -> str:
    """Get the dot path to the v1 API endpoints for users."""
    return "src.app.api.v1.users"


@pytest.fixture
def mock_update_secrets_success(
    mocker: MockerFixture, users_api_v1_endpoints_path: str
) -> None:
    """Bypass provider credentials verification and updating user secrets record to succeed."""
    mock_creds_class = MagicMock()
    mock_creds_class.verify_creds.return_value = [True, MessageSchema(message="true")]
    mock_creds_class.update_secret_schema.return_value = SecretSchema()
    # Patch the functions
    mocker.patch(
        f"{users_api_v1_endpoints_path}.CredsFactory.create_creds_verification",
        return_value=mock_creds_class,
    )


@pytest.fixture
def mock_get_secrets_failure(
    mocker: MockerFixture, users_api_v1_endpoints_path: str
) -> None:
    """Bypass fetching users secrets to fail."""
    # Patch the function
    mocker.patch(f"{users_api_v1_endpoints_path}.get_user_secrets", return_value=None)


@pytest.fixture
def mock_get_secrets(mocker: MockerFixture, users_api_v1_endpoints_path: str) -> None:
    """Bypass fetching users secrets to pass for a fake user."""

    def override_get_current_user_no_key() -> UserModel:
        return UserModel(
            name="FakeUser",
            email="fakeuser@gmail.com",
            hashed_password="faskpasswordhash",  # noqa: S106
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            is_admin=False,
            public_key=None,
        )

    # Temporarily override the dependency
    app.dependency_overrides[get_current_user] = override_get_current_user_no_key
    # Patch the function
    mocker.patch(
        f"{users_api_v1_endpoints_path}.get_user_secrets",
        return_value=SecretSchema(),
    )


async def test_update_aws_secrets_success(
    auth_client: AsyncClient, mock_update_secrets_success: None
) -> None:
    """Test that attempting to update user AWS provider credentials succeeds."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/users/me/secrets",
        json=aws_secrets_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()["message"]
        == "AWS credentials successfully verified and updated."
    )


async def test_update_user_secrets_database_fetch_failure(
    auth_client: AsyncClient, mock_get_secrets_failure: None
) -> None:
    """Test that attempting to update user provider credentials fails when user record is not found in database."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/users/me/secrets",
        json=aws_secrets_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "User secrets record not found!"


async def test_update_user_secrets_encryption_failure(
    auth_client: AsyncClient,
    mock_get_secrets: None,
    mock_update_secrets_success: None,
) -> None:
    """Test that attempting to update user provider credentials fails when user public key does not exist."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/users/me/secrets",
        json=aws_secrets_payload,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        response.json()["detail"]
        == "User encryption keys not set up. Please register a new account."
    )
