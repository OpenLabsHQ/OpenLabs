import asyncio
import copy
import logging
import os
import random
import shutil
import socket
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Generator

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.compose import DockerCompose
from testcontainers.postgres import PostgresContainer

from src.app.core.cdktf.ranges.base_range import AbstractBaseRange
from src.app.core.cdktf.ranges.range_factory import RangeFactory
from src.app.core.cdktf.stacks.base_stack import AbstractBaseStack
from src.app.core.config import settings
from src.app.core.db.database import Base, async_get_db
from src.app.enums.providers import OpenLabsProvider
from src.app.enums.regions import OpenLabsRegion
from src.app.models.user_model import UserModel
from src.app.schemas.range_schemas import (
    BlueprintRangeCreateSchema,
    BlueprintRangeHeaderSchema,
    BlueprintRangeSchema,
    DeployedRangeHeaderSchema,
    DeployedRangeSchema,
)
from src.app.schemas.secret_schema import SecretSchema
from src.app.utils.api_utils import get_api_base_route
from src.app.utils.cdktf_utils import create_cdktf_dir
from tests.unit.api.v1.config import (
    BASE_ROUTE,
    base_user_login_payload,
    base_user_register_payload,
    valid_blueprint_range_create_payload,
    valid_deployed_range_data,
    valid_deployed_range_header_data,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@pytest.fixture(autouse=True)
def create_test_cdktf_dir(request: pytest.FixtureRequest) -> None:
    """Override settings CDKTF dir for testing."""
    settings.CDKTF_DIR = create_cdktf_dir()

    # Register a finalizer to remove the directory after the test module finishes
    request.addfinalizer(lambda: shutil.rmtree(settings.CDKTF_DIR, ignore_errors=True))


@pytest.fixture(scope="session")
def postgres_container() -> Generator[str, None, None]:
    """Get connection string to Postgres container.

    Returns
    -------
        Generator[str, None, None]: Async connection string to postgres database.

    """
    logger.info("Starting Postgres test container...")
    with PostgresContainer("postgres:17") as container:
        container.start()

        raw_url = container.get_connection_url()
        async_url = raw_url.replace("psycopg2", "asyncpg")

        container_up_msg = f"Test container up => {async_url}"
        logger.info(container_up_msg)

        yield async_url

    logger.info("Postgres test container stopped.")


@pytest.fixture(scope="session", autouse=True)
def create_db_schema(postgres_container: str) -> None:
    """Create database schema synchronously (using psycopg2 driver).

    Args:
    ----
        postgres_container (str): Postgres container connection string.

    Returns:
    -------
        None

    """
    sync_url = postgres_container.replace("asyncpg", "psycopg2")

    create_schema_msg = f"Creating schema with sync engine => {sync_url}"
    logger.info(create_schema_msg)

    sync_engine = create_engine(sync_url, echo=False, future=True)

    try:
        Base.metadata.create_all(sync_engine)
        logger.info("All tables created (sync).")
    except SQLAlchemyError as err:
        logger.exception("Error creating tables.")
        raise err
    finally:
        sync_engine.dispose()
        logger.info("Sync engine disposed after schema creation.")


@pytest.fixture(scope="module")
def synthesize_factory() -> (
    Callable[[type[AbstractBaseStack], BlueprintRangeSchema, str, OpenLabsRegion], str]
):
    """Get factory to generate CDKTF synthesis for different stack classes."""
    from cdktf import Testing

    def _synthesize(
        stack_cls: type[AbstractBaseStack],
        cyber_range: BlueprintRangeSchema,
        stack_name: str = "test_range",
        region: OpenLabsRegion = OpenLabsRegion.US_EAST_1,
    ) -> str:
        """Synthesize generic stack using CDKTF testing library."""
        app = Testing.app()

        # Synthesize the stack using the provided stack class
        return str(
            Testing.synth(
                stack_cls(
                    app,
                    cyber_range,
                    stack_name,
                    settings.CDKTF_DIR,
                    region,
                    "test-range",
                )
            )
        )

    return _synthesize


@pytest.fixture(scope="module")
def range_factory() -> Callable[
    [type[AbstractBaseRange], BlueprintRangeSchema, OpenLabsRegion],
    AbstractBaseRange,
]:
    """Get factory to generate range object sythesis output."""

    def _range_synthesize(
        range_cls: type[AbstractBaseRange],
        range_blueprint: BlueprintRangeSchema,
        region: OpenLabsRegion = OpenLabsRegion.US_EAST_1,
        state_file: None = None,
    ) -> AbstractBaseRange:
        """Create range object and return synth() output."""
        secrets = SecretSchema()

        return RangeFactory.create_range(
            name="test-range",
            description="Range for testing purposes!",
            range_obj=range_blueprint,
            region=region,
            secrets=secrets,
            state_file=state_file,
        )

    return _range_synthesize


@pytest_asyncio.fixture(scope="session")
async def async_engine(postgres_container: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async database engine.

    Args:
    ----
        postgres_container (str): Postgres container connection string.

    Returns:
    -------
        AsyncGenerator[AsyncEngine, None]: Async database engine.

    """
    engine = create_async_engine(
        postgres_container, echo=False, future=True, poolclass=NullPool
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def db_override(
    async_engine: AsyncEngine,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """Fixture to override database dependency in test FastAPI app."""
    # Create a session factory using the captured engine.
    async_session_factory_for_override = async_sessionmaker(
        bind=async_engine, expire_on_commit=False, class_=AsyncSession
    )

    async def override_async_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_factory_for_override() as session:
            try:
                yield session
                await session.commit()
                logger.debug(
                    "Test DB transaction committed successfully by override_async_get_db."
                )
            except Exception as e:
                logger.debug(
                    "Exception during test DB session or commit in override_async_get_db. Rolling back. Error: %s",
                    e,
                )
                await session.rollback()
                raise

    return override_async_get_db


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


@pytest.fixture(scope="session")
def client_app(
    db_override: Callable[[], AsyncGenerator[AsyncSession, None]],
) -> FastAPI:
    """Create app for client fixture."""
    from src.app.main import app

    app.dependency_overrides[async_get_db] = db_override

    return app


@pytest.fixture(scope="session")
def auth_client_app(
    db_override: Callable[[], AsyncGenerator[AsyncSession, None]],
) -> FastAPI:
    """Create app for auth_client fixture."""
    from src.app.main import app

    app.dependency_overrides[async_get_db] = db_override

    return app


@pytest_asyncio.fixture(scope="session")
async def client(
    client_app: FastAPI,
) -> AsyncGenerator[AsyncClient, None]:
    """Get async client fixture connected to the FastAPI app and test database container.

    **Note:** This client is created once per test session and is shared across all tests that
    use the `client` fixture. This means that if any test authenticates before your test, the
    client will act as an authenticated client.

    To ensure you have an unauthenticated client logout first:
        ```python
        async def my_unauthenticated_test(client: AsyncClient) -> None:
            assert await logout_user(client)
        ```
    """
    transport = ASGITransport(app=client_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clean up overrides after the test finishes
    client_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session")
async def auth_client(
    auth_client_app: FastAPI,
) -> AsyncGenerator[AsyncClient, None]:
    """Get authenticated async client fixture conntected to the FastAPI app and test database container.

    **Note:** This client is created once per test session and is shared accross all tests that use the
    `auth_client` fixture. If you need a more isolated environment for testing, use the `client` fixture
    and authenticate manually in the test using `authenticate_client`.

    Example:
        ```python
        async def my_auth_test(client: AsyncClient) -> None:
            assert await authenticate_client(client)

            client.post("/some/authenticated/endpoint")
        ```

    """
    transport = ASGITransport(app=auth_client_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert await authenticate_client(client), "Failed to authenticate test client"
        yield client

    # Clean up overrides after the test finishes
    auth_client_app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def get_free_port() -> int:
    """Get an unused port on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def create_test_output_dir() -> str:
    """Create test output directory `.testing-out`.

    Returns
    -------
        str: Path to test output dir.

    """
    test_output_dir = "./.testing-out/"
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)

    return test_output_dir


def rotate_docker_compose_test_log_files(test_output_dir: str) -> None:
    """Rotate and cleanup docker_compose_test_*.log files."""
    logs_to_keep = 5
    log_prefix = "docker_compose_test_"
    logger.info(
        "--- Log Cleanup ---\nRunning log rotation. Keeping the newest %d log(s).",
        logs_to_keep,
    )

    try:
        log_dir = Path(test_output_dir)
        log_files = sorted(
            log_dir.glob(f"{log_prefix}*.log"), reverse=True
        )  # Logs named with YYYY-MM-DD_HH-MM-SS format

        files_to_delete = log_files[logs_to_keep:]

        if not files_to_delete:
            logger.info("No old logs to delete.")
            return

        logger.info("Found %d old log(s) to delete.", len(files_to_delete))
        for log_file in files_to_delete:
            try:
                log_file.unlink()
                logger.debug("Deleted old log file: %s", log_file)
            except OSError as e:
                logger.error("Error deleting file %s: %s", log_file, e)

    except Exception as e:
        logger.error("An unexpected error occurred during log cleanup: %s", e)


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


@pytest.fixture(scope="session")
def docker_services(
    get_free_port: int,
    create_test_output_dir: str,
) -> Generator[DockerCompose, None, None]:
    """Spin up docker compose environment using `docker-compose.yml` in project root."""
    ip_var_name = "API_IP_ADDR"
    port_var_name = "API_PORT"

    # Export test config
    os.environ[ip_var_name] = "127.127.127.127"
    os.environ[port_var_name] = str(get_free_port)

    compose_files = ["docker-compose.yml", "docker-compose.test.yml"]

    with DockerCompose(
        context=".",
        compose_file_name=compose_files,
        pull=True,
        build=True,
        wait=False,
        keep_volumes=False,
    ) as compose:
        logger.info("Docker Compose environment started.")
        try:
            yield compose
        finally:
            logger.info("Saving container logs...")

            # Check if the test run failed by seeing if an exception was raised
            exc_type, _, _ = sys.exc_info()
            did_fail = exc_type is not None

            status = "FAILED" if did_fail else "PASSED"
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
            log_filename = f"docker_compose_test_{status}_{timestamp}.log"
            log_path = os.path.join(create_test_output_dir, log_filename)

            stdout, stderr = compose.get_logs()

            # Save the logs to a file
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("--- STDOUT ---\n")
                f.write(stdout)
                f.write("\n--- STDERR ---\n")
                f.write(stderr)

            logger.info("Container logs saved to: %s", log_path)

            # Rotate and clear old logs
            rotate_docker_compose_test_log_files(create_test_output_dir)

    del os.environ[ip_var_name]
    del os.environ[port_var_name]
    logger.info("Docker Compose environment stopped.")


@pytest_asyncio.fixture(scope="session")
async def integration_client(
    docker_services: DockerCompose,
    get_free_port: int,
) -> AsyncGenerator[AsyncClient, None]:
    """Create async client that connects to live FastAPI docker compose container."""
    base_url = f"http://127.127.127.127:{get_free_port}"

    # Wait for docker compose and container to start
    await wait_for_fastapi_service(
        f"{base_url}{get_api_base_route(version=1)}", timeout=60
    )

    async with AsyncClient(base_url=base_url) as client:
        yield client


@pytest_asyncio.fixture(scope="session")
async def auth_integration_client(
    docker_services: DockerCompose,
    get_free_port: int,
) -> AsyncGenerator[AsyncClient, None]:
    """Create authenticated async client to live FastAPI docker compose container."""
    base_url = f"http://127.127.127.127:{get_free_port}"

    # Wait for docker compose and container to start
    await wait_for_fastapi_service(
        f"{base_url}{get_api_base_route(version=1)}", timeout=60
    )

    async with AsyncClient(base_url=base_url) as client:
        assert await authenticate_client(client), "Failed to authenticate test client"
        yield client


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
    response = await auth_client.get(f"{base_route}/users/me")
    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "Failed to add cloud credentials. Provided client is not authenticated!"
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
    response = await auth_client.get(f"{base_route}/users/me")
    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "Failed to add range blueprint. Provided client is not authenticated!"
        )
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
    response = await auth_client.get(f"{base_route}/users/me")
    if response.status_code != status.HTTP_200_OK:
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
    response = await auth_client.get(f"{base_route}/users/me")
    if response.status_code != status.HTTP_200_OK:
        logger.error("Failed to destroy range. Provided client is not authenticated!")
        return False

    # Destroy range
    response = await auth_client.delete(
        f"{base_route}/ranges/{range_id}",
        timeout=None,  # TODO: remove when ARQ jobs implemented
    )

    return response.status_code == status.HTTP_200_OK


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
    response = await auth_client.get(f"{base_route}/users/me")
    if response.status_code != status.HTTP_200_OK:
        logger.error("Failed to destroy range. Provided client is not authenticated!")
        return None

    # Get range
    response = await auth_client.get(f"{base_route}/ranges/{range_id}")
    if response.status_code != status.HTTP_200_OK:
        logger.error(
            "Failed to get deployed range. Error: %s", response.json()["detail"]
        )
        return None

    return DeployedRangeSchema.model_validate(response.json())


