import base64
import copy
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
from arq.worker import Worker
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.worker.ranges import deploy_range, destroy_range
from src.app.models.user_model import UserModel
from src.app.schemas.range_schemas import (
    BlueprintRangeSchema,
    DeployedRangeHeaderSchema,
    DeployedRangeSchema,
)
from src.app.schemas.secret_schema import SecretSchema
from tests.common.api.v1.config import (
    valid_blueprint_range_create_payload,
    valid_deployed_range_data,
    valid_range_deploy_payload,
)
from tests.test_utils import add_key_recursively, generate_random_int

pytestmark = pytest.mark.unit


@pytest.fixture
def worker_ranges_path() -> str:
    """Return current path value of the ranges functions used by the ARQ worker."""
    return "src.app.core.worker.ranges"


@pytest.fixture
def mock_arq_ctx() -> MagicMock:
    """Create a mock ARQ worker context."""
    return MagicMock(spec=Worker)


@pytest.fixture
def blueprint_range() -> BlueprintRangeSchema:
    """Get a blueprint range schema for testing."""
    blueprint_schema_json = copy.deepcopy(valid_blueprint_range_create_payload)
    add_key_recursively(blueprint_schema_json, "id", generate_random_int)
    return BlueprintRangeSchema.model_validate(
        blueprint_schema_json, from_attributes=True
    )


@pytest.fixture
def deployed_range() -> DeployedRangeSchema:
    """Get a deployed range schema for testing."""
    return DeployedRangeSchema.model_validate(valid_deployed_range_data)


@pytest.fixture
def mock_enc_key() -> str:
    """Get a base64 string to use for testing functions that need enc_keys."""
    fake_key = "fakekeyvalueherehithere"
    bytes_string = fake_key.encode("utf-8")
    encoded_bytes = base64.b64encode(bytes_string)
    return encoded_bytes.decode("utf-8")


@pytest.fixture
def mock_worker_deploy_range_success(
    mocker: MockerFixture,
    worker_ranges_path: str,
) -> None:
    """Patch over all non-range object external dependencies to ensure the deploy function returns as if successful."""
    # Patch database connection
    mocker.patch(f"{worker_ranges_path}.managed_async_get_db")

    # Mock user calls
    mock_user = AsyncMock(spec=UserModel)
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mocker.patch(f"{worker_ranges_path}.get_user", return_value=mock_user)

    # Mock secrets calls
    mock_secrets = AsyncMock(spec=SecretSchema)
    mocker.patch(
        f"{worker_ranges_path}.get_decrypted_secrets", return_value=mock_secrets
    )

    # Patch create range calls
    mock_range_header = AsyncMock(spec=DeployedRangeHeaderSchema)
    mock_range_header.model_dump.return_value = {"data": "Fake header data"}
    mocker.patch(f"{worker_ranges_path}.create_deployed_range", mock_range_header)


@pytest.fixture
def mock_worker_destroy_range_success(
    mocker: MockerFixture,
    worker_ranges_path: str,
) -> None:
    """Patch over all non-range object external dependencies to ensure the delete function returns as if successful."""
    # Patch database connection
    mocker.patch(f"{worker_ranges_path}.managed_async_get_db")

    # Mock user calls
    mock_user = AsyncMock(spec=UserModel)
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mocker.patch(f"{worker_ranges_path}.get_user", return_value=mock_user)

    # Mock secrets calls
    mock_secrets = AsyncMock(spec=SecretSchema)
    mocker.patch(
        f"{worker_ranges_path}.get_decrypted_secrets", return_value=mock_secrets
    )

    # Patch create range calls
    mock_range_header = AsyncMock(spec=DeployedRangeHeaderSchema)
    mock_range_header.model_dump.return_value = {"data": "Fake header data"}
    mocker.patch(f"{worker_ranges_path}.delete_deployed_range", mock_range_header)


