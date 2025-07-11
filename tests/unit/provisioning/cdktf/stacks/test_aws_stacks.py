from typing import Callable

import pytest
from cdktf import Testing as CdktfTesting
from cdktf_cdktf_provider_aws.instance import Instance
from cdktf_cdktf_provider_aws.subnet import Subnet
from cdktf_cdktf_provider_aws.vpc import Vpc

from src.app.enums.operating_systems import AWS_OS_MAP
from src.app.enums.regions import OpenLabsRegion
from src.app.enums.specs import AWS_SPEC_MAP
from src.app.provisioning.cdktf.stacks.aws_stack import AWSStack
from src.app.provisioning.cdktf.stacks.base_stack import AbstractBaseStack
from src.app.schemas.range_schemas import BlueprintRangeSchema
from tests.unit.provisioning.cdktf.config import one_all_blueprint


@pytest.fixture(scope="module")
def aws_one_all_synthesis(
    synthesize_factory: Callable[
        [type[AbstractBaseStack], BlueprintRangeSchema, str, OpenLabsRegion], str
    ],
) -> str:
    """Synthesize AWS stack with one_all_blueprint."""
    # Call the factory with the desired stack, stack name, and region.
    return synthesize_factory(
        AWSStack,
        one_all_blueprint,
        "aws_test_range",
        OpenLabsRegion.US_EAST_1,
    )


def test_aws_stack_every_vpc_is_valid(aws_one_all_synthesis: str) -> None:
    """Ensure every VPC is valid."""
    assert CdktfTesting.to_have_resource(aws_one_all_synthesis, Vpc.TF_RESOURCE_TYPE)

    for vpc in one_all_blueprint.vpcs:
        assert CdktfTesting.to_have_resource_with_properties(
            aws_one_all_synthesis,
            Vpc.TF_RESOURCE_TYPE,
            {"tags": {"Name": f"{vpc.name}"}, "cidr_block": str(vpc.cidr)},
        )


def test_aws_stack_has_a_public_subnet(aws_one_all_synthesis: str) -> None:
    """Ensure each the range stack has one public subnet."""
    assert CdktfTesting.to_have_resource(aws_one_all_synthesis, Subnet.TF_RESOURCE_TYPE)

    assert CdktfTesting.to_have_resource_with_properties(
        aws_one_all_synthesis,
        Subnet.TF_RESOURCE_TYPE,
        {
            "tags": {"Name": "JumpBoxVPCPublicSubnet"},
            "cidr_block": "10.255.99.0/24",
        },
    )


def test_aws_stack_has_a_jumpbox_ec2_instance(
    aws_one_all_synthesis: str,
) -> None:
    """Ensure each the range stack has a jumpbox EC2 instance."""
    assert CdktfTesting.to_have_resource(
        aws_one_all_synthesis, Instance.TF_RESOURCE_TYPE
    )

    assert CdktfTesting.to_have_resource_with_properties(
        aws_one_all_synthesis,
        Instance.TF_RESOURCE_TYPE,
        {"tags": {"Name": "JumpBox"}},
    )


def test_aws_stack_each_vpc_has_at_least_one_subnet(aws_one_all_synthesis: str) -> None:
    """Ensure each VPC has at least one subnet."""
    assert CdktfTesting.to_have_resource(aws_one_all_synthesis, Subnet.TF_RESOURCE_TYPE)

    for vpc in one_all_blueprint.vpcs:
        for subnet in vpc.subnets:
            assert CdktfTesting.to_have_resource_with_properties(
                aws_one_all_synthesis,
                Subnet.TF_RESOURCE_TYPE,
                {
                    "tags": {"Name": f"{subnet.name}"},
                    "cidr_block": str(subnet.cidr),
                },
            )


def test_aws_stack_each_subnet_has_at_least_one_ec2_instance(
    aws_one_all_synthesis: str,
) -> None:
    """Ensure each subnet has at least one EC2 instance."""
    assert CdktfTesting.to_have_resource(
        aws_one_all_synthesis, Instance.TF_RESOURCE_TYPE
    )

    for vpc in one_all_blueprint.vpcs:
        for subnet in vpc.subnets:
            for host in subnet.hosts:
                assert CdktfTesting.to_have_resource_with_properties(
                    aws_one_all_synthesis,
                    Instance.TF_RESOURCE_TYPE,
                    {
                        "tags": {"Name": f"{host.hostname}"},
                        "ami": str(AWS_OS_MAP[host.os]),
                        "instance_type": str(AWS_SPEC_MAP[host.spec]),
                    },
                )
