import logging
import os
from contextlib import asynccontextmanager
from enum import Enum
from typing import AsyncGenerator

from httpx import AsyncClient

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
