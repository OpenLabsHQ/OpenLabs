from typing import Callable

import pytest
from cdktf import Testing
from cdktf_cdktf_provider_aws.instance import Instance
from cdktf_cdktf_provider_aws.subnet import Subnet
from cdktf_cdktf_provider_aws.vpc import Vpc

from src.app.core.cdktf.ranges.aws_range import AWSRange
from src.app.core.cdktf.ranges.base_range import AbstractBaseRange
from src.app.enums.operating_systems import AWS_OS_MAP
from src.app.enums.regions import OpenLabsRegion
from src.app.enums.specs import AWS_SPEC_MAP
from src.app.schemas.template_range_schema import TemplateRangeSchema
from tests.unit.core.cdktf.config import modify_cidr, one_all_template


@pytest.fixture(scope="module")
def aws_one_all_synthesis(
    range_factory: Callable[
        [type[AbstractBaseRange], TemplateRangeSchema, OpenLabsRegion],
        AbstractBaseRange,
    ],
) -> str:
    """Synthesize AWS stack with one_all_template."""
    # Call the factory with the desired stack, stack name, and region.
    range_obj = range_factory(AWSRange, one_all_template, OpenLabsRegion.US_EAST_1)

    successful_synthesize = range_obj.synthesize()
    if not successful_synthesize:
        pytest.fail("Failed to synthesize test range object!")

    with open(range_obj.get_synth_file_path(), mode="r") as file:
        return file.read()


@pytest.fixture(scope="function")
def aws_range(
    range_factory: Callable[
        [type[AbstractBaseRange], TemplateRangeSchema, OpenLabsRegion],
        AbstractBaseRange,
    ],
) -> AbstractBaseRange:
    """Synthesize AWS stack with one_all_template."""
    # Call the factory with the desired stack, stack name, and region.
    return range_factory(AWSRange, one_all_template, OpenLabsRegion.US_EAST_1)


def test_aws_range_every_vpc_is_valid(aws_one_all_synthesis: str) -> None:
    """Ensure every VPC is valid."""
    assert Testing.to_have_resource(aws_one_all_synthesis, Vpc.TF_RESOURCE_TYPE)

    for vpc in one_all_template.vpcs:
        assert Testing.to_have_resource_with_properties(
            aws_one_all_synthesis,
            Vpc.TF_RESOURCE_TYPE,
            {"tags": {"Name": f"{vpc.name}"}, "cidr_block": str(vpc.cidr)},
        )


def test_aws_range_each_vpc_has_a_public_subnet(aws_one_all_synthesis: str) -> None:
    """Ensure each VPC has at least one public subnet."""
    assert Testing.to_have_resource(aws_one_all_synthesis, Subnet.TF_RESOURCE_TYPE)

    for vpc in one_all_template.vpcs:
        # Generate the new subnet CIDR with third octet = 99
        public_subnet_cidr = modify_cidr(str(vpc.cidr), 99)
        assert Testing.to_have_resource_with_properties(
            aws_one_all_synthesis,
            Subnet.TF_RESOURCE_TYPE,
            {
                "tags": {"Name": f"RangePublicSubnet-{vpc.name}"},
                "cidr_block": str(public_subnet_cidr),
            },
        )


def test_aws_range_each_vpc_has_a_jumpbox_ec2_instance(
    aws_one_all_synthesis: str,
) -> None:
    """Ensure each VPC has a jumpbox EC2 instance."""
    assert Testing.to_have_resource(aws_one_all_synthesis, Instance.TF_RESOURCE_TYPE)

    for vpc in one_all_template.vpcs:
        assert Testing.to_have_resource_with_properties(
            aws_one_all_synthesis,
            Instance.TF_RESOURCE_TYPE,
            {"tags": {"Name": f"JumpBox-{vpc.name}"}},
        )


def test_aws_range_each_vpc_has_at_least_one_subnet(aws_one_all_synthesis: str) -> None:
    """Ensure each VPC has at least one subnet."""
    assert Testing.to_have_resource(aws_one_all_synthesis, Subnet.TF_RESOURCE_TYPE)

    for vpc in one_all_template.vpcs:
        for subnet in vpc.subnets:
            assert Testing.to_have_resource_with_properties(
                aws_one_all_synthesis,
                Subnet.TF_RESOURCE_TYPE,
                {
                    "tags": {"Name": f"{subnet.name}-{vpc.name}"},
                    "cidr_block": str(subnet.cidr),
                },
            )


def test_aws_range_each_subnet_has_at_least_one_ec2_instance(
    aws_one_all_synthesis: str,
) -> None:
    """Ensure each subnet has at least one EC2 instance."""
    assert Testing.to_have_resource(aws_one_all_synthesis, Instance.TF_RESOURCE_TYPE)

    for vpc in one_all_template.vpcs:
        for subnet in vpc.subnets:
            for host in subnet.hosts:
                assert Testing.to_have_resource_with_properties(
                    aws_one_all_synthesis,
                    Instance.TF_RESOURCE_TYPE,
                    {
                        "tags": {"Name": f"{host.hostname}-{vpc.name}"},
                        "ami": str(AWS_OS_MAP[host.os]),
                        "instance_type": str(AWS_SPEC_MAP[host.spec]),
                    },
                )


def test_aws_range_no_secrets(aws_range: AWSRange) -> None:
    """Test that the aws range has_secrets() returns False when one or more secrets are missing."""
    aws_range.secrets.aws_secret_key = "fakeawssecretkey"  # noqa: S105 (Testing)
    aws_range.secrets.aws_access_key = ""
    assert aws_range.has_secrets() is False

    aws_range.secrets.aws_secret_key = ""
    aws_range.secrets.aws_access_key = "fakeawssecretkey"
    assert aws_range.has_secrets() is False

    aws_range.secrets.aws_access_key = ""
    aws_range.secrets.aws_secret_key = ""
    assert aws_range.has_secrets() is False


def test_aws_range_has_secrets(aws_range: AWSRange) -> None:
    """Test that the aws range has_secrets() returns True when all secrets are present."""
    aws_range.secrets.aws_secret_key = "fakeawssecretkey"  # noqa: S105 (Testing)
    aws_range.secrets.aws_access_key = "fakeawssecretkey"
    assert aws_range.has_secrets() is True


def test_aws_range_get_cred_env_vars(aws_range: AWSRange) -> None:
    """Test that the aws range returns the correct terraform environment credential variables."""
    fake_secret_key = "fakeawssecretkey"  # noqa: S105 (Testing)
    fake_access_key = "fakeawsaccesskey"

    aws_range.secrets.aws_secret_key = fake_secret_key
    aws_range.secrets.aws_access_key = fake_access_key

    cred_vars = aws_range.get_cred_env_vars()

    # Check for correct variable existence
    assert "AWS_ACCESS_KEY_ID" in cred_vars
    assert "AWS_SECRET_ACCESS_KEY" in cred_vars

    # Check correct values returned
    assert cred_vars["AWS_ACCESS_KEY_ID"] == fake_access_key
    assert cred_vars["AWS_SECRET_ACCESS_KEY"] == fake_secret_key
