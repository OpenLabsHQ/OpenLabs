from typing import Any

import pytest

from src.app.schemas.template_range_schema import TemplateRangeSchema
from src.app.utils.cdktf_utils import create_cdktf_dir

# Valid payload for comparison
valid_one_all_range_payload: dict[str, Any] = {
    "vpcs": [
        {
            "cidr": "192.168.0.0/16",
            "name": "example-vpc-1",
            "subnets": [
                {
                    "cidr": "192.168.1.0/24",
                    "name": "example-subnet-1",
                    "hosts": [
                        {
                            "hostname": "example-host-1",
                            "os": "debian_11",
                            "spec": "tiny",
                            "size": 8,
                            "tags": ["web", "linux"],
                        }
                    ],
                }
            ],
        },
        {
            "cidr": "10.10.0.0/16",
            "name": "example-vpc-2",
            "subnets": [
                {
                    "cidr": "10.10.1.0/24",
                    "name": "example-subnet-1",
                    "hosts": [
                        {
                            "hostname": "example-host-1",
                            "os": "debian_11",
                            "spec": "tiny",
                            "size": 8,
                            "tags": ["web", "linux"],
                        }
                    ],
                }
            ],
        },
    ],
    "provider": "aws",
    "name": "example-range-2",
    "vnc": False,
    "vpn": False,
}

cyber_range = TemplateRangeSchema.model_validate(
    valid_one_all_range_payload, from_attributes=True
)


# Function to derive a subnet CIDR from the VPC CIDR
def modify_cidr(vpc_cidr: str, new_third_octet: int) -> str:
    """Dervies public subnet with third octet = 99 from the vpc cidr block."""
    ip_part, prefix = vpc_cidr.split("/")
    octets = ip_part.split(".")
    octets[2] = str(new_third_octet)  # Change the third octet
    octets[3] = "0"  # Explicitly set the fourth octet to 0
    return f"{'.'.join(octets)}/24"  # Convert back to CIDR


@pytest.fixture(scope="module")
def synthesized() -> str:
    """Synthesizes the CDKTF stack to JSON once for all tests."""
    from cdktf import Testing

    from src.app.core.cdktf.stacks.aws_stack import AWSStack
    from src.app.enums.regions import OpenLabsRegion

    app = Testing.app()
    test_dir = create_cdktf_dir()
    return str(
        Testing.synth(
            AWSStack(app, cyber_range, "test_range", test_dir, OpenLabsRegion.US_EAST_1)
        )
    )


def test_every_vpc_is_valid(synthesized: str) -> None:
    """Ensure every VPC is valid."""
    from cdktf import Testing
    from cdktf_cdktf_provider_aws.vpc import Vpc

    assert Testing.to_have_resource(synthesized, Vpc.TF_RESOURCE_TYPE)

    for vpc in cyber_range.vpcs:
        assert Testing.to_have_resource_with_properties(
            synthesized,
            Vpc.TF_RESOURCE_TYPE,
            {"tags": {"Name": f"{vpc.name}"}, "cidr_block": str(vpc.cidr)},
        )


def test_each_vpc_has_a_public_subnet(synthesized: str) -> None:
    """Ensure each VPC has at least one public subnet."""
    from cdktf import Testing
    from cdktf_cdktf_provider_aws.subnet import Subnet

    assert Testing.to_have_resource(synthesized, Subnet.TF_RESOURCE_TYPE)

    for vpc in cyber_range.vpcs:
        # Generate the new subnet CIDR with third octet = 99
        public_subnet_cidr = modify_cidr(str(vpc.cidr), 99)
        assert Testing.to_have_resource_with_properties(
            synthesized,
            Subnet.TF_RESOURCE_TYPE,
            {
                "tags": {"Name": f"RangePublicSubnet-{vpc.name}"},
                "cidr_block": str(public_subnet_cidr),
            },
        )


def test_each_vpc_has_a_jumpbox_ec2_instance(synthesized: str) -> None:
    """Ensure each VPC has a jumpbox EC2 instance."""
    from cdktf import Testing
    from cdktf_cdktf_provider_aws.instance import Instance

    assert Testing.to_have_resource(synthesized, Instance.TF_RESOURCE_TYPE)

    for vpc in cyber_range.vpcs:
        assert Testing.to_have_resource_with_properties(
            synthesized,
            Instance.TF_RESOURCE_TYPE,
            {"tags": {"Name": f"JumpBox-{vpc.name}"}},
        )


def test_each_vpc_has_at_least_one_subnet(synthesized: str) -> None:
    """Ensure each VPC has at least one subnet."""
    from cdktf import Testing
    from cdktf_cdktf_provider_aws.subnet import Subnet

    assert Testing.to_have_resource(synthesized, Subnet.TF_RESOURCE_TYPE)

    for vpc in cyber_range.vpcs:
        for subnet in vpc.subnets:
            assert Testing.to_have_resource_with_properties(
                synthesized,
                Subnet.TF_RESOURCE_TYPE,
                {
                    "tags": {"Name": f"{subnet.name}-{vpc.name}"},
                    "cidr_block": str(subnet.cidr),
                },
            )


def test_each_subnet_has_at_least_one_ec2_instance(synthesized: str) -> None:
    """Ensure each subnet has at least one EC2 instance."""
    from cdktf import Testing
    from cdktf_cdktf_provider_aws.instance import Instance

    from src.app.enums.operating_systems import AWS_OS_MAP
    from src.app.enums.specs import AWS_SPEC_MAP

    assert Testing.to_have_resource(synthesized, Instance.TF_RESOURCE_TYPE)

    for vpc in cyber_range.vpcs:
        for subnet in vpc.subnets:
            for host in subnet.hosts:
                assert Testing.to_have_resource_with_properties(
                    synthesized,
                    Instance.TF_RESOURCE_TYPE,
                    {
                        "tags": {"Name": f"{host.hostname}-{vpc.name}"},
                        "ami": str(AWS_OS_MAP[host.os]),
                        "instance_type": str(AWS_SPEC_MAP[host.spec]),
                    },
                )
