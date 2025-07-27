"""Tests for AWS Pulumi range implementation."""
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pulumi.automation as auto

from src.app.core.pulumi.ranges.aws_range import AWSPulumiRange
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.range_schemas import DeployedRangeCreateSchema
from src.app.schemas.secret_schema import SecretSchema
from tests.unit.core.pulumi.config import one_all_blueprint
from tests.unit.core.pulumi.pulumi_mocks import (
    MockStack,
    TEST_OUTPUTS,
)


@pytest.fixture
def mock_aws_secrets() -> SecretSchema:
    """Create mock AWS secrets for testing."""
    return SecretSchema(
        aws_access_key="AKIA1234567890ABCDEF",
        aws_secret_key="abcdef1234567890abcdef1234567890abcdef12"
    )


@pytest.fixture
def aws_pulumi_range(mock_aws_secrets: SecretSchema) -> AWSPulumiRange:
    """Create AWS Pulumi range for testing."""
    return AWSPulumiRange(
        name="test-aws-range",
        range_obj=one_all_blueprint,
        region=OpenLabsRegion.US_EAST_1,
        secrets=mock_aws_secrets,
        description="Test AWS range for unit testing"
    )


@pytest.fixture
def deployed_aws_range(mock_aws_secrets: SecretSchema) -> AWSPulumiRange:
    """Create deployed AWS Pulumi range for testing."""
    state_data = {"version": 3, "deployment": {"test": "aws-data"}}
    return AWSPulumiRange(
        name="test-aws-range",
        range_obj=one_all_blueprint,
        region=OpenLabsRegion.US_EAST_1,
        secrets=mock_aws_secrets,
        description="Test AWS range for unit testing",
        state_data=state_data
    )


