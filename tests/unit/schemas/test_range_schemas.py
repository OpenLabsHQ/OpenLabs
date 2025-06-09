import copy
import re

import pytest
from pydantic import ValidationError

from src.app.schemas.range_schemas import DeployedRangeCreateSchema
from tests.unit.api.v1.config import valid_deployed_range_data


def test_deployed_range_schema_duplicate_vpc_names() -> None:
    """Test that the deployed range creation schema fails when there are duplicate VPC names."""
    duplicate_vpc = copy.deepcopy(valid_deployed_range_data["vpcs"][0])
    invalid_range = copy.deepcopy(valid_deployed_range_data)

    # Add duplicate VPC with duplicate name
    invalid_range["vpcs"].append(duplicate_vpc)

    expected_msg = re.compile(r"unique names", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        DeployedRangeCreateSchema.model_validate(invalid_range)


def test_deployed_range_schema_overlap_vpc_cidr() -> None:
    """Test that the deployed range creation schema fails when there are overlapping VPC CIDRs."""
    invalid_range = copy.deepcopy(valid_deployed_range_data)

    # Add overlapping VPC
    assert len(invalid_range["vpcs"]) >= 1
    duplicate_vpc = copy.deepcopy(invalid_range["vpcs"][0])
    duplicate_vpc["name"] = invalid_range["vpcs"][0]["name"] + "-1"
    invalid_range["vpcs"].append(duplicate_vpc)

    for i, vpc in enumerate(invalid_range["vpcs"]):
        vpc["cidr"] = f"192.168.0.0/{i + 16}"

        # Avoid subnet cidr containment errors
        for y, subnet in enumerate(vpc["subnets"]):
            subnet["cidr"] = f"192.168.{y + 1}.0/24"

    expected_msg = re.compile(r"mutually exclusive", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        DeployedRangeCreateSchema.model_validate(invalid_range)
