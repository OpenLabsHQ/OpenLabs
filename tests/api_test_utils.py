import asyncio
import copy
import logging
import uuid
from typing import Any

from fastapi import status
from httpx import AsyncClient

from src.app.enums.providers import OpenLabsProvider
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.range_schemas import (
    BlueprintRangeHeaderSchema,
    DeployedRangeHeaderSchema,
    DeployedRangeKeySchema,
    DeployedRangeSchema,
)
from src.app.utils.api_utils import get_api_base_route
from tests.unit.api.v1.config import (
    BASE_ROUTE,
    base_user_login_payload,
    base_user_register_payload,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def wait_for_fastapi_service(base_url: str, timeout: int = 30) -> bool:
    """Poll the FastAPI health endpoint until it returns a 200 status code or the timeout is reached."""
    url = f"{base_url}/health/ping"
    start = asyncio.get_event_loop().time()

    while True:
        try:
            async with AsyncClient() as client:
                response = await client.get(url)
            if response.status_code == status.HTTP_200_OK:
                logger.info("FastAPI service is available.")
                return True
        except Exception as e:
            logger.debug("FastAPI service not yet available: %s", e)

        # Wait
        await asyncio.sleep(1)

        # Timeout expired
        if asyncio.get_event_loop().time() - start > timeout:
            logger.error("FastAPI service did not become available in time.")
            return False


async def register_user(
    client: AsyncClient,
    email: str | None = None,
    password: str | None = None,
    name: str | None = None,
) -> tuple[int, str, str, str]:
    """Register a user using the provided client.

    Optionally, provide a specific email, password, and name for the registered user.

    Args:
    ----
        client (AsyncClient): Client object to interact with the API.
        email (Optional[str]): Email to use for registration. Random email used if not provided.
        password (Optional[str]): Password to use for registration. Random password used if not provided.
        name (Optional[str]): Name to use for registration. Random name used if not provided.

    Returns:
    -------
        int: ID of newly registered user.
        str: Email of registered user.
        str: Password of registered user.
        str: Name of the registered user.

    """
    registration_payload = copy.deepcopy(base_user_register_payload)

    unique_str = str(uuid.uuid4())

    # Create unique email
    if not email:
        email_split = registration_payload["email"].split("@")
        email_split_len = 2  # username and domain from email
        assert len(email_split) == email_split_len
        email = f"{email_split[0]}-{unique_str}@{email_split[1]}"

    # Make name unique for debugging
    if not name:
        name = f"{registration_payload['name']} {unique_str}"

    # Create unique password
    if not password:
        password = f"password-{unique_str}"

    # Build payload with values
    registration_payload["email"] = email
    registration_payload["password"] = password
    registration_payload["name"] = name

    # Register user
    response = await client.post(
        f"{BASE_ROUTE}/auth/register", json=registration_payload
    )
    assert response.status_code == status.HTTP_200_OK, "Failed to register user."

    user_id = int(response.json()["id"])
    assert user_id, "Failed to retrieve test user ID."

    return user_id, email, password, name


async def login_user(client: AsyncClient, email: str, password: str) -> bool:
    """Login into an existing/registered user.

    Sets authentication cookies secure = False to allow for HTTP transportation.
    Ensure that this function is only used in a test environment and sent to
    localhost only.

    Args:
    ----
        client (AsyncClient): Client to login with.
        email (str): Email of user to login as.
        password (str): Password of user to login as.

    Returns:
    -------
        bool: True if successfully logged in. False otherwise.

    """
    if not email:
        msg = "Did not provide an email to login with!"
        raise ValueError(msg)

    if not password:
        msg = "Did not provide a password to login with!"
        raise ValueError(msg)

    # Build login payload
    login_payload = copy.deepcopy(base_user_login_payload)
    login_payload["email"] = email
    login_payload["password"] = password

    # Login
    response = await client.post(f"{BASE_ROUTE}/auth/login", json=login_payload)
    if response.status_code != status.HTTP_200_OK:
        logger.error("Failed to login as user: %s", email)
        return False

    # Make cookies non-secure (Works with HTTP)
    for cookie in client.cookies.jar:
        cookie.secure = False

    return True


async def logout_user(client: AsyncClient) -> bool:
    """Logout out of current user.

    Returns
    -------
        bool: True if successful. False otherwise.

    """
    response = await client.post(f"{BASE_ROUTE}/auth/logout")
    return response.status_code == status.HTTP_200_OK


async def authenticate_client(
    client: AsyncClient,
    email: str | None = None,
    password: str | None = None,
    name: str | None = None,
) -> bool:
    """Register and login a user using the provided client.

    This function is here for convinience stringing together register_user
    and login_user.

    Args:
    ----
        client (AsyncClient): Client object to interact with the API.
        email (Optional[str]): Email to use for registration. Random email used if not provided.
        password (Optional[str]): Password to use for registration. Random password used if not provided.
        name (Optional[str]): Name to use for registration. Random name used if not provided.


    Returns:
    -------
        bool: True if successfully logged in. False otherwise.

    """
    _, email, password, _ = await register_user(client, email, password, name)
    return await login_user(client, email, password)


async def is_logged_in(client: AsyncClient) -> bool:
    """Check whether an httpx client is authenticated to the API.

    Args:
    ----
        client (AsyncClient): Any httpx client.

    Returns:
    -------
        bool: True if client is currently logged in. False otherwise.

    """
    base_route = get_api_base_route(version=1)

    # Verify we are logged in
    response = await client.get(f"{base_route}/users/me")
    if response.status_code != status.HTTP_200_OK:
        logger.error("Client is not logged in!")
        return False

    return True


async def add_cloud_credentials(
    auth_client: AsyncClient,
    provider: OpenLabsProvider,
    credentials_payload: dict[str, Any],
) -> bool:
    """Add cloud credentials to the authenticated client's account.

    Args:
    ----
        auth_client (AsyncClient): Any authenticated httpx client. NOT THE `auth_client` FIXTURE!
        provider (OpenLabsProvider): A valid OpenLabs cloud provider to configure credentials for.
        credentials_payload (dict[str, Any]): Dictionary representation of corresponding cloud provider's credential schema.

    Returns:
    -------
        bool: True if cloud credentials successfully store. False otherwise.

    """
    base_route = get_api_base_route(version=1)

    if not credentials_payload:
        logger.error("Failed to add cloud credentials. Payload empty!")
        return False

    # Verify we are logged in
    logged_in = await is_logged_in(auth_client)
    if not logged_in:
        logger.error(
            "Failed to add cloud credentials. Provided client is not logged in!"
        )
        return False

    # Submit credentials
    provider_url = provider.value.lower()
    response = await auth_client.post(
        f"{base_route}/users/me/secrets/{provider_url}", json=credentials_payload
    )
    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "Failed to add cloud credentials. Error: %s", response.json()["detail"]
        )
        return False

    return True