@pytest.fixture(scope="session")
def load_test_env_file() -> bool:
    """Load .env.tests file.

    Returns
    -------
        bool: If at least one environment variable was set. False otherwise.

    """
    return load_dotenv(".env.tests")


@asynccontextmanager
async def managed_deployed_range(
    integration_client: AsyncClient,
    provider: OpenLabsProvider,
    cloud_credentials_payload: dict[str, Any],
    blueprint_range: BlueprintRangeCreateSchema,
) -> AsyncGenerator[tuple[DeployedRangeSchema, str, str], None]:
    """Deploy a range for testing with automatic cleanup.

    Args:
    ----
        integration_client (AsyncClient): Any authenticated httpx client. Normally, the integration clients. NOT THE `integration_client` FIXTURE!
        provider (OpenLabsProvider): A supported OpenLabs cloud provider.
        cloud_credentials_payload (dict[str, Any]): Dictionary representation of corresponding cloud provider's credential schema.
        blueprint_range (BlueprintRangeCreateSchema): Blueprint range creation schema to save and deploy.

    Returns:
    -------
        DeployedRangeSchema: Deployed range info.
        str: Email of user that owns the deployed range.
        str: Password of user that owns the deployed range.

    """
    deployment_info: dict[str, Any] = {}
    try:
        # Create new user
        _, email, password, _ = await register_user(integration_client)
        await login_user(integration_client, email=email, password=password)

        # Configure blueprint to use requested provider
        blueprint_range.provider = provider
        blueprint_payload = blueprint_range.model_dump(mode="json")

        # Deploy the range
        await add_cloud_credentials(
            integration_client, provider, cloud_credentials_payload
        )
        blueprint_header = await add_blueprint_range(
            integration_client, blueprint_payload
        )
        if not blueprint_header:
            msg = f"Failed to create range blueprint: {blueprint_payload["name"]} for deployment as an {provider.value} range test fixture!"
            logger.error(msg)
            pytest.fail(msg)

        deployed_range_header = await deploy_range(
            integration_client, blueprint_header.id
        )
        if not deployed_range_header:
            msg = f"Failed to deploy range blueprint: {blueprint_payload["name"]} to provider: {provider.value} as a test fixture!"
            logger.error(msg)
            pytest.fail(msg)

        deployed_range = await get_range(integration_client, deployed_range_header.id)
        if not deployed_range:
            msg = (
                f"Failed to get deployed info for range: {deployed_range_header.name}!"
            )
            logger.error(msg)
            pytest.fail(msg)

        # Store details needed for cleanup
        deployment_info = {
            "range_id": deployed_range_header.id,
            "provider": provider,
            "email": email,
            "password": password,
        }

        yield deployed_range, email, password

    finally:
        # TEARDOWN
        if deployment_info:
            # Log back in to destroy the range
            await login_user(
                integration_client,
                email=deployment_info["email"],
                password=deployment_info["password"],
            )
            destroyed = await destroy_range(
                integration_client, deployment_info["range_id"]
            )
            if not destroyed:
                msg = f"Failed to destroy range {deployment_info['range_id']}! Dangling test resources left in: {provider.value.upper()}!"
                logger.critical(msg)
                pytest.fail(msg, pytrace=False)


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
async def deploy_test_range(
    integration_client: AsyncClient,
    provider: OpenLabsProvider,
    blueprint_payload: dict[str, Any],
) -> AsyncGenerator[tuple[DeployedRangeSchema, str, str], None]:
    """Core logic for deploying a range."""
    test_cloud_credentials = get_provider_test_creds(provider)
    if not test_cloud_credentials:
        pytest.skip(f"Credentials for {provider.value.upper()} are not set.")

    blueprint_range = BlueprintRangeCreateSchema.model_validate(blueprint_payload)

    # All the duplicated logic now lives here, in one place.
    async with managed_deployed_range(
        integration_client=integration_client,
        provider=provider,
        cloud_credentials_payload=test_cloud_credentials,
        blueprint_range=blueprint_range,
    ) as deployed_range_data:
        yield deployed_range_data


