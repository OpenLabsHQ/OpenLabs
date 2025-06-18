import asyncio
import copy
import logging
import os
import shutil
import socket
import sys
import uuid
from contextlib import AsyncExitStack
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Generator

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
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
    BlueprintRangeSchema,
    DeployedRangeHeaderSchema,
    DeployedRangeSchema,
)
from src.app.schemas.secret_schema import SecretSchema
from src.app.utils.api_utils import get_api_base_route
from src.app.utils.cdktf_utils import create_cdktf_dir
from tests.api_test_utils import (
    authenticate_client,
    wait_for_fastapi_service,
)
from tests.deploy_test_utils import (
    deploy_managed_range,
    destroy_managed_range,
    get_provider_test_creds,
    isolated_integration_client,
)
from tests.test_utils import (
    add_key_recursively,
    generate_random_int,
    rotate_docker_compose_test_log_files,
)
from tests.unit.api.v1.config import (
    valid_blueprint_range_create_payload,
    valid_blueprint_range_multi_create_payload,
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
async def docker_compose_api_url(
    docker_services: DockerCompose, get_free_port: int
) -> str:
    """Spin up the Docker environment, waits for the API to be live, and returns the base URL of the running service."""
    base_url = f"http://127.127.127.127:{get_free_port}"
    await wait_for_fastapi_service(
        f"{base_url}{get_api_base_route(version=1)}", timeout=60
    )
    return base_url


@pytest_asyncio.fixture(scope="session")
async def integration_client(
    docker_compose_api_url: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Create a shared async client that connects to live FastAPI docker compose container."""
    async with AsyncClient(base_url=docker_compose_api_url) as client:
        yield client


@pytest_asyncio.fixture(scope="session")
async def auth_integration_client(
    docker_compose_api_url: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Create a shared authenticated async client to live FastAPI docker compose container."""
    async with AsyncClient(base_url=docker_compose_api_url) as client:
        assert await authenticate_client(client), "Failed to authenticate test client"
        yield client


@pytest.fixture(scope="session")
def load_test_env_file() -> bool:
    """Load .env.tests file.

    Returns
    -------
        bool: If at least one environment variable was set. False otherwise.

    """
    test_env_file = ".env.tests"
    logger.info("Attempting to load test ENV file: %s", test_env_file)
    return load_dotenv(test_env_file)


@pytest_asyncio.fixture(scope="session")
async def parallel_deployed_ranges_for_provider(
    request: pytest.FixtureRequest,
    docker_compose_api_url: str,
    load_test_env_file: bool,
) -> AsyncGenerator[dict[str, tuple[DeployedRangeSchema, str, str]], None]:
    """Deploys AND destroys all ranges for a provider in PARALLEL."""
    provider: OpenLabsProvider = request.param
    logger.info(
        "Starting parallel deployment of ranges for provider: %s...",
        provider.value.upper(),
    )

    destroy_details = []
    async with AsyncExitStack() as client_stack:
        try:
            blueprint_map = {
                "one_all": valid_blueprint_range_create_payload,
                "multi": valid_blueprint_range_multi_create_payload,
            }

            async def create_and_setup(
                key: str, blueprint_dict: dict[str, Any]
            ) -> dict[str, Any]:
                """Create a client and run the setup task."""
                client = await client_stack.enter_async_context(
                    isolated_integration_client(docker_compose_api_url)
                )
                creds = get_provider_test_creds(provider)
                if not creds:
                    pytest.skip(f"Credentials for {provider.value.upper()} not set.")

                setup_info = await deploy_managed_range(
                    client=client,
                    provider=provider,
                    cloud_credentials_payload=creds,
                    blueprint_range=BlueprintRangeCreateSchema.model_validate(
                        copy.deepcopy(blueprint_dict)
                    ),
                )
                # Add the live client to the info needed for teardown
                setup_info["client"] = client
                return setup_info

            # Deploy ranges
            deploy_tasks = {
                key: create_and_setup(key, blueprint_dict)
                for key, blueprint_dict in blueprint_map.items()
            }
            results = await asyncio.gather(
                *deploy_tasks.values(), return_exceptions=True
            )

            # Check for deploy errors
            deployed_data_for_yield: dict[str, tuple[DeployedRangeSchema, str, str]] = (
                {}
            )
            has_errors = False
            for key, result in zip(deploy_tasks.keys(), results, strict=True):
                if isinstance(result, BaseException):
                    logger.critical(
                        "Deploy failed for '%s': %s", key, result, exc_info=result
                    )
                    has_errors = True
                else:
                    logger.info(
                        "Successfully deployed '%s' range for '%s'.",
                        key,
                        provider.value.upper(),
                    )
                    # Prepare the data for the test (the tuple)
                    deployed_data_for_yield[key] = (
                        result["deployed_range"],
                        result["email"],
                        result["password"],
                    )
                    # Store the full dictionary for destroying
                    destroy_details.append(result)

            if has_errors:
                pytest.fail(
                    f"One or more ranges failed to deploy for provider {provider.value.upper()}."
                )

            yield deployed_data_for_yield

        finally:
            if destroy_details:
                logger.info(
                    "Starting parallel destroy of all test ranges for provider: %s...",
                    provider.value.upper(),
                )
                destroy_tasks = [
                    destroy_managed_range(
                        client=info["client"],
                        email=info["email"],
                        password=info["password"],
                        range_id=info["range_id"],
                        provider=provider,
                    )
                    for info in destroy_details
                ]
                destroy_results = await asyncio.gather(
                    *destroy_tasks, return_exceptions=True
                )

                for result in destroy_results:
                    if isinstance(result, BaseException):
                        # Log any errors during teardown but don't fail the test run
                        logger.error(
                            "Error during parallel destroy: %s",
                            result,
                            exc_info=result,
                        )


@pytest_asyncio.fixture(scope="session")
async def one_all_deployed_range(
    parallel_deployed_ranges_for_provider: dict[
        str, tuple[DeployedRangeSchema, str, str]
    ],
) -> tuple[DeployedRangeSchema, str, str]:
    """Get the deployed 'one-all' range for the currently tested provider."""
    return parallel_deployed_ranges_for_provider["one_all"]


@pytest_asyncio.fixture(scope="session")
async def multi_deployed_range(
    parallel_deployed_ranges_for_provider: dict[
        str, tuple[DeployedRangeSchema, str, str]
    ],
) -> tuple[DeployedRangeSchema, str, str]:
    """Get the deployed 'multi-vpc' range for the currently tested provider."""
    return parallel_deployed_ranges_for_provider["multi"]


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
