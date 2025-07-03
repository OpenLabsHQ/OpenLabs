import copy
import re

import pytest
from pydantic import ValidationError

from src.app.schemas.vpc_schemas import DeployedVPCCreateSchema
from tests.unit.api.v1.config import valid_deployed_vpc_data

pytestmark = pytest.mark.unit


def test_deployed_vpc_schema_invalid_public_cidr() -> None:
    """Test that the deployed VPC creation schema fails with public VPC cidrs."""
    public_cidr_vpc = copy.deepcopy(valid_deployed_vpc_data)
    public_cidr_vpc["cidr"] = "177.143.0.0/16"
    expected_msg = re.compile(r"private cidr range", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        DeployedVPCCreateSchema.model_validate(public_cidr_vpc)


def test_deployed_vpc_schema_duplicate_subnet_names() -> None:
    """Test that the deployed VPC creation schema fails when there are duplicate subnet names."""
    duplicate_subnet = copy.deepcopy(valid_deployed_vpc_data["subnets"][0])
    invalid_vpc = copy.deepcopy(valid_deployed_vpc_data)

    # Add duplicate subnet with duplicate name
    invalid_vpc["subnets"].append(duplicate_subnet)

    expected_msg = re.compile(r"unique names", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        DeployedVPCCreateSchema.model_validate(invalid_vpc)


def test_deployed_vpc_schema_subnet_cidr_contain() -> None:
    """Test that the deployed VPC creation schema fails when the subnet CIDR is not contained in the VPC CIDR."""
    invalid_vpc = copy.deepcopy(valid_deployed_vpc_data)

    # Break CIDR contianment
    invalid_vpc["cidr"] = "192.168.0.0/16"
    invalid_vpc["subnets"][0]["cidr"] = "10.0.1.0/24"

    expected_msg = re.compile(r"contained within", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        DeployedVPCCreateSchema.model_validate(invalid_vpc)


def test_deployed_vpc_schema_overlap_subnet_cidr() -> None:
    """Test that the deployed VPC creation schema fails when there are overlapping subnet CIDRs."""
    invalid_vpc = copy.deepcopy(valid_deployed_vpc_data)

    # Add overlapping subnet
    invalid_vpc["cidr"] = "192.168.0.0/16"
    for i, subnet in enumerate(invalid_vpc["subnets"]):
        subnet["cidr"] = f"192.168.1.0/{24 + i}"

    expected_msg = re.compile(r"mutually exclusive", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        DeployedVPCCreateSchema.model_validate(invalid_vpc)