async def test_worker_deploy_range_success(
    mock_arq_ctx: MagicMock,
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test that the deploy_range worker function returns data when it succeeds."""
    email = "nobody@him.com"

    mock_range_factory()

    assert await deploy_range(
        mock_arq_ctx,
        email,
        mock_enc_key,
        deploy_request_dump=valid_range_deploy_payload,
        blueprint_range_dump=blueprint_range.model_dump(mode="json"),
    )


async def test_worker_destroy_range_success(
    mock_arq_ctx: MagicMock,
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test that the destroy_range worker function returns data when it succeeds."""
    email = "nobody@him.com"

    mock_range_factory()

    assert await destroy_range(
        mock_arq_ctx,
        email,
        mock_enc_key,
        deployed_range_dump=deployed_range.model_dump(mode="json"),
    )


async def test_worker_deploy_range_no_user(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
    mocker: MockerFixture,
    worker_ranges_path: str,
) -> None:
    """Test that the deploy_range worker function raises a ValueError when the user who requested deployment doesn't exist in the database."""
    email = "nobody@him.com"

    # Force no user found
    mocker.patch(f"{worker_ranges_path}.get_user", return_value=None)

    with pytest.raises(ValueError, match=f"{email} not found"):
        await deploy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
        )


async def test_worker_destroy_range_no_user(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
    worker_ranges_path: str,
    mocker: MockerFixture,
) -> None:
    """Test that the destroy_range worker function raises a ValueError when the user who requests destruction doesn't exist in the database."""
    email = "nobody@him.com"

    # Force no user found
    mocker.patch(f"{worker_ranges_path}.get_user", return_value=None)

    with pytest.raises(ValueError, match=f"{email} not found"):
        assert await destroy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
        )


async def test_worker_deploy_range_invalid_enc_key(
    mock_arq_ctx: MagicMock,
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
) -> None:
    """Test that the deploy_range worker function raises a RuntimeError when it can't decode the user's encoded master key."""
    email = "nobody@him.com"

    with pytest.raises(RuntimeError, match="encryption key"):
        await deploy_range(
            mock_arq_ctx,
            email,
            enc_key="hi",
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
        )


async def test_worker_destroy_range_invalid_enc_key(
    mock_arq_ctx: MagicMock,
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
) -> None:
    """Test that the destroy_range worker function raises a RuntimeError when it can't decode the user's encoded master key."""
    email = "nobody@him.com"

    with pytest.raises(RuntimeError, match="encryption key"):
        await destroy_range(
            mock_arq_ctx,
            email,
            enc_key="hi",
            deployed_range_dump=deployed_range.model_dump(mode="json"),
        )


async def test_worker_deploy_range_no_decrypted_secrets(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
    mocker: MockerFixture,
    worker_ranges_path: str,
) -> None:
    """Test that the deploy_range worker function raises a RuntimeError when it can't fetch decrypted cloud secrets."""
    email = "nobody@him.com"

    # Force no decrypted secrets found
    mocker.patch(f"{worker_ranges_path}.get_decrypted_secrets", return_value=None)

    with pytest.raises(RuntimeError, match="decrypt"):
        await deploy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
        )


async def test_worker_destroy_range_no_decrypted_secrets(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
    mocker: MockerFixture,
    worker_ranges_path: str,
) -> None:
    """Test that the destroy_range worker function raises a RuntimeError when it can't fetch decrypted cloud secrets."""
    email = "nobody@him.com"

    # Force no decrypted secrets found
    mocker.patch(f"{worker_ranges_path}.get_decrypted_secrets", return_value=None)

    with pytest.raises(RuntimeError, match="decrypt"):
        await destroy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
        )


async def test_worker_deploy_range_invalid_range_secrets(
    mock_arq_ctx: MagicMock,
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test that the deploy_range worker function returns raises a RuntimeError when has_secrets() returns False.

    This happens when the range object checks it's secrets object to determine whether the
    correct values are stored/populated to be able to deploy to the provider specified in
    it's range object (Blueprint, etc.).
    """
    email = "nobody@him.com"

    mock_range_factory(has_secrets=False)

    with pytest.raises(RuntimeError, match="credentials"):
        await deploy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
        )


async def test_worker_destroy_range_invalid_range_secrets(
    mock_arq_ctx: MagicMock,
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test that the destroy_range worker function returns raises a RuntimeError when has_secrets() returns False.

    This happens when the range object checks it's secrets object to determine whether the
    correct values are stored/populated to be able to destroy infrastructure hosted on the
    provider specified in it's range object (Deployed, etc.).
    """
    email = "nobody@him.com"

    mock_range_factory(has_secrets=False)

    with pytest.raises(RuntimeError, match="credentials"):
        await destroy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
        )