@pytest_asyncio.fixture(scope="session")
async def one_all_deployed_range(
    request: pytest.FixtureRequest,
    integration_client: AsyncClient,
    load_test_env_file: bool,
) -> AsyncGenerator[tuple[DeployedRangeSchema, str, str], None]:
    """Deploys a 'one-all' range to a specific cloud provider.

    The provider is determined by the indirect parameter from the test
    (e.g., "aws", "gcp") via `request.param`.

    Returns
    -------
        DeployedRangeSchema: Deployed range info.
        str: Email of user that owns the deployed range.
        str: Password of user that owns the deployed range.

    """
    provider: OpenLabsProvider = request.param
    async with deploy_test_range(
        integration_client=integration_client,
        provider=provider,
        blueprint_payload=copy.deepcopy(valid_blueprint_range_create_payload),
    ) as (range_info, email, password):
        yield range_info, email, password


@pytest.fixture
def api_client(request: pytest.FixtureRequest) -> AsyncClient:
    """Return the corresponding client fixture.

    Only used for unauthenticated client fixtures.

    """
    return request.getfixturevalue(request.param)


@pytest.fixture
def auth_api_client(request: pytest.FixtureRequest) -> AsyncClient:
    """Return the corresponding client fixture.

    Only use for authenticated client fixtures.

    """
    return request.getfixturevalue(request.param)


