import copy
import random
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.enums.job_status import JobSubmissionDetail
from src.app.models.user_model import UserModel
from src.app.schemas.range_schemas import (
    DeployedRangeHeaderSchema,
    DeployedRangeKeySchema,
    DeployedRangeSchema,
)
from src.app.schemas.secret_schema import SecretSchema
from tests.api_test_utils import authenticate_client
from tests.common.api.v1.config import (
    BASE_ROUTE,
    valid_blueprint_range_create_payload,
    valid_deployed_range_data,
    valid_range_deploy_payload,
    valid_range_private_key_data,
)


@pytest.fixture
def range_api_v1_endpoints_path() -> str:
    """Get the dot path to the v1 API endpoints for ranges."""
    return "src.app.api.v1.ranges"


@pytest.fixture
def mock_decrypt_no_secrets(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Bypass secrets decryption to return a fake secrets record for the user."""

    async def mock_get_decrypted_secrets(
        user: UserModel, db: AsyncSession, master_key: bytes
    ) -> SecretSchema:
        return SecretSchema(
            aws_access_key=None,
            aws_secret_key=None,
            aws_created_at=None,
            azure_client_id=None,
            azure_client_secret=None,
            azure_tenant_id=None,
            azure_subscription_id=None,
            azure_created_at=None,
        )

    # Patch the function
    monkeypatch.setattr(
        f"{range_api_v1_endpoints_path}.get_decrypted_secrets",
        mock_get_decrypted_secrets,
    )


@pytest.fixture
def mock_decrypt_example_valid_aws_secrets(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Bypass secrets decryption to return a fake secrets record for the user."""

    async def mock_get_decrypted_secrets(
        user: UserModel, db: AsyncSession, master_key: bytes
    ) -> SecretSchema:
        return SecretSchema(
            aws_access_key="AKIAIOSFODNN7EXAMPLE",
            aws_secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # noqa: S106
            aws_created_at=datetime.now(tz=timezone.utc),
            azure_client_id=None,
            azure_client_secret=None,
            azure_tenant_id=None,
            azure_subscription_id=None,
            azure_created_at=None,
        )

    # Patch the function
    monkeypatch.setattr(
        f"{range_api_v1_endpoints_path}.get_decrypted_secrets",
        mock_get_decrypted_secrets,
    )


@pytest.fixture
def mock_retrieve_deployed_range_success(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Simulate successfully retrieving a deployed range from the database."""

    async def mock_get_range_success(
        *args: dict[str, Any], **kwargs: dict[str, Any]
    ) -> DeployedRangeSchema:
        return DeployedRangeSchema.model_validate(
            valid_deployed_range_data, from_attributes=True
        )

    monkeypatch.setattr(
        f"{range_api_v1_endpoints_path}.get_deployed_range", mock_get_range_success
    )


@pytest.fixture
def mock_job_enqueue_success(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> str:
    """Simulate successfully enqueueing a job in ARQ."""
    fake_job_id = uuid.uuid4().hex
    mock_enqueue = AsyncMock()
    mock_enqueue.return_value = fake_job_id
    monkeypatch.setattr(f"{range_api_v1_endpoints_path}.enqueue_arq_job", mock_enqueue)
    return fake_job_id


@pytest.fixture
def mock_job_enqueue_failed(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Simulate failing to enqueue a job in ARQ."""
    mock_enqueue = AsyncMock()
    mock_enqueue.return_value = None
    monkeypatch.setattr(f"{range_api_v1_endpoints_path}.enqueue_arq_job", mock_enqueue)


@pytest.fixture
def mock_add_job_to_db_success(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Simulate successfully adding the job record to the database."""
    mock_add_job = AsyncMock()
    mock_add_job.return_value = None
    monkeypatch.setattr(f"{range_api_v1_endpoints_path}.add_job", mock_add_job)


@pytest.fixture
def mock_add_job_to_db_failed(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Simulate successfully adding the job record to the database."""
    mock_add_job = AsyncMock()
    mock_add_job.side_effect = RuntimeError("Fake DB error!")
    monkeypatch.setattr(f"{range_api_v1_endpoints_path}.add_job", mock_add_job)


@pytest_asyncio.fixture(scope="module")
async def mock_deploy_payload(auth_client: AsyncClient) -> dict[str, Any]:
    """Add a range blueprint and generate the appropriate payload to deploy that blueprint.

    This is intentially scoped to the module to prevent uneeded API calls for each test.
    """
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    blueprint_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    blueprint_deploy_payload["blueprint_id"] = blueprint_id

    return blueprint_deploy_payload


async def test_deploy_without_valid_secrets(
    auth_client: AsyncClient,
    mock_decrypt_no_secrets: None,
    mock_deploy_payload: dict[str, Any],
) -> None:
    """Test that attempting to deploy a range without valid cloud provider credentials will fail (no secrets in database for user)."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=mock_deploy_payload,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "credential" in response.json()["detail"].lower()


async def test_deploy_range_deploy_success(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_job_enqueue_success: None,
    mock_add_job_to_db_success: None,
    mock_deploy_payload: dict[str, Any],
) -> None:
    """Test to deploy a range successfully with a returned the associated job ID."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=mock_deploy_payload,
    )
    assert response.status_code == status.HTTP_202_ACCEPTED  # It's an async job
    assert response.json()["arq_job_id"]

    # Job was successfully added to database
    assert JobSubmissionDetail.DB_SAVE_SUCCESS.value == response.json()["detail"]


async def test_deploy_range_add_job_db_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_job_enqueue_success: None,
    mock_add_job_to_db_failed: None,
    mock_deploy_payload: dict[str, Any],
) -> None:
    """Test to deploy a range successfully with a returned the associated job ID, but indicates the job record wasn't added."""
    # The job is successfully submitted, so the response code
    # is still a success but the message to the user changes
    # to reflect that the job might not be in the database for
    # a little bit.
    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=mock_deploy_payload,
    )
    assert response.status_code == status.HTTP_202_ACCEPTED  # It's an async job
    assert response.json()["arq_job_id"]

    # Failed to add job to database in endpoint
    assert JobSubmissionDetail.DB_SAVE_FAILURE.value == response.json()["detail"]


async def test_deploy_range_failed_job_queue(
    auth_client: AsyncClient,
    mock_job_enqueue_failed: None,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_deploy_payload: dict[str, Any],
) -> None:
    """Test that the endpoint returns a 500 error when it fails to queue up a deploy job."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=mock_deploy_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "queue" in response.json()["detail"]


async def test_destroy_without_valid_range_owner(
    client: AsyncClient,
) -> None:
    """Test that attempting to destroy a range that a user does not own will fail."""
    auth_success = await authenticate_client(client)
    if not auth_success:
        pytest.fail("Failed to authenticate client to API!")

    # A negative ID will never exist and thus can never be owned
    # by this user
    response = await client.delete(f"{BASE_ROUTE}/ranges/-1337")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_destroy_decrypt_secrets_failure(
    auth_client: AsyncClient,
    range_api_v1_endpoints_path: str,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that attempting to destroy a range without valid private key will fail."""

    async def mock_get_decrypted_secrets_false(
        user: UserModel, db: AsyncSession, master_key: bytes
    ) -> None:
        return None

    # Patch the function so that the deploy works, but the destroy fails
    monkeypatch.setattr(
        f"{range_api_v1_endpoints_path}.get_decrypted_secrets",
        mock_get_decrypted_secrets_false,
    )

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "credential" in response.json()["detail"].lower()


async def test_destroy_without_valid_secrets(
    auth_client: AsyncClient,
    mock_decrypt_no_secrets: None,
    mock_retrieve_deployed_range_success: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that attempting to destroy a range without valid cloud provider credentials will fail (no secrets in database for user)."""
    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "credential" in response.json()["detail"].lower()


async def test_destroy_range_destroy_success(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    mock_add_job_to_db_success: None,
    mock_job_enqueue_success: None,
) -> None:
    """Test to destroy a range successfully with a returned the associated job ID."""
    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/1",
    )
    assert response.status_code == status.HTTP_202_ACCEPTED  # It's an async job
    assert response.json()["arq_job_id"]

    # Job was successfully added to database
    assert JobSubmissionDetail.DB_SAVE_SUCCESS.value == response.json()["detail"]


async def test_destroy_range_add_job_db_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    mock_add_job_to_db_failed: None,
    mock_job_enqueue_success: None,
) -> None:
    """Test to destroy a range successfully with a returned the associated job ID, but indicates the job record wasn't added."""
    # The job is successfully submitted, so the response code
    # is still a success but the message to the user changes
    # to reflect that the job might not be in the database for
    # a little bit.
    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/1",
    )
    assert response.status_code == status.HTTP_202_ACCEPTED  # It's an async job
    assert response.json()["arq_job_id"]

    # Failed to add job to database in endpoint
    assert JobSubmissionDetail.DB_SAVE_FAILURE.value == response.json()["detail"]


async def test_destroy_range_failed_job_queue(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_job_enqueue_failed: None,
    mock_retrieve_deployed_range_success: None,
) -> None:
    """Test that the endpoint returns a 500 error when it fails to queue up a destroy job."""
    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/1",
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "queue" in response.json()["detail"]


async def test_get_range_headers_success(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    range_api_v1_endpoints_path: str,
) -> None:
    """Test that we get a 200 response when there is at least one range header found."""
    header = DeployedRangeHeaderSchema.model_validate(valid_deployed_range_data)

    monkeypatch.setattr(
        f"{range_api_v1_endpoints_path}.get_deployed_range_headers",
        AsyncMock(return_value=[header]),
    )

    response = await auth_client.get(f"{BASE_ROUTE}/ranges")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data == [header.model_dump(mode="json")]


async def test_get_range_details_success(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    range_api_v1_endpoints_path: str,
) -> None:
    """Test that we get a 200 response when the range we request exists."""
    test_range = DeployedRangeSchema.model_validate(valid_deployed_range_data)

    monkeypatch.setattr(
        f"{range_api_v1_endpoints_path}.get_deployed_range",
        AsyncMock(return_value=test_range),
    )

    response = await auth_client.get(f"{BASE_ROUTE}/ranges/1337")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data == test_range.model_dump(mode="json")


async def test_get_range_key_success(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that we get 200 response when we request the private key for an existing range."""
    test_key = DeployedRangeKeySchema.model_validate(valid_range_private_key_data)

    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_deployed_range_key",
        AsyncMock(return_value=test_key),
    )

    response = await auth_client.get(f"{BASE_ROUTE}/ranges/1337/key")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data == test_key.model_dump(mode="json")
