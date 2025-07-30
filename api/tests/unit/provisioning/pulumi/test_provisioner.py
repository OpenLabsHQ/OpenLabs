from typing import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pulumi
import pytest

from src.app.enums.providers import OpenLabsProvider
from src.app.enums.regions import OpenLabsRegion
from src.app.provisioning.pulumi.provisioner import PulumiOperation


@pytest.fixture(scope="session")
def pulumi_provisioner_path() -> str:
    """Return path to pulumi provisioner file."""
    return "src.app.provisioning.pulumi.provisioner"


@pytest.fixture
def operation_setup(
    monkeypatch: pytest.MonkeyPatch, pulumi_provisioner_path: str
) -> tuple[Callable[..., PulumiOperation], MagicMock]:
    """Initialize the PulumiOperation tests."""
    # Mock the provider registry to return a mock provider
    mock_provider = MagicMock()
    mock_provider.get_pulumi_program.return_value = lambda: None
    mock_provider.get_config_values.return_value = {"aws:region": "us-east-1"}

    # Use setattr to replace the object at the import path.
    monkeypatch.setattr(
        f"{pulumi_provisioner_path}.PROVIDER_REGISTRY",
        {OpenLabsProvider.AWS: mock_provider},
    )

    # Mock schema objects to avoid complex instantiation
    mock_range_obj = MagicMock()
    mock_secrets_obj = MagicMock()

    # Return a factory function to create a new instance for each test
    def _create_operation() -> PulumiOperation:
        return PulumiOperation(
            deployment_id="test-dep-id",
            range_obj=mock_range_obj,
            region=OpenLabsRegion.US_EAST_1,
            provider=OpenLabsProvider.AWS,
            secrets=mock_secrets_obj,
            name="test-range",
            description="A test range",
        )

    return _create_operation, mock_provider


def test_init_success(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
) -> None:
    """Tests successful initialization of the PulumiOperation class."""
    create_op, mock_provider = operation_setup
    op = create_op()

    assert op.stack_name == "ol-test-dep-id"
    assert op.pulumi_provider == mock_provider


def test_init_invalid_provider_raises_error(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
) -> None:
    """Tests that a ValueError is raised for an unknown provider."""
    mock_invalid_provider = MagicMock()
    mock_invalid_provider.value = "BOGUS"

    with pytest.raises(ValueError, match="Provider BOGUS not found"):
        PulumiOperation(
            deployment_id="test-dep-id",
            range_obj=MagicMock(),
            region=OpenLabsRegion.US_EAST_1,
            provider=mock_invalid_provider,  # Invalid provider
            secrets=MagicMock(),
            name="test-range",
            description="A test range",
        )


@pytest.mark.asyncio
async def test_aenter_success(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests the successful entry into the async context manager."""
    create_op, _ = operation_setup
    op = create_op()

    monkeypatch.setattr("aiofiles.os.makedirs", AsyncMock())

    mock_stack = MagicMock()
    mock_stack.set_all_config = MagicMock()
    monkeypatch.setattr(
        pulumi.automation,
        "create_or_select_stack",
        MagicMock(return_value=mock_stack),
    )

    async with op:
        assert op.stack is not None
        mock_stack.set_all_config.assert_called_once()


@pytest.mark.asyncio
async def test_up_success(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
) -> None:
    """Tests the happy path for the 'up' method."""
    create_op, _ = operation_setup
    op = create_op()

    mock_stack = MagicMock()
    mock_stack.up.return_value = MagicMock(
        summary=MagicMock(result="succeeded"), outputs={}
    )
    op.stack = mock_stack

    # Mock _parse_outputs since we are not testing it
    with patch.object(op, "_parse_outputs", return_value="parsed_ok") as mock_parse:
        result = await op.up()
        mock_stack.up.assert_called_once()
        mock_parse.assert_called_once()
        assert result == "parsed_ok"


@pytest.mark.asyncio
async def test_up_raises_error_if_stack_not_initialized(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
) -> None:
    """Tests that 'up' fails if the stack is not initialized."""
    create_op, _ = operation_setup
    op = create_op()
    op.stack = None
    with pytest.raises(RuntimeError, match="Stack not initialized."):
        await op.up()


@pytest.mark.asyncio
async def test_up_raises_error_on_pulumi_failure(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
) -> None:
    """Tests that 'up' raises a RuntimeError if the Pulumi command fails."""
    create_op, _ = operation_setup
    op = create_op()

    mock_stack = MagicMock()
    mock_stack.up.return_value = MagicMock(summary=MagicMock(result="failed"))
    op.stack = mock_stack

    with pytest.raises(RuntimeError, match="up failed"):
        await op.up()


@pytest.mark.asyncio
async def test_destroy_success(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
) -> None:
    """Tests the happy path for the 'destroy' method."""
    create_op, _ = operation_setup
    op = create_op()

    mock_stack = MagicMock()
    mock_stack.destroy.return_value = MagicMock(summary=MagicMock(result="succeeded"))
    op.stack = mock_stack

    await op.destroy()
    mock_stack.destroy.assert_called_once()


@pytest.mark.asyncio
async def test_destroy_raises_error_on_pulumi_failure(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
) -> None:
    """Tests that 'destroy' raises a RuntimeError if the Pulumi command fails."""
    create_op, _ = operation_setup
    op = create_op()

    mock_stack = MagicMock()
    mock_stack.destroy.return_value = MagicMock(summary=MagicMock(result="failed"))
    op.stack = mock_stack

    with pytest.raises(RuntimeError, match="destroy failed"):
        await op.destroy()


@pytest.mark.asyncio
async def test_destroy_raises_error_if_stack_not_initialized(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
) -> None:
    """Tests that 'destroy' fails if the stack is not initialized."""
    create_op, _ = operation_setup
    op = create_op()
    op.stack = None
    with pytest.raises(RuntimeError, match="Stack not initialized."):
        await op.destroy()


def test_check_keys_success(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
) -> None:
    """Test happy path for private _check_keys."""
    create_op, _ = operation_setup
    op = create_op()

    op._check_keys(keys=["key1", "key2"], outputs={"key1": "value", "key2": "value"})


def test_check_keys_raises_error_on_missing_key(
    operation_setup: tuple[Callable[..., PulumiOperation], MagicMock],
) -> None:
    """Tests the private _check_keys helper for its failure case."""
    create_op, _ = operation_setup
    op = create_op()

    with pytest.raises(RuntimeError, match="key2"):
        op._check_keys(keys=["key1", "key2"], outputs={"key1": "value"})
