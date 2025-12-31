import base64
import copy
import logging
from collections.abc import Awaitable
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

import src.app.worker.ranges as worker_range_funcs
from src.app.enums.providers import OpenLabsProvider
from src.app.models.user_model import UserModel
from src.app.provisioning.pulumi.provisioner import PulumiOperation
from src.app.schemas.range_schemas import (
    BlueprintRangeSchema,
    DeployedRangeCreateSchema,
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


@pytest.fixture(scope="session")
def worker_ranges_path() -> str:
    """Return current path value of the ranges functions used by the ARQ worker."""
    return "src.app.worker.ranges"


@pytest.fixture(scope="module")
def mock_arq_ctx() -> MagicMock:
    """Create a mock ARQ worker context."""
    return MagicMock()


@pytest.fixture(scope="module")
def blueprint_range() -> BlueprintRangeSchema:
    """Get a blueprint range schema for testing."""
    blueprint_schema_json = copy.deepcopy(valid_blueprint_range_create_payload)
    add_key_recursively(blueprint_schema_json, "id", generate_random_int)
    return BlueprintRangeSchema.model_validate(
        blueprint_schema_json, from_attributes=True
    )


@pytest.fixture(scope="module")
def deployed_range() -> DeployedRangeSchema:
    """Get a deployed range schema for testing."""
    return DeployedRangeSchema.model_validate(valid_deployed_range_data)


@pytest.fixture(scope="module")
def mock_enc_key() -> str:
    """Get a base64 string to use for testing functions that need enc_keys."""
    fake_key = "fakekeyvalueherehithere"
    bytes_string = fake_key.encode("utf-8")
    encoded_bytes = base64.b64encode(bytes_string)
    return encoded_bytes.decode("utf-8")


@pytest.fixture(scope="session")
def deploy_range() -> Callable[..., Awaitable[dict[str, Any]]]:
    """Return unwrapped deploy_range function."""
    return worker_range_funcs.deploy_range.__wrapped__  # type: ignore


@pytest.fixture(scope="session")
def destroy_range() -> Callable[..., Awaitable[dict[str, Any]]]:
    """Return unwrapped destroy range function."""
    return worker_range_funcs.destroy_range.__wrapped__  # type: ignore


@pytest.fixture
def mock_pulumi_provider(mocker: MockerFixture, worker_ranges_path: str) -> MagicMock:
    """Mock the pulumi provider registry."""
    mock_pulumi_provider = MagicMock()

    mock_provider_registry = {
        OpenLabsProvider.AWS: mock_pulumi_provider,
    }
    mocker.patch(f"{worker_ranges_path}.PROVIDER_REGISTRY", new=mock_provider_registry)
    return mock_pulumi_provider


@pytest.fixture
def mock_no_pulumi_provider(mocker: MockerFixture, worker_ranges_path: str) -> None:
    """Mock the pulumi provider registry to be empty."""
    mocker.patch(f"{worker_ranges_path}.PROVIDER_REGISTRY", new={})


@pytest.fixture
def mock_pulumi_operation_class(
    mocker: MockerFixture, worker_ranges_path: str
) -> AsyncMock:
    """Mock the entire PulumiOperation class."""
    pulumi_operation_class_mock = MagicMock(spec=PulumiOperation)

    mocker.patch(
        f"{worker_ranges_path}.PulumiOperation", new=pulumi_operation_class_mock
    )
    return pulumi_operation_class_mock


@pytest.fixture
def mock_pulumi_operation_instance(
    mocker: MockerFixture,
    worker_ranges_path: str,
    mock_pulumi_operation_class: AsyncMock,
) -> AsyncMock:
    """Mock the PulumiOperation class."""
    pulumi_instance_mock = AsyncMock()

    mock_pulumi_operation_class.return_value.__aenter__.return_value = (
        pulumi_instance_mock
    )

    mocker.patch(
        f"{worker_ranges_path}.PulumiOperation", new=mock_pulumi_operation_class
    )

    return pulumi_instance_mock


@pytest.fixture
def mock_worker_deploy_range_success(
    mocker: MockerFixture,
    mock_pulumi_provider: MagicMock,
    worker_ranges_path: str,
    mock_pulumi_operation_instance: AsyncMock,
) -> None:
    """Patch over all non-range object external dependencies to ensure the deploy function returns as if successful."""
    # Patch database connection
    mocker.patch(f"{worker_ranges_path}.get_db_session_context")

    # Mock user calls
    mock_user = AsyncMock(spec=UserModel)
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mocker.patch(f"{worker_ranges_path}.get_user_by_id", return_value=mock_user)

    # Mock secrets calls
    mock_secrets = AsyncMock(spec=SecretSchema)
    mocker.patch(
        f"{worker_ranges_path}.get_decrypted_secrets", return_value=mock_secrets
    )

    # Mock pulumi provider calls
    mock_pulumi_provider.has_secrets.return_value = True

    # Mock pulumi operation instance calls
    mock_pulumi_operation_instance.up.return_value = (
        DeployedRangeCreateSchema.model_validate(valid_deployed_range_data)
    )

    # Patch create range calls
    mock_create_deployed_range = AsyncMock()
    fake_range_header = DeployedRangeHeaderSchema.model_validate(
        valid_deployed_range_data
    )
    mock_create_deployed_range.return_value = fake_range_header
    mocker.patch(
        f"{worker_ranges_path}.create_deployed_range", mock_create_deployed_range
    )


@pytest.fixture
def mock_worker_destroy_range_success(
    mocker: MockerFixture,
    worker_ranges_path: str,
    mock_pulumi_provider: MagicMock,
    mock_pulumi_operation_instance: AsyncMock,
) -> None:
    """Patch over all non-range object external dependencies to ensure the delete function returns as if successful."""
    # Patch database connection
    mocker.patch(f"{worker_ranges_path}.get_db_session_context")

    # Mock user calls
    mock_user = AsyncMock(spec=UserModel)
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mocker.patch(f"{worker_ranges_path}.get_user_by_id", return_value=mock_user)

    # Mock secrets calls
    mock_secrets = AsyncMock(spec=SecretSchema)
    mocker.patch(
        f"{worker_ranges_path}.get_decrypted_secrets", return_value=mock_secrets
    )

    # Mock pulumi provider calls
    mock_pulumi_provider.has_secrets.return_value = True

    # Mock pulumi operation instance calls
    mock_pulumi_operation_instance.destroy.return_value = None

    # Patch create range calls
    mock_delete_deployed_range = AsyncMock()
    fake_range_header = DeployedRangeHeaderSchema.model_validate(
        valid_deployed_range_data
    )
    mock_delete_deployed_range.return_value = fake_range_header
    mocker.patch(
        f"{worker_ranges_path}.delete_deployed_range", mock_delete_deployed_range
    )


async def test_worker_deploy_range_success(
    mock_arq_ctx: MagicMock,
    deploy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
) -> None:
    """Test that the deploy_range worker function returns data when it succeeds."""
    assert await deploy_range(
        mock_arq_ctx,
        mock_enc_key,
        deploy_request_dump=valid_range_deploy_payload,
        blueprint_range_dump=blueprint_range.model_dump(mode="json"),
        user_id=1,
    )


async def test_worker_destroy_range_success(
    mock_arq_ctx: MagicMock,
    destroy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
) -> None:
    """Test that the destroy_range worker function returns data when it succeeds."""
    assert await destroy_range(
        mock_arq_ctx,
        mock_enc_key,
        deployed_range_dump=deployed_range.model_dump(mode="json"),
        user_id=1,
    )


async def test_worker_deploy_range_no_user(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    mock_worker_deploy_range_success: None,
    deploy_range: Callable[..., Awaitable[dict[str, Any]]],
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
    mocker: MockerFixture,
    worker_ranges_path: str,
) -> None:
    """Test that the deploy_range worker function raises a ValueError when the user who requested deployment doesn't exist in the database."""
    user_id = 1

    # Force no user found
    mocker.patch(f"{worker_ranges_path}.get_user_by_id", return_value=None)

    with pytest.raises(ValueError, match=f"{user_id} not found"):
        await deploy_range(
            mock_arq_ctx,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
            user_id=user_id,
        )


async def test_worker_destroy_range_no_user(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    destroy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
    worker_ranges_path: str,
    mocker: MockerFixture,
) -> None:
    """Test that the destroy_range worker function raises a ValueError when the user who requests destruction doesn't exist in the database."""
    user_id = 1

    # Force no user found
    mocker.patch(f"{worker_ranges_path}.get_user_by_id", return_value=None)

    with pytest.raises(ValueError, match=f"{user_id} not found"):
        assert await destroy_range(
            mock_arq_ctx,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
            user_id=user_id,
        )


async def test_worker_deploy_range_invalid_enc_key(
    mock_arq_ctx: MagicMock,
    deploy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
) -> None:
    """Test that the deploy_range worker function raises a RuntimeError when it can't decode the user's encoded master key."""
    with pytest.raises(RuntimeError, match="encryption key"):
        await deploy_range(
            mock_arq_ctx,
            enc_key="hi",
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_destroy_range_invalid_enc_key(
    mock_arq_ctx: MagicMock,
    destroy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
) -> None:
    """Test that the destroy_range worker function raises a RuntimeError when it can't decode the user's encoded master key."""
    with pytest.raises(RuntimeError, match="encryption key"):
        await destroy_range(
            mock_arq_ctx,
            enc_key="hi",
            deployed_range_dump=deployed_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_deploy_range_no_decrypted_secrets(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    deploy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
    mocker: MockerFixture,
    worker_ranges_path: str,
) -> None:
    """Test that the deploy_range worker function raises a RuntimeError when it can't fetch decrypted cloud secrets."""
    # Force no decrypted secrets found
    mocker.patch(f"{worker_ranges_path}.get_decrypted_secrets", return_value=None)

    with pytest.raises(RuntimeError, match="decrypt"):
        await deploy_range(
            mock_arq_ctx,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_destroy_range_no_decrypted_secrets(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    destroy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
    mocker: MockerFixture,
    worker_ranges_path: str,
) -> None:
    """Test that the destroy_range worker function raises a RuntimeError when it can't fetch decrypted cloud secrets."""
    # Force no decrypted secrets found
    mocker.patch(f"{worker_ranges_path}.get_decrypted_secrets", return_value=None)

    with pytest.raises(RuntimeError, match="decrypt"):
        await destroy_range(
            mock_arq_ctx,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_deploy_range_no_pulumi_provider(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    deploy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_deploy_range_success: None,
    mock_no_pulumi_provider: None,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
) -> None:
    """Test that the worker deploy function raises an exception if there is no pulumi provider available."""
    with pytest.raises(RuntimeError, match="provider"):
        await deploy_range(
            mock_arq_ctx,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_destroy_range_invalid_no_pulumi_provider(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    destroy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_destroy_range_success: None,
    mock_no_pulumi_provider: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
) -> None:
    """Test that the worker destroy function raises an exception if there is no pulumi provider available."""
    with pytest.raises(RuntimeError, match="provider"):
        await destroy_range(
            mock_arq_ctx,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_deploy_range_invalid_range_secrets(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    deploy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_pulumi_provider: MagicMock,
    mock_worker_deploy_range_success: None,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
) -> None:
    """Test that the deploy_range worker function returns raises a RuntimeError when has_secrets() returns False.

    This happens when the range object checks it's secrets object to determine whether the
    correct values are stored/populated to be able to deploy to the provider specified in
    it's range object (Blueprint, etc.).
    """
    mock_pulumi_provider.has_secrets.return_value = False

    with pytest.raises(RuntimeError, match="credentials"):
        await deploy_range(
            mock_arq_ctx,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_destroy_range_invalid_range_secrets(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    destroy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_pulumi_provider: MagicMock,
    mock_worker_destroy_range_success: None,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
) -> None:
    """Test that the destroy_range worker function returns raises a RuntimeError when has_secrets() returns False.

    This happens when the range object checks it's secrets object to determine whether the
    correct values are stored/populated to be able to destroy infrastructure hosted on the
    provider specified in it's range object (Deployed, etc.).
    """
    mock_pulumi_provider.has_secrets.return_value = False

    with pytest.raises(RuntimeError, match="credentials"):
        await destroy_range(
            mock_arq_ctx,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_deploy_range_failed_synthesis(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    deploy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_deploy_range_success: None,
    mock_pulumi_operation_class: MagicMock,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
) -> None:
    """Test that the deploy_range worker function returns raises a RuntimeError when it can't synthesize the range.

    Here we are testing that pulumi errors are passed up and properly raised to fail the worker function.
    """
    mock_pulumi_operation_class.return_value.__aenter__.side_effect = RuntimeError(
        "Mock stack synth error!"
    )

    with pytest.raises(RuntimeError, match="synth"):
        await deploy_range(
            mock_arq_ctx,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_destroy_range_failed_synthesis(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    destroy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_destroy_range_success: None,
    mock_pulumi_operation_class: MagicMock,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
) -> None:
    """Test that the destroy_range worker function returns raises a RuntimeError when it can't synthesize the range.

    Here we are testing that pulumi errors are passed up and properly raised to fail the worker function.
    """
    mock_pulumi_operation_class.return_value.__aenter__.side_effect = RuntimeError(
        "Mock stack synth error!"
    )

    with pytest.raises(RuntimeError, match="synth"):
        await destroy_range(
            mock_arq_ctx,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_deploy_range_failed_deploy(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    deploy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_deploy_range_success: None,
    mock_pulumi_operation_instance: AsyncMock,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
) -> None:
    """Test that the deploy_range worker function fails due to pulumi errors from the up (deploy) method."""
    mock_pulumi_operation_instance.up.side_effect = RuntimeError("Mock deploy error!")

    with pytest.raises(RuntimeError, match="deploy"):
        await deploy_range(
            mock_arq_ctx,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
            user_id=1,
        )

    # Check that we attempt cleanup
    mock_pulumi_operation_instance.destroy.assert_awaited_once()


async def test_worker_destroy_range_failed_destroy(  # noqa: PLR0913
    mock_arq_ctx: MagicMock,
    destroy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_worker_destroy_range_success: None,
    mock_pulumi_operation_instance: AsyncMock,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
) -> None:
    """Test that the destroy_range worker function fails due to pulumi errors from the destroy method."""
    mock_pulumi_operation_instance.destroy.side_effect = RuntimeError(
        "Mock destroy error!"
    )

    with pytest.raises(RuntimeError, match="destroy"):
        await destroy_range(
            mock_arq_ctx,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
            user_id=1,
        )


async def test_worker_deploy_range_db_exception_and_failed_clean_up(  # noqa: PLR0913
    mocker: MockerFixture,
    deploy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_arq_ctx: MagicMock,
    blueprint_range: BlueprintRangeSchema,
    mock_enc_key: str,
    worker_ranges_path: str,
    mock_pulumi_operation_instance: AsyncMock,
    mock_worker_deploy_range_success: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the deploy range function rolls back, attempts to clean up dangling resources, and logs any failed clean up attempts."""
    # Patch create range calls to fail
    fake_error_msg = "Mock DB error!"
    mocker.patch(
        f"{worker_ranges_path}.create_deployed_range",
        side_effect=RuntimeError(fake_error_msg),
    )

    # Force destroy error
    mock_pulumi_operation_instance.destroy.side_effect = RuntimeError(
        "Fake destroy error!"
    )

    with pytest.raises(RuntimeError, match=fake_error_msg):
        await deploy_range(
            mock_arq_ctx,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
            user_id=1,
        )

    # Check we auto destroy the range
    mock_pulumi_operation_instance.destroy.assert_awaited_once()

    # Ensure that we log the failed cleanup
    except_log_keywords = "clean up failed"
    assert any(
        record.levelno == logging.CRITICAL
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )


async def test_worker_destroy_range_db_failure(  # noqa: PLR0913
    mocker: MockerFixture,
    destroy_range: Callable[..., Awaitable[dict[str, Any]]],
    mock_arq_ctx: MagicMock,
    deployed_range: DeployedRangeSchema,
    mock_enc_key: str,
    worker_ranges_path: str,
    mock_worker_destroy_range_success: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the destroy range function rolls back the database transaction fails."""
    # Patch delete range calls to fail
    mocker.patch(
        f"{worker_ranges_path}.delete_deployed_range",
        return_value=None,
    )

    with pytest.raises(RuntimeError, match="delete"):
        await destroy_range(
            mock_arq_ctx,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
            user_id=1,
        )

    # Ensure that we log the failed destroy
    except_log_keywords = "delete range"
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and except_log_keywords in record.message.lower()
        for record in caplog.records
    )