@pytest.fixture
def mock_decrypt_no_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass secrets decryption to return a fake secrets record for the user."""

    async def mock_get_decrypted_secrets(
        user: UserModel, db: AsyncSession, master_key: bytes
    ) -> SecretSchema:
        return SecretSchema(
            aws_access_key=None,
            aws_secret_key=None,
            aws_created_at=None,
            azure_client_id=None,
            azure_client_secret=None,
            azure_tenant_id=None,
            azure_subscription_id=None,
            azure_created_at=None,
        )

    # Patch the function
    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_decrypted_secrets", mock_get_decrypted_secrets
    )


@pytest.fixture
def mock_decrypt_example_valid_aws_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass secrets decryption to return a fake secrets record for the user."""

    async def mock_get_decrypted_secrets(
        user: UserModel, db: AsyncSession, master_key: bytes
    ) -> SecretSchema:
        return SecretSchema(
            aws_access_key="AKIAIOSFODNN7EXAMPLE",
            aws_secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # noqa: S106
            aws_created_at=datetime.now(tz=timezone.utc),
            azure_client_id=None,
            azure_client_secret=None,
            azure_tenant_id=None,
            azure_subscription_id=None,
            azure_created_at=None,
        )

    # Patch the function
    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_decrypted_secrets", mock_get_decrypted_secrets
    )