async def add_blueprint_range(
    auth_client: AsyncClient, blueprint_range: dict[str, Any]
) -> BlueprintRangeHeaderSchema | None:
    """Add a range blueprint to the application.

    Args:
    ----
        auth_client (AsyncClient): Any authenticated httpx client. NOT THE `auth_client` FIXTURE!
        blueprint_range (dict[str, Any]): Dictionary representation of a BlueprintRangeCreateSchema.

    Returns:
    -------
        BlueprintRangeHeaderSchema: Header info of saved blueprint range.

    """
    base_route = get_api_base_route(version=1)

    if not blueprint_range:
        logger.error("Failed to add range blueprint! Blueprint empty!")
        return None

    # Verify we are logged in
    logged_in = await is_logged_in(auth_client)
    if not logged_in:
        logger.error("Failed to add range blueprint. Provided client is not logged in!")
        return None

    # Submit blueprint range
    response = await auth_client.post(
        f"{base_route}/blueprints/ranges", json=blueprint_range
    )
    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "Failed to add range blueprint. Error: %s", response.json()["detail"]
        )
        return None

    return BlueprintRangeHeaderSchema.model_validate(response.json())


async def deploy_range(
    auth_client: AsyncClient,
    blueprint_id: int,
    base_name: str = "Test Range",
    description: str = "Test range. Auto generated for testing.",
    region: OpenLabsRegion = OpenLabsRegion.US_EAST_1,
) -> DeployedRangeHeaderSchema | None:
    """Deploy a range from an existing blueprint range.

    Args:
    ----
        auth_client (AsyncClient): Any authenticated httpx client. NOT THE `auth_client` FIXTURE!
        blueprint_id (int): ID of the blueprint range to deploy.
        base_name (str): String to include in the name. Extra information will be included to make it more identifiable.
        description (str): Description for deployed range.
        region (OpenLabsRegion): Cloud region to deploy range into.

    Returns:
    -------
        DeployedRangeHeaderSchema: Header info of the deployed range if successfully deployed. None otherwise.

    """
    base_route = get_api_base_route(version=1)

    # Verify we are logged in
    logged_in = await is_logged_in(auth_client)
    if not logged_in:
        logger.error("Failed to deploy range. Provided client is not authenticated!")
        return None

    # Fetch blueprint to aid in building descriptive name
    response = await auth_client.get(f"{base_route}/blueprints/ranges/{blueprint_id}")
    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "Failed to deploy range. Could not fetch range blueprint! Error: %s",
            response.json()["detail"],
        )
        return None
    blueprint_range = response.json()

    # Deploy range
    deploy_payload = {
        "name": f"Test-({base_name})-{blueprint_range["provider"]}-Range-from-({blueprint_range["name"]} ({blueprint_range["id"]}))",
        "description": f"{description} This range was auto generated by testing utility functions.",
        "blueprint_id": blueprint_id,
        "region": region.value,
    }
    response = await auth_client.post(
        f"{base_route}/ranges/deploy",
        json=deploy_payload,
        timeout=None,  # TODO: remove when ARQ jobs implemented
    )
    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "Failed to deploy range due to error while deploying. Ensure that all resources were successfully cleaned up! Error: %s",
            response.json()["detail"],
        )
        return None

    return DeployedRangeHeaderSchema.model_validate(response.json())


