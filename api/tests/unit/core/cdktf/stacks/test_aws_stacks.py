from typing import Any, Callable

import pytest
from cdktf import Testing as CdktfTesting
from cdktf_cdktf_provider_aws.instance import Instance
from cdktf_cdktf_provider_aws.subnet import Subnet
from cdktf_cdktf_provider_aws.vpc import Vpc

from src.app.core.cdktf.ranges.aws_range import AWSRange
from src.app.core.cdktf.ranges.base_range import AbstractBaseRange
from src.app.core.cdktf.stacks.aws_stack import AWS_MAX_NAME_LEN
from src.app.enums.operating_systems import AWS_OS_MAP
from src.app.enums.regions import OpenLabsRegion
from src.app.enums.specs import AWS_SPEC_MAP
from src.app.schemas.range_schemas import BlueprintRangeSchema
from src.app.utils.hash_utils import generate_short_hash
from src.app.utils.name_utils import CloudResourceNamer
from tests.unit.core.cdktf.config import one_all_blueprint


@pytest.fixture(scope="module")
def aws_one_all_synthesis_cloud_namer() -> CloudResourceNamer:
    """Build the cloud namer object for the aws synth fixture."""
    range_name = "aws-one-all-synthesis"
    test_deployment_id = generate_short_hash()[:10]  # Max length allowed
    return CloudResourceNamer(
        deployment_id=test_deployment_id,
        range_name=range_name,
        max_len=AWS_MAX_NAME_LEN,
    )


@pytest.fixture(scope="module")
async def aws_one_all_synthesis(
    range_factory: Callable[
        [
            type[AbstractBaseRange],
            BlueprintRangeSchema,
            OpenLabsRegion,
            dict[str, Any] | None,
            str | None,
            str,
        ],
        AbstractBaseRange,
    ],
    aws_one_all_synthesis_cloud_namer: CloudResourceNamer,
) -> str:
    """Synthesize AWS stack with one_all_blueprint."""
    # Call the factory with the desired stack, stack name, and region.
    range_obj = range_factory(
        AWSRange,
        one_all_blueprint,
        OpenLabsRegion.US_EAST_1,
        None,
        aws_one_all_synthesis_cloud_namer.deployment_id,
        aws_one_all_synthesis_cloud_namer.range_name,
    )

    successful_synthesize = await range_obj.synthesize()
    if not successful_synthesize:
        pytest.fail("Failed to synthesize test range object!")

    with open(range_obj.get_synth_file_path(), mode="r") as file:
        return file.read()


def test_aws_range_every_vpc_is_valid(
    aws_one_all_synthesis: str, aws_one_all_synthesis_cloud_namer: CloudResourceNamer
) -> None:
    """Ensure every VPC is valid."""
    assert CdktfTesting.to_have_resource(aws_one_all_synthesis, Vpc.TF_RESOURCE_TYPE)

    for vpc in one_all_blueprint.vpcs:
        assert CdktfTesting.to_have_resource_with_properties(
            aws_one_all_synthesis,
            Vpc.TF_RESOURCE_TYPE,
            {
                "tags": {
                    "Name": aws_one_all_synthesis_cloud_namer.gen_cloud_resource_name(
                        vpc.name, unique=False
                    )
                },
                "cidr_block": str(vpc.cidr),
            },
        )


def test_aws_stack_has_a_public_subnet(
    aws_one_all_synthesis: str, aws_one_all_synthesis_cloud_namer: CloudResourceNamer
) -> None:
    """Ensure each VPC has at least one public subnet."""
    assert CdktfTesting.to_have_resource(aws_one_all_synthesis, Subnet.TF_RESOURCE_TYPE)

    assert CdktfTesting.to_have_resource_with_properties(
        aws_one_all_synthesis,
        Subnet.TF_RESOURCE_TYPE,
        {
            "tags": {
                "Name": aws_one_all_synthesis_cloud_namer.gen_cloud_resource_name(
                    "jumpbox-public-subnet", unique=False
                )
            },
            "cidr_block": "10.255.99.0/24",
        },
    )


def test_aws_stack_has_a_jumpbox_ec2_instance(
    aws_one_all_synthesis: str, aws_one_all_synthesis_cloud_namer: CloudResourceNamer
) -> None:
    """Ensure each the range stack has a jumpbox EC2 instance."""
    assert CdktfTesting.to_have_resource(
        aws_one_all_synthesis, Instance.TF_RESOURCE_TYPE
    )

    assert CdktfTesting.to_have_resource_with_properties(
        aws_one_all_synthesis,
        Instance.TF_RESOURCE_TYPE,
        {
            "tags": {
                "Name": aws_one_all_synthesis_cloud_namer.gen_cloud_resource_name(
                    "jumpbox", unique=False
                )
            }
        },
    )


def test_aws_stack_each_vpc_has_at_least_one_subnet(
    aws_one_all_synthesis: str, aws_one_all_synthesis_cloud_namer: CloudResourceNamer
) -> None:
    """Ensure each VPC has at least one subnet."""
    assert CdktfTesting.to_have_resource(aws_one_all_synthesis, Subnet.TF_RESOURCE_TYPE)

    for vpc in one_all_blueprint.vpcs:
        for subnet in vpc.subnets:
            assert CdktfTesting.to_have_resource_with_properties(
                aws_one_all_synthesis,
                Subnet.TF_RESOURCE_TYPE,
                {
                    "tags": {
                        "Name": aws_one_all_synthesis_cloud_namer.gen_cloud_resource_name(
                            subnet.name, unique=False
                        )
                    },
                    "cidr_block": str(subnet.cidr),
                },
            )


def test_aws_stack_each_subnet_has_at_least_one_ec2_instance(
    aws_one_all_synthesis: str, aws_one_all_synthesis_cloud_namer: CloudResourceNamer
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
                        "tags": {
                            "Name": aws_one_all_synthesis_cloud_namer.gen_cloud_resource_name(
                                host.hostname, unique=False
                            )
                        },
                        "ami": str(AWS_OS_MAP[host.os]),
                        "instance_type": str(AWS_SPEC_MAP[host.spec]),
                    },
                )