@pytest.fixture
async def mock_synthesize_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the synthesize function call to return false to trigger specific error."""
    blueprint_schema_json = copy.deepcopy(valid_blueprint_range_create_payload)
    add_key_recursively(blueprint_schema_json, "id", generate_random_int)
    blueprint_schema = BlueprintRangeSchema.model_validate(
        blueprint_schema_json, from_attributes=True
    )
    monkeypatch.setattr(
        RangeFactory,
        "create_range",
        lambda *args, **kwargs: type(
            "MockRange",
            (AbstractBaseRange,),
            {
                "get_provider_stack_class": lambda self: None,
                "has_secrets": lambda self: True,
                "get_cred_env_vars": lambda self: {},
                "synthesize": lambda self: False,
            },
        )(
            "test-range",
            blueprint_schema,
            OpenLabsRegion.US_EAST_1,
            SecretSchema(),
            "Test range description.",
            None,  # No state file
        ),
    )


@pytest.fixture
async def mock_deploy_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the deploy function call to return false to trigger specific error."""
    blueprint_schema_json = copy.deepcopy(valid_blueprint_range_create_payload)
    add_key_recursively(blueprint_schema_json, "id", generate_random_int)
    blueprint_schema = BlueprintRangeSchema.model_validate(
        blueprint_schema_json, from_attributes=True
    )
    monkeypatch.setattr(
        RangeFactory,
        "create_range",
        lambda *args, **kwargs: type(
            "MockRange",
            (AbstractBaseRange,),
            {
                "get_provider_stack_class": lambda self: None,
                "has_secrets": lambda self: True,
                "get_cred_env_vars": lambda self: {},
                "synthesize": lambda self: True,
                "deploy": lambda self: False,
            },
        )(
            "test-range",
            blueprint_schema,
            OpenLabsRegion.US_EAST_1,
            SecretSchema(),
            "Test range description",
            None,  # No state file
        ),
    )


