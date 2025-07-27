"""Tests for Pulumi range factory."""
import pytest

from src.app.core.pulumi.ranges.aws_range import AWSPulumiRange
from src.app.core.pulumi.ranges.range_factory import PulumiRangeFactory
from src.app.enums.providers import OpenLabsProvider
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.range_schemas import BlueprintRangeSchema
from src.app.schemas.secret_schema import SecretSchema
from tests.unit.core.pulumi.config import one_all_blueprint


@pytest.fixture
def mock_secrets() -> SecretSchema:
    """Create mock secrets for testing."""
    return SecretSchema(
        aws_access_key_id="test_access_key",
        aws_secret_access_key="test_secret_key"
    )


@pytest.fixture
def aws_blueprint() -> BlueprintRangeSchema:
    """Create AWS blueprint for testing."""
    blueprint = one_all_blueprint.model_copy()
    blueprint.provider = OpenLabsProvider.AWS
    return blueprint


class TestPulumiRangeFactory:
    """Test cases for PulumiRangeFactory."""
    
    def test_create_aws_range(
        self, 
        aws_blueprint: BlueprintRangeSchema, 
        mock_secrets: SecretSchema
    ) -> None:
        """Test creating AWS range through factory."""
        range_obj = PulumiRangeFactory.create_range(
            name="test-aws-range",
            range_obj=aws_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=mock_secrets,
            description="Test AWS range from factory"
        )
        
        assert isinstance(range_obj, AWSPulumiRange)
        assert range_obj.name == "test-aws-range"
        assert range_obj.region == OpenLabsRegion.US_EAST_1
        assert range_obj.description == "Test AWS range from factory"
        assert range_obj.secrets == mock_secrets
        assert range_obj.range_obj == aws_blueprint
    
    def test_create_aws_range_with_state(
        self, 
        aws_blueprint: BlueprintRangeSchema, 
        mock_secrets: SecretSchema
    ) -> None:
        """Test creating AWS range with state data."""
        state_data = {"version": 3, "deployment": {"test": "data"}}
        
        range_obj = PulumiRangeFactory.create_range(
            name="test-aws-range",
            range_obj=aws_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=mock_secrets,
            description="Test AWS range with state",
            state_data=state_data
        )
        
        assert isinstance(range_obj, AWSPulumiRange)
        assert range_obj.is_deployed()
        assert range_obj.get_state_data() == state_data
    
    def test_create_range_no_description(
        self, 
        aws_blueprint: BlueprintRangeSchema, 
        mock_secrets: SecretSchema
    ) -> None:
        """Test creating range without description defaults to empty string."""
        range_obj = PulumiRangeFactory.create_range(
            name="test-range",
            range_obj=aws_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=mock_secrets,
            description=None
        )
        
        assert isinstance(range_obj, AWSPulumiRange)
        assert range_obj.description == ""
    
    def test_create_range_invalid_provider(
        self, 
        mock_secrets: SecretSchema
    ) -> None:
        """Test creating range with unsupported provider raises ValueError."""
        # Create a blueprint with unsupported provider
        invalid_blueprint = one_all_blueprint.model_copy()
        invalid_blueprint.provider = "UNSUPPORTED_PROVIDER"  # type: ignore
        
        with pytest.raises(ValueError) as exc_info:
            PulumiRangeFactory.create_range(
                name="test-range",
                range_obj=invalid_blueprint,
                region=OpenLabsRegion.US_EAST_1,
                secrets=mock_secrets,
                description="Test range"
            )
        
        assert "Non-existent provider given" in str(exc_info.value)
        assert "UNSUPPORTED_PROVIDER" in str(exc_info.value)
    
    def test_factory_registry_contains_aws(self) -> None:
        """Test that factory registry contains AWS provider."""
        assert OpenLabsProvider.AWS in PulumiRangeFactory._registry
        assert PulumiRangeFactory._registry[OpenLabsProvider.AWS] == AWSPulumiRange
    
    def test_create_range_different_regions(
        self, 
        aws_blueprint: BlueprintRangeSchema, 
        mock_secrets: SecretSchema
    ) -> None:
        """Test creating ranges in different regions."""
        regions_to_test = [
            OpenLabsRegion.US_EAST_1,
            OpenLabsRegion.US_EAST_2,
        ]
        
        for region in regions_to_test:
            range_obj = PulumiRangeFactory.create_range(
                name=f"test-range-{region.value}",
                range_obj=aws_blueprint,
                region=region,
                secrets=mock_secrets,
                description=f"Test range in {region.value}"
            )
            
            assert isinstance(range_obj, AWSPulumiRange)
            assert range_obj.region == region
            assert range_obj.name == f"test-range-{region.value}"
    
    def test_create_range_preserves_blueprint_data(
        self, 
        aws_blueprint: BlueprintRangeSchema, 
        mock_secrets: SecretSchema
    ) -> None:
        """Test that factory preserves all blueprint data."""
        range_obj = PulumiRangeFactory.create_range(
            name="test-range",
            range_obj=aws_blueprint,
            region=OpenLabsRegion.US_EAST_1,
            secrets=mock_secrets,
            description="Test range"
        )
        
        # Verify blueprint data is preserved
        assert range_obj.range_obj.id == aws_blueprint.id
        assert range_obj.range_obj.name == aws_blueprint.name
        assert range_obj.range_obj.provider == aws_blueprint.provider
        assert len(range_obj.range_obj.vpcs) == len(aws_blueprint.vpcs)
        
        # Verify VPC data is preserved
        for i, vpc in enumerate(aws_blueprint.vpcs):
            range_vpc = range_obj.range_obj.vpcs[i]
            assert range_vpc.name == vpc.name
            assert range_vpc.cidr == vpc.cidr
            assert len(range_vpc.subnets) == len(vpc.subnets)
            
            # Verify subnet data is preserved
            for j, subnet in enumerate(vpc.subnets):
                range_subnet = range_vpc.subnets[j]
                assert range_subnet.name == subnet.name
                assert range_subnet.cidr == subnet.cidr
                assert len(range_subnet.hosts) == len(subnet.hosts)
                
                # Verify host data is preserved
                for k, host in enumerate(subnet.hosts):
                    range_host = range_subnet.hosts[k]
                    assert range_host.hostname == host.hostname
                    assert range_host.os == host.os
                    assert range_host.spec == host.spec