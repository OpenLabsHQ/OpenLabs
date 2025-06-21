import asyncio
import io

import paramiko
import pytest
from httpx import AsyncClient

from src.app.schemas.range_schemas import DeployedRangeSchema
from tests.api_test_utils import get_range, get_range_key, login_user
from tests.deploy_test_utils import (
    RangeType,
    test_provider_id,
    test_range_id,
)
from tests.integration.api.v1.config import PROVIDER_RANGE_PARAMS, RANGE_TYPE_PARAMS

pytestmark = pytest.mark.integration


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "provider_deployed_ranges_for_provider",
    PROVIDER_RANGE_PARAMS,
    indirect=True,
    ids=test_provider_id,
)
@pytest.mark.parametrize("range_type", RANGE_TYPE_PARAMS, ids=test_range_id)
class TestRange:
    """Test suite for /ranges endpoints using integration client and live cloud infrastructure."""

    async def test_deployed_range_success(
        self,
        provider_deployed_ranges_for_provider: dict[
            RangeType, tuple[DeployedRangeSchema, str, str]
        ],
        range_type: RangeType,
    ) -> None:
        """Test that the deployment was successful.

        If this test fails or has an error that means that the
        range deployment fixture failed. This means that the
        deployment logic in the application is broken.
        """
        deployed_range = provider_deployed_ranges_for_provider[range_type]
        range_info, email, password = deployed_range

        # Check that we recieved auth info
        assert email
        assert password

        # Check that range deployed
        if not range_info:
            pytest.fail("One-all range failed to deploy!")

    async def test_ranges_get_deployed_range(
        self,
        integration_client: AsyncClient,
        provider_deployed_ranges_for_provider: dict[
            RangeType, tuple[DeployedRangeSchema, str, str]
        ],
        range_type: RangeType,
    ) -> None:
        """Test that we can get the deployed range details."""
        deployed_range = provider_deployed_ranges_for_provider[range_type]
        range_info, email, password = deployed_range

        assert await login_user(
            integration_client, email, password
        ), "Failed to login to deployed range account."

        # Attempt to fetch range
        recieved_range_info = await get_range(integration_client, range_info.id)
        assert (
            recieved_range_info
        ), f"Could not retrieve one-all range with ID: {range_info.id}"

        # Validate the data is correct
        assert recieved_range_info.model_dump() == range_info.model_dump()

    async def test_jumpbox_direct_connection(
        self,
        integration_client: AsyncClient,
        provider_deployed_ranges_for_provider: dict[
            RangeType, tuple[DeployedRangeSchema, str, str]
        ],
        range_type: RangeType,
    ) -> None:
        """Test a direct SSH connection to the jumpbox to execute commands.

        This test verifies:
        1.  Successful SSH authentication to the jumpbox.
        2.  The user identity by running the 'id' command.
        3.  Outbound internet connectivity from the jumpbox.
        """
        deployed_range = provider_deployed_ranges_for_provider[range_type]
        range_info, email, password = deployed_range

        assert await login_user(
            integration_client, email, password
        ), "Failed to login to the deployed range account."

        private_key_str = await get_range_key(integration_client, range_info.id)
        assert (
            private_key_str
        ), f"Could not retrieve key for range with ID: {range_info.id}"

        ssh_client = None
        try:
            private_key_file = io.StringIO(private_key_str)
            private_key = paramiko.RSAKey.from_private_key(private_key_file)

            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy()  # noqa: S507
            )

            # Connect directly to the jumpbox using its public IP
            await asyncio.to_thread(
                ssh_client.connect,
                hostname=str(range_info.jumpbox_public_ip),
                username="ubuntu",
                pkey=private_key,
                timeout=10,
            )

            # Validate command exexcution with 'id' command
            _, stdout, stderr = await asyncio.to_thread(ssh_client.exec_command, "id")
            command_output = stdout.read().decode("utf-8").strip()
            error_output = stderr.read().decode("utf-8").strip()

            assert "ubuntu" in command_output
            assert (
                not error_output
            ), f"Error executing 'id' command on jumpbox: {error_output}"
            print("Successfully verified user identity on jumpbox.")

            # Verify internet connectivity
            ip_check_command = "curl -s --max-time 10 ip.me"
            _, stdout, stderr = await asyncio.to_thread(
                ssh_client.exec_command, ip_check_command
            )

            public_ip_output = stdout.read().decode("utf-8").strip()
            error_output = stderr.read().decode("utf-8").strip()

            assert (
                not error_output
            ), f"Error executing internet check on jumpbox: {error_output}"
            assert public_ip_output == str(
                range_info.jumpbox_public_ip
            ), f"Internet check failed: Expected IP '{range_info.jumpbox_public_ip}', but got '{public_ip_output}'"

        except paramiko.AuthenticationException:
            pytest.fail(
                "SSH authentication failed for jumpbox. Check username and private key.",
            )
        finally:
            if ssh_client:
                ssh_client.close()
