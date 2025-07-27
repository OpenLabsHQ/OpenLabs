"""Tests for Pulumi worker range functions."""
import base64
import copy
from collections.abc import Awaitable
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

import src.app.worker.ranges as worker_range_funcs
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
    deployed_schema_json = copy.deepcopy(valid_deployed_range_data)
    add_key_recursively(deployed_schema_json, "id", generate_random_int)
    return DeployedRangeSchema.model_validate(
        deployed_schema_json, from_attributes=True
    )


@pytest.fixture(scope="module")
def mock_enc_key() -> str:
    """Create a mock encryption key."""
    test_key = b"test_master_key_32_bytes_long___"
    return base64.b64encode(test_key).decode()


@pytest.fixture(scope="function")
def deploy_range() -> Callable[..., Awaitable[dict[str, Any]]]:
    """Get the deploy range worker function."""
    return worker_range_funcs.deploy_range


@pytest.fixture(scope="function")
def destroy_range() -> Callable[..., Awaitable[dict[str, Any]]]:
    """Get the destroy range worker function."""
    return worker_range_funcs.destroy_range


@pytest.fixture
def mock_worker_deploy_range_success(
    mocker: MockerFixture,
    worker_ranges_path: str,
) -> None:
    """Patch all external dependencies to ensure deploy function succeeds."""
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
) -> None:
    """Patch all external dependencies to ensure destroy function succeeds."""
    # Patch database connection
    mocker.patch(f"{worker_ranges_path}.get_db_session_context")

    # Mock user calls
    mock_user = AsyncMock(spec=UserModel)
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.is_admin = False
    mocker.patch(f"{worker_ranges_path}.get_user_by_id", return_value=mock_user)

    # Mock secrets calls
    mock_secrets = AsyncMock(spec=SecretSchema)
    mocker.patch(
        f"{worker_ranges_path}.get_decrypted_secrets", return_value=mock_secrets
    )

    # Patch delete range calls
    mock_delete_deployed_range = AsyncMock()
    fake_range_header = DeployedRangeHeaderSchema.model_validate(
        valid_deployed_range_data
    )
    mock_delete_deployed_range.return_value = fake_range_header
    mocker.patch(
        f"{worker_ranges_path}.delete_deployed_range", mock_delete_deployed_range
    )