async def destroy_range(auth_client: AsyncClient, range_id: int) -> bool:
    """Deploy a range from an existing blueprint range.

    Args:
    ----
        auth_client (AsyncClient): Any authenticated httpx client. NOT THE `auth_client` FIXTURE!
        range_id (int): ID of the deployed range.

    Returns:
    -------
        bool: True if range successfully destroyed. False otherwise.

    """
    base_route = get_api_base_route(version=1)

    # Verify we are logged in
    logged_in = await is_logged_in(auth_client)
    if not logged_in:
        logger.error("Failed to destroy range. Provided client is not authenticated!")
        return False

    # Destroy range
    response = await auth_client.delete(
        f"{base_route}/ranges/{range_id}",
        timeout=None,  # TODO: remove when ARQ jobs implemented
    )
    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "Failed to destroy range ID: %s. Error: %s",
            range_id,
            response.json()["detail"],
        )
        return False

    return True


async def get_range(
    auth_client: AsyncClient, range_id: int
) -> DeployedRangeSchema | None:
    """Get a deployed range's information.

    Args:
    ----
        auth_client (AsyncClient): Any authenticated httpx client. NOT THE `auth_client` FIXTURE!
        range_id (int): ID of the deployed range.

    Returns:
    -------
        DeployedRangeSchema: The deployed range information if found. None otherwise.

    """
    base_route = get_api_base_route(version=1)

    # Verify we are logged in
    logged_in = await is_logged_in(auth_client)
    if not logged_in:
        logger.error(
            "Failed to get deployed range. Provided client is not authenticated!"
        )
        return None

    # Get range
    response = await auth_client.get(f"{base_route}/ranges/{range_id}")
    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "Failed to get deployed range. Error: %s", response.json()["detail"]
        )
        return None

    return DeployedRangeSchema.model_validate(response.json())


async def get_range_key(auth_client: AsyncClient, range_id: int) -> str | None:
    """Get a deployed range's jumpbox key.

    Args:
    ----
        auth_client (AsyncClient): Any authenticated httpx client. NOT THE `auth_client` FIXTURE!
        range_id (int): ID of the deployed range.

    Returns:
    -------
        str: The range's private key.

    """
    # Verify we are logged in
    logged_in = await is_logged_in(auth_client)
    if not logged_in:
        logger.error("Failed to destroy range. Provided client is not authenticated!")
        return None

    base_route = get_api_base_route(version=1)

    # Get range key
    response = await auth_client.get(f"{base_route}/ranges/{range_id}/key")
    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "Failed to get deployed range key. Error: %s", response.json()["detail"]
        )
        return None

    key_response = DeployedRangeKeySchema.model_validate(response.json())
    unformatted_key = key_response.range_private_key

    # Format key
    return unformatted_key.replace("\\n", "\n")
