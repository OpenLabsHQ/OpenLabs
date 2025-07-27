"""Tests for Pulumi base range functionality."""
import json
import shutil
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.core.pulumi.ranges.base_range import AbstractBasePulumiRange
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.range_schemas import BlueprintRangeSchema, DeployedRangeCreateSchema
from src.app.schemas.secret_schema import SecretSchema
from tests.unit.core.pulumi.config import one_all_blueprint
from tests.unit.core.pulumi.pulumi_mocks import (
    MockStack,
    TEST_OUTPUTS,
    mock_create_or_select_stack,
)


class ConcretePulumiRange(AbstractBasePulumiRange):
    """Concrete implementation of AbstractBasePulumiRange for testing."""
    
    def get_pulumi_program(self) -> callable:
        """Return a simple test Pulumi program."""
        def test_program():
            import pulumi
            pulumi.export("test-output", "test-value")
        return test_program
    
    def has_secrets(self) -> bool:
        """Mock implementation."""
        return True
    
    def get_config_values(self) -> Dict[str, Any]:
        """Mock implementation."""
        return {"test:config": {"value": "test"}}


@pytest.fixture
def mock_secrets() -> SecretSchema:
    """Create mock secrets for testing."""
    return SecretSchema(
        aws_access_key_id="test_access_key",
        aws_secret_access_key="test_secret_key"
    )


@pytest.fixture
def pulumi_range(mock_secrets: SecretSchema) -> ConcretePulumiRange:
    """Create a concrete Pulumi range for testing."""
    return ConcretePulumiRange(
        name="test-range",
        range_obj=one_all_blueprint,
        region=OpenLabsRegion.US_EAST_1,
        secrets=mock_secrets,
        description="Test range for unit testing"
    )


@pytest.fixture
def deployed_pulumi_range(mock_secrets: SecretSchema) -> ConcretePulumiRange:
    """Create a deployed Pulumi range for testing."""
    state_data = {"version": 3, "deployment": {"test": "data"}}
    return ConcretePulumiRange(
        name="test-range",
        range_obj=one_all_blueprint,
        region=OpenLabsRegion.US_EAST_1,
        secrets=mock_secrets,
        description="Test range for unit testing",
        state_data=state_data
    )