@pytest.fixture
async def mock_deploy_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the deploy function call to return true."""
    blueprint_schema_json = copy.deepcopy(valid_blueprint_range_create_payload)
    add_key_recursively(blueprint_schema_json, "id", generate_random_int)
    blueprint_schema = BlueprintRangeSchema.model_validate(
        blueprint_schema_json, from_attributes=True
    )
    monkeypatch.setattr(
        RangeFactory,
        "create_range",
        lambda *args, **kwargs: type(
            "MockRange",
            (AbstractBaseRange,),
            {
                "get_provider_stack_class": lambda self: None,
                "has_secrets": lambda self: True,
                "get_cred_env_vars": lambda self: {},
                "synthesize": lambda self: True,
                "deploy": lambda self: True,
            },
        )(
            "test-range",
            blueprint_schema,
            OpenLabsRegion.US_EAST_1,
            SecretSchema(),
            "Test range description.",
            None,  # No state file
        ),
    )


@pytest.fixture
def mock_is_range_owner_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the is_range_owner function to return false."""

    async def mock_is_range_owner(
        db: AsyncSession, range_id: int, user_id: uuid.UUID
    ) -> bool:
        return False

    monkeypatch.setattr("src.app.api.v1.ranges.is_range_owner", mock_is_range_owner)


@pytest.fixture
def mock_is_range_owner_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the is_range_owner function to return false."""

    async def mock_is_range_owner(
        db: AsyncSession, range_id: int, user_id: int
    ) -> bool:
        return True

    monkeypatch.setattr("src.app.api.v1.ranges.is_range_owner", mock_is_range_owner)


@pytest.fixture
def mock_create_range_in_db_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the create_deployed_range crud function to return nothing to force the error when adding to the ranges table."""

    async def mock_create_range_in_db_failure(*args: dict, **kwargs: dict) -> None:
        return None

    monkeypatch.setattr(
        "src.app.api.v1.ranges.create_deployed_range", mock_create_range_in_db_failure
    )