async def test_worker_deploy_range_failed_synthesis(
    mock_arq_ctx: MagicMock,
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test that the deploy_range worker function returns raises a RuntimeError when it can't synthesize the range."""
    email = "nobody@him.com"

    mock_range_factory(synthesize=False)

    with pytest.raises(RuntimeError, match="synthesize"):
        await deploy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
        )


async def test_worker_destroy_range_failed_synthesis(
    mock_arq_ctx: MagicMock,
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test that the destroy_range worker function returns raises a RuntimeError when it can't synthesize the range."""
    email = "nobody@him.com"

    mock_range_factory(synthesize=False)

    with pytest.raises(RuntimeError, match="synthesize"):
        await destroy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
        )


async def test_worker_deploy_range_failed_deploy(
    mock_arq_ctx: MagicMock,
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test that the deploy_range worker function returns raises a RuntimeError when it can't deploy the range."""
    email = "nobody@him.com"

    # Dummy falsey value to trigger error
    mock_range_factory(deploy=False)

    with pytest.raises(RuntimeError, match="deploy"):
        await deploy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
        )


async def test_worker_deploy_range_failed_destroy(
    mock_arq_ctx: MagicMock,
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
    mock_range_factory: Callable[..., MagicMock],
) -> None:
    """Test that the destroy_range worker function returns raises a RuntimeError when it can't destroy the range."""
    email = "nobody@him.com"

    mock_range_factory(destroy=False)

    with pytest.raises(RuntimeError, match="deploy"):
        await destroy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
        )


async def test_worker_deploy_range_db_exception_and_failed_clean_up(  # noqa: PLR0913
    mocker: MockerFixture,
    mock_arq_ctx: MagicMock,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
    worker_ranges_path: str,
    mock_range_factory: Callable[..., MagicMock],
    mock_worker_deploy_range_success: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the deploy range function rolls back, attempts to clean up dangling resources, and logs any failed clean up attempts."""
    email = "nobody@him.com"

    # Patch database connection
    mock_db_session = AsyncMock(spec=AsyncSession)

    @asynccontextmanager
    async def fake_managed_async_get_db() -> AsyncGenerator[Any, AsyncMock]:
        yield mock_db_session

    # 3. Patch the original context manager with your fake one.
    mocker.patch(
        f"{worker_ranges_path}.managed_async_get_db", new=fake_managed_async_get_db
    )

    # Patch create range calls to fail
    fake_error_msg = "Mock DB error!"
    mocker.patch(
        f"{worker_ranges_path}.create_deployed_range",
        side_effect=RuntimeError(fake_error_msg),
    )

    # Simulate a failed auto cleanup
    mock_range = mock_range_factory(destroy=False)

    with pytest.raises(RuntimeError, match=fake_error_msg):
        await deploy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
        )

    # Check that db state is corrected
    mock_db_session.rollback.assert_awaited_once()

    # Check we auto destroy the range
    mock_range.destroy.assert_awaited_once()

    # Ensure that we log the failed cleanup
    except_log_keywords = "clean up failed"
    assert any(
        record.levelno == logging.CRITICAL
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_worker_destroy_range_db_failure(  # noqa: PLR0913
    mocker: MockerFixture,
    mock_arq_ctx: MagicMock,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
    worker_ranges_path: str,
    mock_range_factory: Callable[..., MagicMock],
    mock_worker_destroy_range_success: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the destroy range function rolls back the database transaction fails."""
    email = "nobody@him.com"

    # Patch database connection
    mock_db_session = AsyncMock(spec=AsyncSession)

    @asynccontextmanager
    async def fake_managed_async_get_db() -> AsyncGenerator[Any, AsyncMock]:
        yield mock_db_session

    # 3. Patch the original context manager with your fake one.
    mocker.patch(
        f"{worker_ranges_path}.managed_async_get_db", new=fake_managed_async_get_db
    )

    # Patch delete range calls to fail
    mocker.patch(
        f"{worker_ranges_path}.delete_deployed_range",
        return_value=None,
    )

    mock_range_factory()

    with pytest.raises(RuntimeError, match="delete"):
        await destroy_range(
            mock_arq_ctx,
            email,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
        )

    # Check that db state is corrected
    mock_db_session.rollback.assert_awaited_once()

    # Ensure that we log the failed destroy
    except_log_keywords = "delete range"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )
