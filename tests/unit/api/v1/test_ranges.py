import copy
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from arq import ArqRedis
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.user_model import UserModel
from src.app.schemas.job_schemas import JobCreateSchema, JobSchema
from src.app.schemas.range_schemas import (
    DeployedRangeHeaderSchema,
    DeployedRangeKeySchema,
    DeployedRangeSchema,
)
from src.app.schemas.secret_schema import SecretSchema
from tests.api_test_utils import authenticate_client

from .config import (
    BASE_ROUTE,
    complete_job_payload,
    valid_blueprint_range_create_payload,
    valid_deployed_range_data,
    valid_range_deploy_payload,
    valid_range_private_key_data,
)

pytestmark = pytest.mark.unit


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
def mock_redis_queue_pool_no_connection(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Patch the queue.pool object to be None to simulate no connection te Redis."""
    monkeypatch.setattr(f"{range_api_v1_endpoints_path}.queue.pool", None)


@pytest.fixture
def mock_redis_queue_pool_successful_job_queue(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Patch the queue.pool object to ensure it passes as a real Redis connection and queues a fake job."""
    fake_redis = AsyncMock(spec=ArqRedis)

    class FakeJob:
        job_id: str = str(uuid.uuid4()).replace("-", "")

    fake_redis.enqueue_job.return_value = FakeJob()

    monkeypatch.setattr(f"{range_api_v1_endpoints_path}.queue.pool", fake_redis)


@pytest.fixture
def mock_redis_queue_pool_failed_job_queue(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Patch the queue.pool object to ensure it passes as a real Redis connection and but fails to queue a job."""
    fake_redis = AsyncMock(spec=ArqRedis)

    fake_redis.enqueue_job.return_value = None

    monkeypatch.setattr(f"{range_api_v1_endpoints_path}.queue.pool", fake_redis)


@pytest.fixture
def mock_successful_fetch_job_info(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Patch over the redis job info retrieval utlity function to return a valid job schema."""
    # Mock return value
    mock_job_schema = JobCreateSchema.model_validate(complete_job_payload)

    # Mock function
    mock_get_info_from_redis = AsyncMock()
    mock_get_info_from_redis.return_value = mock_job_schema

    monkeypatch.setattr(
        f"{range_api_v1_endpoints_path}.get_job_from_redis", mock_get_info_from_redis
    )


@pytest.fixture
def mock_failed_fetch_job_info(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Patch over the redis job info retrieval utlity function to return no data."""
    # Mock function failure
    mock_get_info_from_redis = AsyncMock()
    mock_get_info_from_redis.return_value = None

    monkeypatch.setattr(
        f"{range_api_v1_endpoints_path}.get_job_from_redis", mock_get_info_from_redis
    )


@pytest.fixture
def mock_successful_job_add_to_db(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> None:
    """Patch over the job creation crud function to simulate successfully adding the job to the database."""
    mock_created_job = JobSchema.model_validate(complete_job_payload)

    # Mock function
    mock_crud_create_job = AsyncMock()
    mock_crud_create_job.return_value = mock_created_job

    monkeypatch.setattr(
        f"{range_api_v1_endpoints_path}.create_job", mock_crud_create_job
    )


@pytest.fixture
def mock_failed_job_add_to_db(
    monkeypatch: pytest.MonkeyPatch, range_api_v1_endpoints_path: str
) -> dict[str, type[Exception] | str]:
    """Patch over the job creation crud function to simulate an exception while adding the job to the database."""
    # Fake exception
    exception_type = RuntimeError
    exception_msg = "Fake error adding job!"

    # Mock function
    mock_crud_create_job = AsyncMock()
    mock_crud_create_job.side_effect = exception_type(exception_msg)

    monkeypatch.setattr(
        f"{range_api_v1_endpoints_path}.create_job", mock_crud_create_job
    )

    return {"exception_type": exception_type, "exception_msg": exception_msg}


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


async def test_deploy_range_no_redis_connection(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_redis_queue_pool_no_connection: None,
) -> None:
    """Test to deploy a range but fail because we are not connected to Redis."""
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

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "connect" in response.json()["detail"].lower()


async def test_deploy_range_deploy_success(  # noqa: PLR0913
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_range_factory: Callable[..., MagicMock],
    mock_redis_queue_pool_successful_job_queue: None,
    mock_successful_fetch_job_info: None,
    mock_successful_job_add_to_db: None,
) -> None:
    """Test to deploy a range successfully with a returned the associated job ID."""
    # Mock range object
    mock_range_factory()

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

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_202_ACCEPTED  # It's an async job
    assert response.json()["id"]  # OpenLabs job ID
    assert response.json()["arq_job_id"]


async def test_deploy_range_queue_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_range_factory: Callable[..., MagicMock],
    mock_redis_queue_pool_failed_job_queue: None,
) -> None:
    """Test to deploy a range returns a 500 when we fail to queue the deploy job."""
    # Mock range object
    mock_range_factory()

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

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "queue" in response.json()["detail"].lower()


async def test_deploy_range_no_job_data_in_redis(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_redis_queue_pool_successful_job_queue: None,
    mock_failed_fetch_job_info: None,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test that we get a 500 error when the endpoint is not able to fetch job details from redis."""
    # Mock range object
    mock_range_factory()

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

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "job" in response.json()["detail"].lower()


async def test_deploy_range_add_job_db_failure(  # noqa: PLR0913
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_redis_queue_pool_successful_job_queue: None,
    mock_successful_fetch_job_info: None,
    mock_failed_job_add_to_db: dict[str, type[Exception] | str],
    caplog: pytest.LogCaptureFixture,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test that we get a 500 error when the endpoint is not able to fetch job details from redis."""
    # Mock range object
    mock_range_factory()

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

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "job" in response.json()["detail"].lower()

    # Check that we properly log the exception
    assert any(
        record.levelno is logging.ERROR and record.exc_info is not None
        for record in caplog.records
    )


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
        "src.app.api.v1.ranges.get_decrypted_secrets", mock_get_decrypted_secrets_false
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


async def test_destroy_range_no_redis_connection(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    mock_redis_queue_pool_no_connection: None,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test to destroy a range but fail because we are not connected to Redis."""
    # Mock range object
    mock_range_factory()

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/1",
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "connect" in response.json()["detail"].lower()


async def test_destroy_range_destroy_success(  # noqa: PLR0913
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    mock_range_factory: Callable[..., MagicMock],
    mock_redis_queue_pool_successful_job_queue: None,
    mock_successful_fetch_job_info: None,
    mock_successful_job_add_to_db: None,
) -> None:
    """Test to destroy a range successfully with a returned the associated job ID."""
    # Mock range object
    mock_range_factory()

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/1",
    )
    assert response.status_code == status.HTTP_202_ACCEPTED  # It's an async job
    assert response.json()["id"]  # OpenLabs job ID
    assert response.json()["arq_job_id"]


async def test_destroy_range_queue_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    mock_range_factory: Callable[..., MagicMock],
    mock_redis_queue_pool_failed_job_queue: None,
) -> None:
    """Test to destroy a range returns a 500 when we fail to queue the destroy job."""
    # Mock range object
    mock_range_factory()

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/1",
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "queue" in response.json()["detail"].lower()


async def test_destroy_range_no_job_data_in_redis(  # noqa: PLR0913
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    mock_range_factory: Callable[..., MagicMock],
    mock_redis_queue_pool_successful_job_queue: None,
    mock_failed_fetch_job_info: None,
) -> None:
    """Test to destroy a range returns a 500 when we fail to queue the destroy job."""
    # Mock range object
    mock_range_factory()

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/1",
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "job" in response.json()["detail"].lower()


async def test_destroy_range_add_job_db_failure(  # noqa: PLR0913
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_retrieve_deployed_range_success: None,
    mock_range_factory: Callable[..., MagicMock],
    mock_redis_queue_pool_successful_job_queue: None,
    mock_successful_fetch_job_info: None,
    mock_failed_job_add_to_db: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test to destroy a range returns a 500 when we fail to queue the destroy job."""
    # Mock range object
    mock_range_factory()

    response = await auth_client.delete(
        f"{BASE_ROUTE}/ranges/1",
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "job" in response.json()["detail"].lower()

    # Check that we properly log the exception
    assert any(
        record.levelno is logging.ERROR and record.exc_info is not None
        for record in caplog.records
    )


async def test_get_range_headers_success(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that we get a 200 response when there is at least one range header found."""
    header = DeployedRangeHeaderSchema.model_validate(valid_deployed_range_data)

    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_deployed_range_headers",
        AsyncMock(return_value=[header]),
    )

    response = await auth_client.get(f"{BASE_ROUTE}/ranges")
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert response_data == [header.model_dump(mode="json")]


async def test_get_range_details_success(
    auth_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that we get a 200 response when the range we request exists."""
    test_range = DeployedRangeSchema.model_validate(valid_deployed_range_data)

    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_deployed_range",
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