@pytest.fixture
def mock_create_range_in_db_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the create_deployed_range crud function to return fake range to simulate success."""

    async def mock_create_range_in_db_success(
        *args: dict, **kwargs: dict
    ) -> DeployedRangeHeaderSchema:
        return DeployedRangeHeaderSchema.model_validate(
            valid_deployed_range_header_data, from_attributes=True
        )

    monkeypatch.setattr(
        "src.app.api.v1.ranges.create_deployed_range", mock_create_range_in_db_success
    )


@pytest.fixture
def mock_delete_range_in_db_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the delete_range function to return nothing to force the error when deleteing from the ranges table."""

    async def mock_delete_range(*args: dict, **kwargs: dict) -> None:
        return None

    monkeypatch.setattr(
        "src.app.api.v1.ranges.delete_deployed_range", mock_delete_range
    )


@pytest.fixture
def mock_delete_range_in_db_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the delete_deployed_range crud function to return mock header data to simulate a successful delete."""

    async def mock_delete_range_in_db_success(
        *args: dict, **kwargs: dict
    ) -> DeployedRangeHeaderSchema:
        return DeployedRangeHeaderSchema.model_validate(
            valid_deployed_range_header_data, from_attributes=True
        )

    monkeypatch.setattr(
        "src.app.api.v1.ranges.delete_deployed_range", mock_delete_range_in_db_success
    )


@pytest.fixture
def mock_retrieve_deployed_range_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate successfully retrieving a deployed range from the database."""

    async def mock_get_range_success(
        *args: dict, **kwargs: dict
    ) -> DeployedRangeSchema:
        return DeployedRangeSchema.model_validate(
            valid_deployed_range_data, from_attributes=True
        )

    monkeypatch.setattr(
        "src.app.api.v1.ranges.get_deployed_range", mock_get_range_success
    )


def remove_key_recursively(
    data_structure: dict[Any, Any] | list[Any], key_to_remove: str
) -> None:
    """Recursively removes all instances of a specific key from a nested data structure (dictionaries and lists of dictionaries).

    The function modifies the 'data_structure' in-place.

    Args:
    ----
        data_structure: The dictionary or list to process. This could be
                        your main nested dictionary.
        key_to_remove: The string key to search for and remove from
                       any dictionaries found within the structure.

    Returns:
    -------
        None

    """
    if isinstance(data_structure, dict):
        for key in list(data_structure.keys()):
            if key == key_to_remove:
                del data_structure[key]
            else:
                remove_key_recursively(data_structure[key], key_to_remove)
    elif isinstance(data_structure, list):
        for item in data_structure:
            remove_key_recursively(item, key_to_remove)


def add_key_recursively(
    data_structure: dict[Any, Any] | list[Any],
    key_to_add: str,
    value_generator: Callable[[], Any],
) -> None:
    """Recursively adds a specific key with a generated value to all dictionaries within a nested data structure (dictionaries and lists of dictionaries).

    The function modifies the 'data_structure' in-place.

    Args:
    ----
        data_structure: The dictionary or list to process.
        key_to_add: The string key to add to any dictionaries found within the structure.
        value_generator: A function that will be called to generate the value for the new key each time it's added.

    Returns:
    -------
        None

    """
    if isinstance(data_structure, dict):
        data_structure[key_to_add] = value_generator()
        for key in data_structure:
            # Avoid adding the key to the value we just added if it's also a dict
            if key != key_to_add or not isinstance(data_structure[key], dict):
                add_key_recursively(data_structure[key], key_to_add, value_generator)
    elif isinstance(data_structure, list):
        for item in data_structure:
            add_key_recursively(item, key_to_add, value_generator)


def generate_random_int(lower_bound: int = 1, upper_bound: int = 100) -> int:
    """Generate random ints `lower_bound` <= int <= `upper_bound`.

    Args:
    ----
        lower_bound (int): Lower bound of random ints generated.
        upper_bound (int): Upper bound of random ints generated.

    Returns:
    -------
        int: Randomly generated `lower_bound` <= int <= `upper_bound`.

    """
    return random.randint(lower_bound, upper_bound)  # noqa: S311