class TestAbstractBasePulumiRange:
    """Test cases for AbstractBasePulumiRange."""
    
    def test_init_without_state(self, pulumi_range: ConcretePulumiRange) -> None:
        """Test initialization without state data."""
        assert pulumi_range.name == "test-range"
        assert pulumi_range.region == OpenLabsRegion.US_EAST_1
        assert not pulumi_range.is_deployed()
        assert pulumi_range.get_state_data() is None
        assert pulumi_range._stack is None
    
    def test_init_with_state(self, deployed_pulumi_range: ConcretePulumiRange) -> None:
        """Test initialization with state data."""
        assert deployed_pulumi_range.is_deployed()
        assert deployed_pulumi_range.get_state_data() is not None
        assert "deployment" in deployed_pulumi_range.get_state_data()
    
    def test_work_dir_path(self, pulumi_range: ConcretePulumiRange) -> None:
        """Test work directory path generation."""
        work_dir = pulumi_range.get_work_dir()
        assert "pulumi_stacks" in str(work_dir)
        assert pulumi_range.stack_name in str(work_dir)
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_create_stack_success(
        self, 
        mock_makedirs: AsyncMock,
        mock_to_thread: AsyncMock,
        pulumi_range: ConcretePulumiRange
    ) -> None:
        """Test successful stack creation."""
        mock_stack = MockStack("test-stack")
        mock_to_thread.side_effect = [
            mock_stack,  # create_or_select_stack
            None,        # install_plugin
            None,        # set_config calls
        ]
        
        result = await pulumi_range._create_stack()
        
        assert result is True
        assert pulumi_range._stack is not None
        mock_makedirs.assert_called_once()
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_create_stack_failure(
        self,
        mock_makedirs: AsyncMock,
        mock_to_thread: AsyncMock,
        pulumi_range: ConcretePulumiRange
    ) -> None:
        """Test stack creation failure."""
        mock_to_thread.side_effect = Exception("Stack creation failed")
        
        result = await pulumi_range._create_stack()
        
        assert result is False
        assert pulumi_range._stack is None
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_deploy_success(
        self,
        mock_makedirs: AsyncMock,
        mock_to_thread: AsyncMock,
        pulumi_range: ConcretePulumiRange
    ) -> None:
        """Test successful deployment."""
        mock_stack = MockStack("test-stack", TEST_OUTPUTS)
        
        # Mock the async calls in order
        mock_to_thread.side_effect = [
            mock_stack,                   # create_or_select_stack
            None,                         # set_config calls
            mock_stack.up(),              # stack.up()
            mock_stack.export_stack(),    # stack.export_stack()
        ]
        
        with patch.object(pulumi_range, 'cleanup_workspace', return_value=True):
            result = await pulumi_range.deploy()
        
        assert result is not None
        assert isinstance(result, DeployedRangeCreateSchema)
        assert result.name == "test-range"
        assert pulumi_range.is_deployed()
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_deploy_failure(
        self,
        mock_makedirs: AsyncMock,
        mock_to_thread: AsyncMock,
        pulumi_range: ConcretePulumiRange
    ) -> None:
        """Test deployment failure."""
        mock_to_thread.side_effect = Exception("Deployment failed")
        
        with patch.object(pulumi_range, 'cleanup_workspace', return_value=True):
            result = await pulumi_range.deploy()
        
        assert result is None
        assert not pulumi_range.is_deployed()
    
    async def test_destroy_not_deployed(self, pulumi_range: ConcretePulumiRange) -> None:
        """Test destroy when range is not deployed."""
        result = await pulumi_range.destroy()
        assert result is False
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_destroy_success(
        self,
        mock_makedirs: AsyncMock,
        mock_to_thread: AsyncMock,
        deployed_pulumi_range: ConcretePulumiRange
    ) -> None:
        """Test successful destruction."""
        mock_stack = MockStack("test-stack")
        
        mock_to_thread.side_effect = [
            mock_stack,                     # create_or_select_stack
            None,                          # set_config calls
            None,                          # import_stack
            mock_stack.destroy(),          # stack.destroy()
        ]
        
        with patch.object(deployed_pulumi_range, 'cleanup_workspace', return_value=True):
            result = await deployed_pulumi_range.destroy()
        
        assert result is True
        assert not deployed_pulumi_range.is_deployed()
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_destroy_failure(
        self,
        mock_makedirs: AsyncMock,
        mock_to_thread: AsyncMock,
        deployed_pulumi_range: ConcretePulumiRange
    ) -> None:
        """Test destruction failure."""
        mock_to_thread.side_effect = Exception("Destroy failed")
        
        with patch.object(deployed_pulumi_range, 'cleanup_workspace', return_value=True):
            result = await deployed_pulumi_range.destroy()
        
        assert result is False
    
    def test_parse_pulumi_outputs_success(self, pulumi_range: ConcretePulumiRange) -> None:
        """Test successful output parsing."""
        from tests.unit.core.pulumi.pulumi_mocks import MockOutputValue
        
        outputs = {k: MockOutputValue(v) for k, v in TEST_OUTPUTS.items()}
        
        # Use asyncio.run for the async method
        import asyncio
        result = asyncio.run(pulumi_range._parse_pulumi_outputs(outputs))
        
        assert result is not None
        assert isinstance(result, DeployedRangeCreateSchema)
        assert result.name == "test-range"
        assert result.jumpbox_resource_id == "i-1234567890abcdef0"
        assert result.jumpbox_public_ip == "203.0.113.12"
    
    def test_parse_pulumi_outputs_missing_keys(self, pulumi_range: ConcretePulumiRange) -> None:
        """Test output parsing with missing required keys."""
        from tests.unit.core.pulumi.pulumi_mocks import MockOutputValue
        
        # Missing required jumpbox keys
        outputs = {
            "test-range-vpc1-resource-id": MockOutputValue("vpc-12345678"),
        }
        
        import asyncio
        result = asyncio.run(pulumi_range._parse_pulumi_outputs(outputs))
        
        assert result is None
    
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.path.exists', return_value=True)
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    async def test_cleanup_workspace_success(
        self,
        mock_to_thread: AsyncMock,
        mock_exists: AsyncMock,
        pulumi_range: ConcretePulumiRange
    ) -> None:
        """Test successful workspace cleanup."""
        mock_to_thread.return_value = None
        
        result = await pulumi_range.cleanup_workspace()
        
        assert result is True
        mock_to_thread.assert_called_once()
    
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.path.exists', return_value=True)
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    async def test_cleanup_workspace_failure(
        self,
        mock_to_thread: AsyncMock,
        mock_exists: AsyncMock,
        pulumi_range: ConcretePulumiRange
    ) -> None:
        """Test workspace cleanup failure."""
        mock_to_thread.side_effect = Exception("Cleanup failed")
        
        result = await pulumi_range.cleanup_workspace()
        
        assert result is False