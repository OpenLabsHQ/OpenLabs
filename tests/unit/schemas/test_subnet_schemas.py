import copy
import re

import pytest
from pydantic import ValidationError

from src.app.schemas.subnet_schemas import DeployedSubnetCreateSchema
from tests.unit.api.v1.config import valid_deployed_subnet_data

pytestmark = pytest.mark.unit


def test_deployed_subnet_schema_invalid_public_cidr() -> None:
    """Test that the deployed subnet creation schema fails with public subnet cidrs."""
    public_cidr_subnet = copy.deepcopy(valid_deployed_subnet_data)
    public_cidr_subnet["cidr"] = "177.143.0.0/16"
    expected_msg = re.compile(r"private cidr range", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        DeployedSubnetCreateSchema.model_validate(public_cidr_subnet)


def test_deployed_subnet_schema_duplicate_hostnames() -> None:
    """Test that the deployed subnet createion schema fails when there are duplicate hostnames."""
    dup_hostname_subnet = copy.deepcopy(valid_deployed_subnet_data)
    assert len(dup_hostname_subnet["hosts"]) >= 1

    # Add extra host
    extra_host = copy.deepcopy(dup_hostname_subnet["hosts"][0])
    dup_hostname_subnet["hosts"].append(extra_host)

    # Set all hosts with same hostname
    for host in dup_hostname_subnet["hosts"]:
        host["hostname"] = "duplicate-hostname"

    expected_msg = re.compile(r"hostnames.*unique", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        DeployedSubnetCreateSchema.model_validate(dup_hostname_subnet)


def test_deployed_subnet_schema_max_number_hosts() -> None:
    """Test that the deployed subnet creation schema fails when there are more hosts than the subnet CIDR can contain."""
    too_many_hosts_subnet = copy.deepcopy(valid_deployed_subnet_data)
    too_many_hosts_subnet["cidr"] = "192.168.1.0/31"

    # Add 3 hosts to subnet
    for i in range(3):
        extra_host = copy.deepcopy(too_many_hosts_subnet["hosts"][0])
        extra_host["hostname"] += f"-{i}"
        too_many_hosts_subnet["hosts"].append(extra_host)

    expected_msg = re.compile(r"too many hosts", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        DeployedSubnetCreateSchema.model_validate(too_many_hosts_subnet)
