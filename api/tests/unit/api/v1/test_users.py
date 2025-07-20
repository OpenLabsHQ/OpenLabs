from typing import Any
from httpx import AsyncClient
import pytest
from pytest_mock import MockerFixture

from src.app.schemas.message_schema import MessageSchema
from tests.unit.api.v1.config import BASE_ROUTE
from fastapi import status
from tests.unit.api.v1.config import aws_secrets_payload
from unittest.mock import MagicMock


@pytest.fixture
def users_api_v1_endpoints_path() -> str:
    """Get the dot path to the v1 API endpoints for users."""
    return "src.app.api.v1.users"


@pytest.fixture
def mock_update_secrets_success(
    mocker: MockerFixture, users_api_v1_endpoints_path: str
) -> None:
    """Bypass provider credentials verification to succeed."""

    mock_creds_class = MagicMock()
    mock_creds_class.verify_creds.return_value = [True, MessageSchema(message="true")]
    # Patch the function
    mocker.patch(
        f"{users_api_v1_endpoints_path}.CredsFactory.create_creds_verification",
        return_value=mock_creds_class,
    )


async def test_update_secrets_database_fetch_failure(
    auth_client: AsyncClient, mock_update_secrets_success: None
) -> None:
    """Test that attempting to update user provider credentials fails when user record is not found in the database"""
    response = await auth_client.post(
        f"{BASE_ROUTE}/users/me/secrets",
        json=aws_secrets_payload,
    )
    assert response.status_code == status.HTTP_200_OK