class TestAWSPulumiRange:
    """Test cases for AWSPulumiRange."""
    
    def test_init_aws_range(self, aws_pulumi_range: AWSPulumiRange) -> None:
        """Test AWS Pulumi range initialization."""
        assert aws_pulumi_range.name == "test-aws-range"
        assert aws_pulumi_range.region == OpenLabsRegion.US_EAST_1
        assert not aws_pulumi_range.is_deployed()
        assert aws_pulumi_range.get_state_data() is None
    
    def test_has_secrets_true(self, aws_pulumi_range: AWSPulumiRange) -> None:
        """Test has_secrets returns True when credentials are present."""
        assert aws_pulumi_range.has_secrets() is True
    
    def test_has_secrets_false_missing_access_key(self, mock_aws_secrets: SecretSchema) -> None:
        """Test has_secrets returns False when access key is missing."""
        mock_aws_secrets.aws_access_key = ""
        range_obj = AWSPulumiRange(
            name="test-range",
            range_obj=one_all_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=mock_aws_secrets,
            description="Test range"
        )
        assert range_obj.has_secrets() is False
    
    def test_has_secrets_false_missing_secret_key(self, mock_aws_secrets: SecretSchema) -> None:
        """Test has_secrets returns False when secret key is missing."""
        mock_aws_secrets.aws_secret_key = ""
        range_obj = AWSPulumiRange(
            name="test-range",
            range_obj=one_all_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=mock_aws_secrets,
            description="Test range"
        )
        assert range_obj.has_secrets() is False
    
    def test_has_secrets_false_no_credentials(self) -> None:
        """Test has_secrets returns False when no credentials are provided."""
        empty_secrets = SecretSchema()
        range_obj = AWSPulumiRange(
            name="test-range",
            range_obj=one_all_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=empty_secrets,
            description="Test range"
        )
        assert range_obj.has_secrets() is False
    
    def test_get_cred_env_vars(self, aws_pulumi_range: AWSPulumiRange) -> None:
        """Test credential environment variables generation."""
        env_vars = aws_pulumi_range.get_cred_env_vars()
        
        assert "AWS_ACCESS_KEY_ID" in env_vars
        assert "AWS_SECRET_ACCESS_KEY" in env_vars
        assert env_vars["AWS_ACCESS_KEY_ID"] == "AKIA1234567890ABCDEF"
        assert env_vars["AWS_SECRET_ACCESS_KEY"] == "abcdef1234567890abcdef1234567890abcdef12"
    
    def test_get_config_values(self, aws_pulumi_range: AWSPulumiRange) -> None:
        """Test Pulumi configuration values generation."""
        config_values = aws_pulumi_range.get_config_values()
        
        assert "aws:region" in config_values
        assert "aws:accessKey" in config_values
        assert "aws:secretKey" in config_values
        
        # Check region is set correctly
        assert config_values["aws:region"].value == "us-east-1"
        
        # Check credentials are marked as secret
        assert config_values["aws:accessKey"].secret is True
        assert config_values["aws:secretKey"].secret is True
        
        # Check credential values
        assert config_values["aws:accessKey"].value == "AKIA1234567890ABCDEF"
        assert config_values["aws:secretKey"].value == "abcdef1234567890abcdef1234567890abcdef12"
    
    def test_get_pulumi_program(self, aws_pulumi_range: AWSPulumiRange) -> None:
        """Test Pulumi program function generation."""
        program = aws_pulumi_range.get_pulumi_program()
        
        assert callable(program)
        # The program should be a function that can be called
        # We can't easily test the content without running Pulumi
        assert program.__name__ == "pulumi_program"
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_deploy_aws_range_success(
        self,
        mock_makedirs: AsyncMock,
        mock_to_thread: AsyncMock,
        aws_pulumi_range: AWSPulumiRange
    ) -> None:
        """Test successful AWS range deployment."""
        mock_stack = MockStack("test-stack", TEST_OUTPUTS)
        
        # Mock the async calls in order
        mock_to_thread.side_effect = [
            mock_stack,                   # create_or_select_stack
            None,                         # set_config calls (multiple)
            None,                         # set_config calls (multiple)
            None,                         # set_config calls (multiple)
            mock_stack.up(),              # stack.up()
            mock_stack.export_stack(),    # stack.export_stack()
        ]
        
        with patch.object(aws_pulumi_range, 'cleanup_workspace', return_value=True):
            result = await aws_pulumi_range.deploy()
        
        assert result is not None
        assert isinstance(result, DeployedRangeCreateSchema)
        assert result.name == "test-aws-range"
        assert result.jumpbox_resource_id == "i-1234567890abcdef0"
        assert result.jumpbox_public_ip == "203.0.113.12"
        assert aws_pulumi_range.is_deployed()
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_deploy_aws_range_failure(
        self,
        mock_makedirs: AsyncMock,
        mock_to_thread: AsyncMock,
        aws_pulumi_range: AWSPulumiRange
    ) -> None:
        """Test AWS range deployment failure."""
        mock_to_thread.side_effect = Exception("AWS deployment failed")
        
        with patch.object(aws_pulumi_range, 'cleanup_workspace', return_value=True):
            result = await aws_pulumi_range.deploy()
        
        assert result is None
        assert not aws_pulumi_range.is_deployed()
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_destroy_aws_range_success(
        self,
        mock_makedirs: AsyncMock,
        mock_to_thread: AsyncMock,
        deployed_aws_range: AWSPulumiRange
    ) -> None:
        """Test successful AWS range destruction."""
        mock_stack = MockStack("test-stack")
        
        mock_to_thread.side_effect = [
            mock_stack,                     # create_or_select_stack
            None,                          # set_config calls (multiple)
            None,                          # set_config calls (multiple)
            None,                          # set_config calls (multiple)
            None,                          # import_stack
            mock_stack.destroy(),          # stack.destroy()
        ]
        
        with patch.object(deployed_aws_range, 'cleanup_workspace', return_value=True):
            result = await deployed_aws_range.destroy()
        
        assert result is True
        assert not deployed_aws_range.is_deployed()
    
    def test_aws_range_configuration_different_regions(self, mock_aws_secrets: SecretSchema) -> None:
        """Test AWS range configuration for different regions."""
        # Test US_EAST_2
        range_east2 = AWSPulumiRange(
            name="test-range-east2",
            range_obj=one_all_blueprint,
            region=OpenLabsRegion.US_EAST_2,
            secrets=mock_aws_secrets,
            description="Test range in US East 2"
        )
        
        config_east2 = range_east2.get_config_values()
        assert config_east2["aws:region"].value == "us-east-2"
    
    def test_aws_range_state_management(self, deployed_aws_range: AWSPulumiRange) -> None:
        """Test AWS range state management."""
        # Range should be marked as deployed when initialized with state
        assert deployed_aws_range.is_deployed()
        
        # State data should be retrievable
        state_data = deployed_aws_range.get_state_data()
        assert state_data is not None
        assert "deployment" in state_data
        assert state_data["deployment"]["test"] == "aws-data"
    
    @patch('src.app.utils.crypto.generate_range_rsa_key_pair')
    def test_pulumi_program_key_generation(
        self, 
        mock_key_gen: MagicMock,
        aws_pulumi_range: AWSPulumiRange
    ) -> None:
        """Test that the Pulumi program uses key generation."""
        mock_key_gen.return_value = ("private_key", "public_key")
        
        program = aws_pulumi_range.get_pulumi_program()
        
        # We can't easily execute the program without Pulumi runtime,
        # but we can verify it's callable and has the right signature
        assert callable(program)
        assert program.__name__ == "pulumi_program"