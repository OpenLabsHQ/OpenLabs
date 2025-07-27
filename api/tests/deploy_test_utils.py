import asyncio
import logging
import os
from contextlib import asynccontextmanager
from enum import Enum
from socket import error as SocketError  # noqa: N812
from typing import AsyncGenerator

import paramiko
from httpx import AsyncClient
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from src.app.enums.operating_systems import (
    AWS_SSH_USERNAME_MAP,
    AZURE_SSH_USERNAME_MAP,
    OpenLabsOS,
)
from src.app.enums.providers import OpenLabsProvider

logger = logging.getLogger(__name__)


class RangeType(Enum):
    """Types of deployed ranges used for testing."""

    ONE_ALL = "one_all"
    MULTI = "multi"


def get_provider_test_creds(provider: OpenLabsProvider) -> dict[str, str] | None:
    """Get the configured test cloud credentials for the provider.

    Args:
    ----
        provider (OpenLabsProvider): Supported OpenLabs cloud provider.

    Returns:
    -------
        dict[str, str]: Filled in cloud credential payload if ENV vars set. None otherwise.

    """
    credentials: dict[str, str | None]

    # Select provider configuration
    if provider == OpenLabsProvider.AWS:
        credentials = {
            "aws_access_key": os.environ.get("INTEGRATION_TEST_AWS_ACCESS_KEY"),
            "aws_secret_key": os.environ.get("INTEGRATION_TEST_AWS_SECRET_KEY"),
        }
    else:
        logger.error(
            "Provider '%s' is not configured for integration tests.",
            provider.value.upper(),
        )
        return None

    validated_credentials = {
        key: value for key, value in credentials.items() if value is not None
    }

    if len(validated_credentials) < len(credentials):
        logger.warning("Credentials for %s are not set.", provider.value.upper())
        return None

    return validated_credentials


@asynccontextmanager
async def isolated_integration_client(
    base_url: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide a single, isolated client to the docker compose API."""
    async with AsyncClient(base_url=base_url) as client:
        yield client


def provider_test_id(provider: OpenLabsProvider) -> str | None:
    """Generate test IDs for OpenLabs providers.

    Args:
    ----
        provider (OpenLabsProvider): Provider to generate test ID for.

    Returns:
    -------
        str: Test ID for provider.

    """
    if isinstance(provider, OpenLabsProvider):
        return provider.value.upper()
    logger.error(
        "Failed to generate provider test ID! Expected 'OpenLabsProvider', recieved: %s",
        type(provider),
    )
    return None


def range_test_id(range_type: RangeType) -> str | None:
    """Generate test IDs for tested range types.

    Args:
    ----
        range_type (RangeType): Tested range type to generate ID for.

    Returns:
    -------
        str: Test ID for range type.

    """
    if isinstance(range_type, RangeType):
        return range_type.value.upper()
    logger.error(
        "Failed to generate range type test ID! Expected 'RangeType', recieved: %s",
        type(range_type),
    )
    return None


RETRYABLE_EXCEPTIONS = (
    paramiko.SSHException,
    TimeoutError,
    SocketError,
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),  # Wait 5 seconds between retries
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,  # Reraise the last exception if all retries fail
)
async def ssh_connect_to_host(
    hostname: str,
    username: str,
    private_key: paramiko.PKey,
    jumpbox_transport: paramiko.Transport | None = None,
    jumpbox_public_ip: str | None = None,
) -> paramiko.SSHClient:
    """Establish a SSH connection to a host with retry logic.

    This function can connect directly to a host or tunnel through a jumpbox
    by providing an active `paramiko.Transport`.

    Args:
        hostname: The IP address or hostname of the target machine.
        username: The SSH username for the target machine.
        private_key: The paramiko private key object for authentication.
        jumpbox_transport: Optional transport from an existing jumpbox client for tunneling.
        jumpbox_public_ip: The jumpbox's public IP, required for tunneling.

    Returns:
        A connected `paramiko.SSHClient` instance.

    """
    target_client = paramiko.SSHClient()
    target_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507

    sock = None
    if jumpbox_transport:
        if not jumpbox_public_ip:
            msg = "jumpbox_public_ip is required when using a jumpbox_transport."
            raise ValueError(msg)

        # Create a tunnel ("direct-tcpip" channel) through the jumpbox
        src_addr = (str(jumpbox_public_ip), 22)
        dest_addr = (str(hostname), 22)
        sock = jumpbox_transport.open_channel("direct-tcpip", dest_addr, src_addr)

    await asyncio.to_thread(
        target_client.connect,
        hostname=hostname,
        username=username,
        pkey=private_key,
        sock=sock,
        timeout=15,  # Extra timeout to improve reliability
    )
    return target_client


def get_ssh_username(provider: OpenLabsProvider, os: OpenLabsOS) -> str:
    """Get the default SSH username for a given provider and OS."""
    if provider == OpenLabsProvider.AWS:
        return AWS_SSH_USERNAME_MAP[os]
    if provider == OpenLabsProvider.AZURE:
        return AZURE_SSH_USERNAME_MAP[os]

    msg = f"Unsupported provider-OS combination: {provider}-{os}"
    raise ValueError(msg)
