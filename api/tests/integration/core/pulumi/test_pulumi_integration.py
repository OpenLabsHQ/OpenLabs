"""Integration tests for Pulumi infrastructure deployment."""
import pytest
from unittest.mock import patch, MagicMock

from src.app.core.pulumi.ranges.aws_range import AWSPulumiRange
from src.app.core.pulumi.ranges.range_factory import PulumiRangeFactory
from src.app.enums.providers import OpenLabsProvider
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.range_schemas import BlueprintRangeSchema
from src.app.schemas.secret_schema import SecretSchema
from tests.unit.core.pulumi.config import one_all_blueprint
from tests.unit.core.pulumi.pulumi_mocks import MockStack, TEST_OUTPUTS


@pytest.fixture
def aws_credentials() -> SecretSchema:
    """Mock AWS credentials for integration tests."""
    return SecretSchema(
        aws_access_key_id="AKIA1234567890ABCDEF",
        aws_secret_access_key="abcdef1234567890abcdef1234567890abcdef12"
    )


@pytest.fixture
def aws_blueprint() -> BlueprintRangeSchema:
    """AWS blueprint for integration tests."""
    blueprint = one_all_blueprint.model_copy()
    blueprint.provider = OpenLabsProvider.AWS
    return blueprint


@pytest.mark.integration
class TestPulumiIntegration:
    """Integration tests for Pulumi deployment system."""
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_full_deployment_lifecycle(
        self,
        mock_makedirs: MagicMock,
        mock_to_thread: MagicMock,
        aws_blueprint: BlueprintRangeSchema,
        aws_credentials: SecretSchema
    ) -> None:
        """Test complete deployment and destruction lifecycle."""
        mock_stack = MockStack("integration-test-stack", TEST_OUTPUTS)
        
        # Mock deployment sequence
        deploy_sequence = [
            mock_stack,                    # create_or_select_stack
            None,                         # install_plugin
            None,                         # set_config calls
            None,                         # set_config calls
            None,                         # set_config calls
            mock_stack.up(),              # stack.up()
            mock_stack.export_stack(),    # stack.export_stack()
        ]
        
        # Mock destruction sequence  
        destroy_sequence = [
            mock_stack,                      # create_or_select_stack
            None,                           # install_plugin
            None,                           # set_config calls
            None,                           # set_config calls
            None,                           # set_config calls
            None,                           # import_stack
            mock_stack.destroy(),           # stack.destroy()
        ]
        
        # Create range using factory
        range_obj = PulumiRangeFactory.create_range(
            name="integration-test-range",
            range_obj=aws_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=aws_credentials,
            description="Integration test range"
        )
        
        assert isinstance(range_obj, AWSPulumiRange)
        assert not range_obj.is_deployed()
        
        # Test deployment
        mock_to_thread.side_effect = deploy_sequence
        
        with patch.object(range_obj, 'cleanup_workspace', return_value=True):
            deployed_range = await range_obj.deploy()
        
        assert deployed_range is not None
        assert deployed_range.name == "integration-test-range"
        assert range_obj.is_deployed()
        
        # Test destruction
        mock_to_thread.side_effect = destroy_sequence
        
        with patch.object(range_obj, 'cleanup_workspace', return_value=True):
            destroy_success = await range_obj.destroy()
        
        assert destroy_success is True
        assert not range_obj.is_deployed()
    
    def test_factory_creates_correct_provider_instance(
        self,
        aws_blueprint: BlueprintRangeSchema,
        aws_credentials: SecretSchema
    ) -> None:
        """Test that factory creates the correct provider instance."""
        # Test AWS provider
        aws_range = PulumiRangeFactory.create_range(
            name="test-aws",
            range_obj=aws_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=aws_credentials,
            description="Test AWS"
        )
        
        assert isinstance(aws_range, AWSPulumiRange)
        assert aws_range.has_secrets()
        
        # Verify AWS-specific methods work
        config_values = aws_range.get_config_values()
        assert "aws:region" in config_values
        assert config_values["aws:region"].value == "us-east-1"
        
        env_vars = aws_range.get_cred_env_vars()
        assert "AWS_ACCESS_KEY_ID" in env_vars
        assert "AWS_SECRET_ACCESS_KEY" in env_vars
    
    @patch('src.app.core.pulumi.ranges.base_range.asyncio.to_thread')
    @patch('src.app.core.pulumi.ranges.base_range.aio_os.makedirs')
    async def test_deployment_failure_cleanup(
        self,
        mock_makedirs: MagicMock,
        mock_to_thread: MagicMock,
        aws_blueprint: BlueprintRangeSchema,
        aws_credentials: SecretSchema
    ) -> None:
        """Test that deployment failure triggers proper cleanup."""
        # Simulate deployment failure
        mock_to_thread.side_effect = Exception("Simulated deployment failure")
        
        range_obj = PulumiRangeFactory.create_range(
            name="failure-test-range",
            range_obj=aws_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=aws_credentials,
            description="Failure test range"
        )
        
        # Mock cleanup to track if it's called
        with patch.object(range_obj, 'cleanup_workspace', return_value=True) as mock_cleanup:
            deployed_range = await range_obj.deploy()
        
        # Deployment should fail
        assert deployed_range is None
        assert not range_obj.is_deployed()
        
        # Cleanup should be called
        mock_cleanup.assert_called_once()
    
    def test_range_state_persistence(
        self,
        aws_blueprint: BlueprintRangeSchema,
        aws_credentials: SecretSchema
    ) -> None:
        """Test that range state is properly managed."""
        state_data = {
            "version": 3,
            "deployment": {
                "test": "state_data",
                "resources": ["resource1", "resource2"]
            }
        }
        
        # Create range with state
        range_with_state = PulumiRangeFactory.create_range(
            name="state-test-range",
            range_obj=aws_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=aws_credentials,
            description="State test range",
            state_data=state_data
        )
        
        assert range_with_state.is_deployed()
        assert range_with_state.get_state_data() == state_data
        
        # Create range without state
        range_without_state = PulumiRangeFactory.create_range(
            name="no-state-test-range",
            range_obj=aws_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=aws_credentials,
            description="No state test range"
        )
        
        assert not range_without_state.is_deployed()
        assert range_without_state.get_state_data() is None
    
    def test_multiple_regions_support(
        self,
        aws_blueprint: BlueprintRangeSchema,
        aws_credentials: SecretSchema
    ) -> None:
        """Test that multiple AWS regions are supported."""
        regions_to_test = [
            (OpenLabsRegion.US_EAST_1, "us-east-1"),
            (OpenLabsRegion.US_EAST_2, "us-east-2"),
        ]
        
        for openlabs_region, aws_region in regions_to_test:
            range_obj = PulumiRangeFactory.create_range(
                name=f"test-{aws_region}",
                range_obj=aws_blueprint,
                region=openlabs_region,
                secrets=aws_credentials,
                description=f"Test range in {aws_region}"
            )
            
            assert isinstance(range_obj, AWSPulumiRange)
            assert range_obj.region == openlabs_region
            
            config_values = range_obj.get_config_values()
            assert config_values["aws:region"].value == aws_region