class TestPulumiWorkerRanges:
    """Test cases for Pulumi worker range functions."""

    async def test_worker_deploy_range_success(
        self,
        mock_arq_ctx: MagicMock,
        deploy_range: Callable[..., Awaitable[dict[str, Any]]],
        mock_worker_deploy_range_success: None,
        blueprint_range: BlueprintRangeSchema,
        mock_enc_key: str,
        mock_pulumi_range_factory: Callable[..., MagicMock],
    ) -> None:
        """Test that the deploy_range worker function returns data when it succeeds."""
        # Configure the mock Pulumi range for successful deployment
        mock_pulumi_range_factory()

        result = await deploy_range(
            mock_arq_ctx,
            mock_enc_key,
            deploy_request_dump=valid_range_deploy_payload,
            blueprint_range_dump=blueprint_range.model_dump(mode="json"),
            user_id=1,
        )

        assert result is not None
        assert isinstance(result, dict)

    async def test_worker_destroy_range_success(
        self,
        mock_arq_ctx: MagicMock,
        destroy_range: Callable[..., Awaitable[dict[str, Any]]],
        mock_worker_destroy_range_success: None,
        deployed_range: DeployedRangeSchema,
        mock_enc_key: str,
        mock_pulumi_range_factory: Callable[..., MagicMock],
    ) -> None:
        """Test that the destroy_range worker function returns data when it succeeds."""
        # Configure the mock Pulumi range for successful destruction
        mock_pulumi_range_factory()

        result = await destroy_range(
            mock_arq_ctx,
            mock_enc_key,
            deployed_range_dump=deployed_range.model_dump(mode="json"),
            user_id=1,
        )

        assert result is not None
        assert isinstance(result, dict)

    async def test_worker_deploy_range_no_secrets(
        self,
        mock_arq_ctx: MagicMock,
        deploy_range: Callable[..., Awaitable[dict[str, Any]]],
        mock_worker_deploy_range_success: None,
        blueprint_range: BlueprintRangeSchema,
        mock_enc_key: str,
        mock_pulumi_range_factory: Callable[..., MagicMock],
    ) -> None:
        """Test deploy_range fails when no secrets are available."""
        # Configure mock to simulate missing secrets
        mock_pulumi_range_factory(has_secrets=False)

        with pytest.raises(RuntimeError, match="No credentials found"):
            await deploy_range(
                mock_arq_ctx,
                mock_enc_key,
                deploy_request_dump=valid_range_deploy_payload,
                blueprint_range_dump=blueprint_range.model_dump(mode="json"),
                user_id=1,
            )

    async def test_worker_deploy_range_deployment_failure(
        self,
        mock_arq_ctx: MagicMock,
        deploy_range: Callable[..., Awaitable[dict[str, Any]]],
        mock_worker_deploy_range_success: None,
        blueprint_range: BlueprintRangeSchema,
        mock_enc_key: str,
        mock_pulumi_range_factory: Callable[..., MagicMock],
    ) -> None:
        """Test deploy_range fails when deployment fails."""
        # Configure mock to simulate deployment failure
        mock_pulumi_range_factory(deploy=None)

        with pytest.raises(RuntimeError, match="Failed to deploy range"):
            await deploy_range(
                mock_arq_ctx,
                mock_enc_key,
                deploy_request_dump=valid_range_deploy_payload,
                blueprint_range_dump=blueprint_range.model_dump(mode="json"),
                user_id=1,
            )

    async def test_worker_destroy_range_destruction_failure(
        self,
        mock_arq_ctx: MagicMock,
        destroy_range: Callable[..., Awaitable[dict[str, Any]]],
        mock_worker_destroy_range_success: None,
        deployed_range: DeployedRangeSchema,
        mock_enc_key: str,
        mock_pulumi_range_factory: Callable[..., MagicMock],
    ) -> None:
        """Test destroy_range fails when destruction fails."""
        # Configure mock to simulate destruction failure
        mock_pulumi_range_factory(destroy=False)

        with pytest.raises(RuntimeError, match="Failed to deploy range"):  # Note: destroy uses same error message pattern
            await destroy_range(
                mock_arq_ctx,
                mock_enc_key,
                deployed_range_dump=deployed_range.model_dump(mode="json"),
                user_id=1,
            )

    async def test_worker_deploy_range_no_user(
        self,
        mock_arq_ctx: MagicMock,
        deploy_range: Callable[..., Awaitable[dict[str, Any]]],
        blueprint_range: BlueprintRangeSchema,
        mock_enc_key: str,
        mocker: MockerFixture,
        worker_ranges_path: str,
    ) -> None:
        """Test deploy_range raises ValueError when user doesn't exist."""
        user_id = 1

        # Patch database connection
        mocker.patch(f"{worker_ranges_path}.get_db_session_context")

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

    async def test_worker_destroy_range_no_user(
        self,
        mock_arq_ctx: MagicMock,
        destroy_range: Callable[..., Awaitable[dict[str, Any]]],
        deployed_range: DeployedRangeSchema,
        mock_enc_key: str,
        mocker: MockerFixture,
        worker_ranges_path: str,
    ) -> None:
        """Test destroy_range raises ValueError when user doesn't exist."""
        user_id = 1

        # Patch database connection
        mocker.patch(f"{worker_ranges_path}.get_db_session_context")

        # Force no user found
        mocker.patch(f"{worker_ranges_path}.get_user_by_id", return_value=None)

        with pytest.raises(ValueError, match=f"{user_id} not found"):
            await destroy_range(
                mock_arq_ctx,
                mock_enc_key,
                deployed_range_dump=deployed_range.model_dump(mode="json"),
                user_id=user_id,
            )

    async def test_worker_deploy_range_invalid_encryption_key(
        self,
        mock_arq_ctx: MagicMock,
        deploy_range: Callable[..., Awaitable[dict[str, Any]]],
        mock_worker_deploy_range_success: None,
        blueprint_range: BlueprintRangeSchema,
    ) -> None:
        """Test deploy_range fails with invalid encryption key."""
        invalid_key = "invalid_base64_key"

        with pytest.raises(RuntimeError, match="Failed to decode encryption key"):
            await deploy_range(
                mock_arq_ctx,
                invalid_key,
                deploy_request_dump=valid_range_deploy_payload,
                blueprint_range_dump=blueprint_range.model_dump(mode="json"),
                user_id=1,
            )

    async def test_worker_destroy_range_invalid_encryption_key(
        self,
        mock_arq_ctx: MagicMock,
        destroy_range: Callable[..., Awaitable[dict[str, Any]]],
        mock_worker_destroy_range_success: None,
        deployed_range: DeployedRangeSchema,
    ) -> None:
        """Test destroy_range fails with invalid encryption key."""
        invalid_key = "invalid_base64_key"

        with pytest.raises(RuntimeError, match="Failed to decode encryption key"):
            await destroy_range(
                mock_arq_ctx,
                invalid_key,
                deployed_range_dump=deployed_range.model_dump(mode="json"),
                user_id=1,
            )