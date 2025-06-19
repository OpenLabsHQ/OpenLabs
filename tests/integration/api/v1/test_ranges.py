import io
import sys

import paramiko
import pytest
from httpx import AsyncClient

from src.app.schemas.range_schemas import DeployedRangeSchema
from tests.api_test_utils import get_range, get_range_key, login_user
from tests.integration.api.v1.config import PROVIDER_DEPLOYED_RANGE_PARAMS

pytestmark = pytest.mark.integration


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "parallel_deployed_ranges_for_provider",
    PROVIDER_DEPLOYED_RANGE_PARAMS,
    indirect=True,
)
class TestRangeOneAll:
    """Test suite for /ranges endpoints using integration client, live cloud infrastructure, and the one-all range blueprint."""

    async def test_one_all_deployed_range(
        self,
        one_all_deployed_range: tuple[DeployedRangeSchema, str, str],
    ) -> None:
        """Test that the deployment was successful.

        If this test fails or has an error that means that the AWS
        one-all range deployment fixture failed. This means that the
        deployment logic in the application is broken.
        """
        range_info, email, password = one_all_deployed_range

        # Check that we recieved auth info
        assert email
        assert password

        # Check that range deployed
        if not range_info:
            pytest.fail("One-all range failed to deploy!")

    async def test_ranges_get_deployed_range_one_all(
        self,
        integration_client: AsyncClient,
        one_all_deployed_range: tuple[DeployedRangeSchema, str, str],
    ) -> None:
        """Test that we can get the one-all deployed range details."""
        range_info, email, password = one_all_deployed_range

        assert await login_user(
            integration_client, email, password
        ), "Failed to login to one-all deployed range account."

        # Attempt to fetch range
        recieved_range_info = await get_range(integration_client, range_info.id)
        assert (
            recieved_range_info
        ), f"Could not retrieve one-all range with ID: {range_info.id}"

        # Validate the data is correct
        assert recieved_range_info.model_dump() == range_info.model_dump()

    async def test_ranges_test_jumpbox_ssh_one_all(
        self,
        integration_client: AsyncClient,
        one_all_deployed_range: tuple[DeployedRangeSchema, str, str],
    ) -> None:
        """Test that we can SSH into the jumpbox using the lab's range key and execute a command."""
        range_info, email, password = one_all_deployed_range

        assert await login_user(
            integration_client, email, password
        ), "Failed to login to one-all deployed range account."

        # Get range key
        private_key_str = await get_range_key(integration_client, range_info.id)
        assert (
            private_key_str
        ), f"Could not retrieve key for one-all range with ID: {range_info.id}"

        try:
            private_key_file = io.StringIO(private_key_str)
            private_key = paramiko.RSAKey.from_private_key(private_key_file)

            with paramiko.SSHClient() as ssh_client:
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # Connect using the private key object
                ssh_client.connect(
                    hostname=str(range_info.jumpbox_public_ip),
                    username="ubuntu",
                    pkey=private_key,
                )

                # Execute the 'id' command
                _, stdout, stderr = ssh_client.exec_command("id")

                # TODO: Come up with a better check?
                command_output = stdout.read().decode("utf-8").strip()
                assert "ubuntu" in command_output

                error_output = stderr.read().decode("utf-8").strip()
                assert not error_output

        except paramiko.AuthenticationException:
            print(
                "Authentication failed. Check username and private key.",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "parallel_deployed_ranges_for_provider",
    PROVIDER_DEPLOYED_RANGE_PARAMS,
    indirect=True,
)
class TestRangeMulti:
    """Test suite for /ranges endpoints using integration client, live cloud infrastructure, and the multi-vpc/subnet/host range blueprint."""

    async def test_multi_deployed_range(
        self,
        multi_deployed_range: tuple[DeployedRangeSchema, str, str],
    ) -> None:
        """Test that the deployment was successful.

        If this test fails or has an error that means that the AWS
        one-all range deployment fixture failed. This means that the
        deployment logic in the application is broken.
        """
        range_info, email, password = multi_deployed_range

        # Check that we recieved auth info
        assert email
        assert password

        # Check that range deployed
        if not range_info:
            pytest.fail("Multi range failed to deploy!")

    async def test_ranges_get_deployed_range_multi(
        self,
        integration_client: AsyncClient,
        multi_deployed_range: tuple[DeployedRangeSchema, str, str],
    ) -> None:
        """Test that we can get the multi deployed range details."""
        range_info, email, password = multi_deployed_range

        assert await login_user(
            integration_client, email, password
        ), "Failed to login to multi deployed range account."

        # Attempt to fetch range
        recieved_range_info = await get_range(integration_client, range_info.id)
        assert (
            recieved_range_info
        ), f"Could not retrieve multi range with ID: {range_info.id}"

        # Validate the data is correct
        assert recieved_range_info.model_dump() == range_info.model_dump()
