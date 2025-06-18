import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import pytest
from httpx import AsyncClient

from src.app.enums.providers import OpenLabsProvider
from src.app.schemas.range_schemas import (
    BlueprintRangeCreateSchema,
)
from tests.api_test_utils import (
    add_blueprint_range,
    add_cloud_credentials,
    deploy_range,
    destroy_range,
    get_range,
    login_user,
    register_user,
)

logger = logging.getLogger(__name__)


async def deploy_managed_range(
    client: AsyncClient,
    provider: OpenLabsProvider,
    cloud_credentials_payload: dict[str, Any],
    blueprint_range: BlueprintRangeCreateSchema,
) -> dict[str, Any]:
    """Deploy a single range and returns a dictionary with its data and auth info.

    **Note:** Do not use this to deploy a range with the API manually/in tests. This
    is used by fixtures only for automatic test range deployments.
    """
    # Create new user for this deployment
    _, email, password, _ = await register_user(client)
    await login_user(client, email=email, password=password)

    # Configure and create blueprint
    blueprint_range.provider = provider
    blueprint_payload = blueprint_range.model_dump(mode="json")
    await add_cloud_credentials(client, provider, cloud_credentials_payload)
    blueprint_header = await add_blueprint_range(client, blueprint_payload)
    if not blueprint_header:
        pytest.fail(f"Failed to create range blueprint: {blueprint_payload['name']}")

    # Deploy the range
    deployed_range_header = await deploy_range(client, blueprint_header.id)
    if not deployed_range_header:
        pytest.fail(f"Failed to deploy range blueprint: {blueprint_payload['name']}")

    # Get full deployed range info
    deployed_range = await get_range(client, deployed_range_header.id)
    if not deployed_range:
        pytest.fail(
            f"Failed to get deployed info for range: {deployed_range_header.name}"
        )

    # Return all info needed for the test and for teardown
    return {
        "range_id": deployed_range_header.id,
        "email": email,
        "password": password,
        "deployed_range": deployed_range,
    }


async def destroy_managed_range(
    client: AsyncClient,
    email: str,
    password: str,
    range_id: int,
    provider: OpenLabsProvider,
) -> None:
    """Destroy a single range.

    **Note:** Do not use this to destroy a range manually with the API. This is
    used by fixtures only for automatic test range destroys.
    """
    try:
        # Log back in to the dedicated user to destroy the range
        if await login_user(client, email=email, password=password):
            if not await destroy_range(client, range_id):
                logger.critical(
                    "Destroy failed for range %s in %s! Likely dangling resources left behind.",
                    range_id,
                    provider.value.upper(),
                )
        else:
            logger.critical("Destroy failed! Could not log in as user %s.", email)
    except Exception as e:
        logger.critical(
            "Destroy failed for range %s! Exception: %s", range_id, e, exc_info=True
        )


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
