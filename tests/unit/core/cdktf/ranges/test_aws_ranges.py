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
from src.app.schemas.range_schemas import BlueprintRangeSchema
from tests.unit.core.cdktf.config import modify_cidr, one_all_blueprint


@pytest.fixture(scope="module")
def aws_one_all_synthesis(
    range_factory: Callable[
        [type[AbstractBaseRange], BlueprintRangeSchema, OpenLabsRegion],
        AbstractBaseRange,
    ],
) -> str:
    """Synthesize AWS stack with one_all_blueprint."""
    # Call the factory with the desired stack, stack name, and region.
    range_obj = range_factory(AWSRange, one_all_blueprint, OpenLabsRegion.US_EAST_1)

    successful_synthesize = range_obj.synthesize()
    if not successful_synthesize:
        pytest.fail("Failed to synthesize test range object!")

    with open(range_obj.get_synth_file_path(), mode="r") as file:
        return file.read()


@pytest.fixture(scope="function")
def aws_range(
    range_factory: Callable[
        [type[AbstractBaseRange], BlueprintRangeSchema, OpenLabsRegion],
        AbstractBaseRange,
    ],
) -> AbstractBaseRange:
    """Synthesize AWS stack with one_all_blueprint."""
    # Call the factory with the desired stack, stack name, and region.
    return range_factory(AWSRange, one_all_blueprint, OpenLabsRegion.US_EAST_1)


def test_aws_range_every_vpc_is_valid(aws_one_all_synthesis: str) -> None:
    """Ensure every VPC is valid."""
    assert Testing.to_have_resource(aws_one_all_synthesis, Vpc.TF_RESOURCE_TYPE)

    for vpc in one_all_blueprint.vpcs:
        assert Testing.to_have_resource_with_properties(
            aws_one_all_synthesis,
            Vpc.TF_RESOURCE_TYPE,
            {"tags": {"Name": f"{vpc.name}"}, "cidr_block": str(vpc.cidr)},
        )


def test_aws_range_each_vpc_has_a_public_subnet(aws_one_all_synthesis: str) -> None:
    """Ensure each VPC has at least one public subnet."""
    assert Testing.to_have_resource(aws_one_all_synthesis, Subnet.TF_RESOURCE_TYPE)

    for vpc in one_all_blueprint.vpcs:
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

    for vpc in one_all_blueprint.vpcs:
        assert Testing.to_have_resource_with_properties(
            aws_one_all_synthesis,
            Instance.TF_RESOURCE_TYPE,
            {"tags": {"Name": f"JumpBox-{vpc.name}"}},
        )


def test_aws_range_each_vpc_has_at_least_one_subnet(aws_one_all_synthesis: str) -> None:
    """Ensure each VPC has at least one subnet."""
    assert Testing.to_have_resource(aws_one_all_synthesis, Subnet.TF_RESOURCE_TYPE)

    for vpc in one_all_blueprint.vpcs:
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

    for vpc in one_all_blueprint.vpcs:
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


def test_aws_range_synthesize_exception(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that aws range synthesize() returns False on exception."""

    def fake_get_provider_stack_class() -> None:
        msg = "Forced exception in get_provider_stack_class"
        raise Exception(msg)

    # Patch get_provider_stack_class with the fake function.
    monkeypatch.setattr(
        aws_range, "get_provider_stack_class", fake_get_provider_stack_class
    )

    # Calling synthesize() should now catch the exception and return False.
    result = aws_range.synthesize()
    assert result is False


def test_aws_range_not_synthesized_state_on_init(aws_range: AWSRange) -> None:
    """Test that aws range objects sythesized state variable is false on init."""
    assert not aws_range.is_synthesized()


def test_aws_range_sythesized_state_after_synth(aws_range: AWSRange) -> None:
    """Test that aws range objects synthesized state variable is truth after synth() call."""
    assert aws_range.synthesize()
    assert aws_range.is_synthesized()


def test_aws_range_no_destroy_not_synthesized(aws_range: AWSRange) -> None:
    """Test that aws range.destroy() returns false when range object not synthesized yet."""
    assert not aws_range.destroy()


def test_aws_range_no_deploy_not_synthesized(aws_range: AWSRange) -> None:
    """Test that the aws range.deploy() returns false when range object not synthesized yet."""
    assert not aws_range.deploy()


def test_aws_range_not_deployed_state_when_no_state_file_init(
    aws_range: AWSRange,
) -> None:
    """Test that the aws range is_deployed state variable is false when no state_file is passed in on init."""
    assert not aws_range.is_deployed()


def test_aws_range_get_state_file_none_when_no_state_file_init(
    aws_range: AWSRange,
) -> None:
    """Test that the aws range get_state_file() returns None when no state_file is passed in on init."""
    assert aws_range.get_state_file() is None


def test_aws_range_get_state_file_with_content(aws_range: AWSRange) -> None:
    """Test that aws range get_state_file() returns the state_file variable content."""
    test_state_file = {"test": "Test content"}
    aws_range.state_file = test_state_file
    assert aws_range.get_state_file() == test_state_file


def test_aws_range_get_state_file_path(aws_range: AWSRange) -> None:
    """Test that the aws range get_state_file_path() returns the correct path."""
    correct_path = (
        aws_range.get_synth_dir() / f"terraform.{aws_range.stack_name}.tfstate"
    )
    assert aws_range.get_state_file_path() == correct_path


def test_aws_range_create_state_file_no_content(aws_range: AWSRange) -> None:
    """Test that the aws range create_state_file() returns false when no state_file content available."""
    assert not aws_range.create_state_file()


def test_aws_range_create_state_file(aws_range: AWSRange) -> None:
    """Test that the aws range create_state_file() creates a correct state file."""
    test_state_file = {"test": "Test content"}
    aws_range.state_file = test_state_file

    assert aws_range.synthesize()
    assert aws_range.create_state_file()

    # Test correct content
    state_file_content = ""
    with open(aws_range.get_state_file_path(), mode="r") as file:
        state_file_content = file.read()

    assert state_file_content, "State file is empty when it should have content!"

    loaded_state_file_content = json.loads(state_file_content)
    assert loaded_state_file_content == test_state_file


def test_aws_range_cleanup_synth(aws_range: AWSRange) -> None:
    """Test that aws range cleanup_synth() works after synthesis."""
    assert aws_range.synthesize(), "Failed to synthesize AWS range object!"
    assert aws_range.cleanup_synth()


def test_aws_range_cleanup_synth_exception(
    aws_range: AWSRange, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that aws range cleanup_synth() returns False on exception."""

    # Define a fake rmtree function that always raises an exception.
    def fake_rmtree(path: str, ignore_errors: bool = False) -> None:
        msg = "Forced exception for testing"
        raise OSError(msg)

    # Override shutil.rmtree with our fake function.
    monkeypatch.setattr(shutil, "rmtree", fake_rmtree)

    # Call the cleanup_synth method; it should catch the exception and return False.
    result = aws_range.cleanup_synth()
    assert result is False
