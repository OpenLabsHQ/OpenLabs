import logging
import os
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Generator, Iterator
from unittest.mock import AsyncMock, MagicMock

import dotenv
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture
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

from src.app.core.config import settings
from src.app.core.db.database import Base, async_get_db
from src.app.enums.job_status import OpenLabsJobStatus
from src.app.enums.providers import OpenLabsProvider
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.range_schemas import (
    BlueprintRangeCreateSchema,
    BlueprintRangeSchema,
    DeployedRangeCreateSchema,
    DeployedRangeSchema,
)
from src.app.schemas.secret_schema import SecretSchema
from src.app.utils.api_utils import get_api_base_route
from src.app.utils.cdktf_utils import create_cdktf_dir
from src.app.utils.path_utils import find_git_root
from tests.api_test_utils import (
    add_blueprint_range,
    add_cloud_credentials,
    authenticate_client,
    deploy_range,
    destroy_range,
    get_range,
    login_user,
    register_user,
    wait_for_fastapi_service,
    wait_for_jobs,
)
from tests.common.api.v1.config import (
    valid_blueprint_range_create_payload,
    valid_blueprint_range_multi_create_payload,
    valid_deployed_range_data,
)
from tests.deploy_test_utils import (
    RangeType,
    get_provider_test_creds,
    isolated_integration_client,
)
from tests.test_utils import rotate_docker_compose_test_log_files

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Config
COMPOSE_DIR = find_git_root()
API_PORT_VAR_NAME = "API_PORT"


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Dynamically mark all tests in the test suite."""
    rootdir = config.rootpath

    # Notes:
    # ------
    #   - `tests/common/` tests are automatically marked
    #       through their parameters, so there is no rule here.
    #
    #   - Provider specific tests are marked via parameters and
    #       on a file-by-file basis as there is no provider specific
    #       folder structure.

    for item in items:
        # Rule 1: All tests in tests/unit marked 'unit'
        if (rootdir / "tests" / "unit") in item.path.parents:
            item.add_marker("unit")

        # Rule 2: All tests in tests/integration marked 'integration'
        # These tests are slow because they build the entire docker compose
        if (rootdir / "tests" / "integration") in item.path.parents:
            item.add_marker("integration")
            item.add_marker("slow")

        # Rule 3: All tests under any folder named 'cdktf' marked accordingly
        # These tests are slow because of the loading time for providers
        if "cdktf" in item.path.parts:
            item.add_marker("cdktf")
            item.add_marker("slow")

        # Rule 4: All tests under an 'api' folder marked accordingly
        # These are slow because of docker container fixture setup and
        # import CDKTF dependencies through the range endpoints.
        if "api" in item.path.parts:
            item.add_marker("api")
            item.add_marker("slow")

        # Rule 5: All tests under the 'scripts' folder marked slow
        # These are slow because they have retry/wait periods
        if "scripts" in item.path.parts:
            item.add_marker("slow")

        # Rule 6: All tests under any the 'worker' folder marked accordingly
        # and slow because the worker imports CDKTF dependencies through
        # the range deploy/destroy functions.
        if "worker" in item.path.parts:
            item.add_marker("worker")
            item.add_marker("slow")

        # Rule 7: Mark tests in AWS-specific files.
        filename = item.path.name
        if "_aws_" in filename:
            item.add_marker("aws")


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
        raw_url = container.get_connection_url()
        async_url = raw_url.replace("psycopg2", "asyncpg")

        container_up_msg = f"Test container up => {async_url}"
        logger.info(container_up_msg)

        yield async_url

    logger.info("Postgres test container stopped.")


@pytest.fixture(scope="session")
def create_db_schema(postgres_container: str) -> Generator[str, None, None]:
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
        yield postgres_container
    except SQLAlchemyError as err:
        logger.exception("Error creating tables.")
        raise err
    finally:
        sync_engine.dispose()
        logger.info("Sync engine disposed after schema creation.")


@pytest.fixture(scope="module")
def synthesize_factory() -> (
    Callable[[type[Any], BlueprintRangeSchema, str, OpenLabsRegion], str]
):
    """Get factory to generate CDKTF synthesis for different stack classes."""
    # Import here to avoid CDKTF long loading phase
    from cdktf import Testing  # noqa: PLC0415

    from src.app.core.cdktf.stacks.base_stack import AbstractBaseStack  # noqa: PLC0415

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
    [Any, BlueprintRangeSchema, OpenLabsRegion],
    Any,
]:
    """Get factory to generate range object sythesis output."""
    from src.app.core.cdktf.ranges.base_range import AbstractBaseRange  # noqa: PLC0415
    from src.app.core.cdktf.ranges.range_factory import RangeFactory  # noqa: PLC0415

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


@pytest.fixture(scope="function")
def pulumi_range_factory() -> Callable[
    [Any, BlueprintRangeSchema, OpenLabsRegion],
    Any,
]:
    """Get factory to generate Pulumi range objects."""
    from src.app.core.pulumi.ranges.base_range import AbstractBasePulumiRange  # noqa: PLC0415
    from src.app.core.pulumi.ranges.range_factory import PulumiRangeFactory  # noqa: PLC0415

    def _pulumi_range_create(
        range_cls: type[AbstractBasePulumiRange],
        range_blueprint: BlueprintRangeSchema,
        region: OpenLabsRegion = OpenLabsRegion.US_EAST_1,
        state_data: None = None,
    ) -> AbstractBasePulumiRange:
        """Create Pulumi range object."""
        secrets = SecretSchema(
            aws_access_key="test_access_key",
            aws_secret_key="test_secret_key"
        )

        return PulumiRangeFactory.create_range(
            name="test-range",
            description="Range for testing purposes!",
            range_obj=range_blueprint,
            region=region,
            secrets=secrets,
            state_data=state_data,
        )

    return _pulumi_range_create


@pytest.fixture
def mock_pulumi_range_factory(
    mocker: MockerFixture,
) -> Iterator[Callable[..., MagicMock]]:
    """Provide a factory function to create and patch a customizable Pulumi range mock.

    This fixture patches `PulumiRangeFactory.create_range` to return a `MagicMock`
    that is configured based on the arguments passed to the factory function.

    Yields:
        Callable[..., MagicMock]: A function to create and patch the mock.

    """
    from src.app.core.pulumi.ranges.base_range import AbstractBasePulumiRange  # noqa: PLC0415
    from src.app.core.pulumi.ranges.range_factory import PulumiRangeFactory  # noqa: PLC0415

    def _create_and_patch(  # noqa: D417, PLR0913
        # Arguments for configuring the Pulumi mock
        has_secrets: bool = True,
        deploy: DeployedRangeCreateSchema | None = None,
        destroy: bool = True,
        get_config_values: dict[str, Any] | None = None,
        get_cred_env_vars: dict[str, Any] | None = None,
    ) -> MagicMock:
        """Patch PulumiRangeFactory.create_range and configures the mock's behavior.

        Args:
            has_secrets: Whether the mock should return True for has_secrets().
            deploy: The deployed range schema to return from deploy().
            destroy: Whether destroy() should return True.
            get_config_values: Config values to return from get_config_values().
            get_cred_env_vars: Environment variables to return from get_cred_env_vars().

        Returns:
            MagicMock: The configured mock object.

        """
        deployed_create_schema = DeployedRangeCreateSchema.model_validate(
            valid_deployed_range_data
        )

        if deploy is None:
            deploy = deployed_create_schema

        if get_config_values is None:
            get_config_values = {"aws:region": {"value": "us-east-1"}}

        if get_cred_env_vars is None:
            get_cred_env_vars = {
                "AWS_ACCESS_KEY_ID": "test_access_key",
                "AWS_SECRET_ACCESS_KEY": "test_secret_key",
            }

        # Create a mock that acts like AbstractBasePulumiRange
        mock_range = MagicMock()

        # Configure mock methods
        mock_range.has_secrets.return_value = has_secrets
        mock_range.deploy = AsyncMock(return_value=deploy)
        mock_range.destroy = AsyncMock(return_value=destroy)
        mock_range.get_config_values.return_value = get_config_values
        mock_range.get_cred_env_vars.return_value = get_cred_env_vars
        mock_range.is_deployed.return_value = False
        mock_range.get_state_data.return_value = None
        mock_range.cleanup_workspace = AsyncMock(return_value=True)

        # Patch the factory method
        mocker.patch.object(
            PulumiRangeFactory, "create_range", return_value=mock_range
        )

        return mock_range

    yield _create_and_patch


@pytest_asyncio.fixture(scope="session")
async def async_engine(create_db_schema: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async database engine.

    Args:
    ----
        create_db_schema (str): Postgres container connection string.

    Returns:
    -------
        AsyncGenerator[AsyncEngine, None]: Async database engine.

    """
    db_conn_str = create_db_schema
    engine = create_async_engine(
        db_conn_str, echo=False, future=True, poolclass=NullPool
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
def test_app(
    db_override: Callable[[], AsyncGenerator[AsyncSession, None]],
) -> Generator[FastAPI, None, None]:
    """Create a single app for all client fixtures with the DB override."""
    from src.app.main import app  # noqa: PLC0415

    app.dependency_overrides[async_get_db] = db_override
    yield app

    # Clean up overrides after the test session finishes
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session")
async def client(
    test_app: FastAPI,
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
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="session")
async def auth_client(
    test_app: FastAPI,
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
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert await authenticate_client(client), "Failed to authenticate test client"
        yield client


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
    test_output_dir = "./testing-out/"
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)

    return test_output_dir


@pytest.fixture(scope="session")
def test_env_file() -> Generator[Path, None, None]:
    """Create a test .env file."""
    env_path = Path(f"{COMPOSE_DIR}/.env")
    backup_path = env_path.with_suffix(env_path.suffix + ".bak")
    example_path = Path(f"{COMPOSE_DIR}/.env.example")

    if not example_path.is_file():
        pytest.fail(f"Required example .env file not found: {example_path}")

    # Back up the original .env if it exists
    original_env_existed = env_path.exists()
    if original_env_existed:
        env_path.rename(backup_path)
        logger.info("Backed up existing .env file to: %s.", backup_path)

    # Create the test .env from the example
    new_env_path = shutil.copy(example_path, env_path)

    try:
        yield Path(new_env_path)
    finally:
        if original_env_existed:
            backup_path.replace(env_path)
            logger.info("Restored .env file from backup.")
        else:
            # If no backup, cleanup our test .env
            env_path.unlink()
            logger.info("Removed temporary .env file.")


def configure_integration_test_app(test_env_file: Path, api_port: int) -> None:
    """Configure a .env file for integration testing.

    Args:
        test_env_file: Path to test .env file
        api_port: Free port that API will listen on

    Returns:
        None

    """
    if not test_env_file.is_file():
        pytest.fail("Failed to configure .env file for testing. Env file not found!")

    # Set env variables
    dotenv.set_key(test_env_file, API_PORT_VAR_NAME, str(api_port))


@pytest.fixture(scope="session")
def docker_services(
    get_free_port: int, create_test_output_dir: str, test_env_file: Path
) -> Generator[DockerCompose, None, None]:
    """Spin up docker compose environment using `docker-compose.yml` in project root."""
    configure_integration_test_app(test_env_file, api_port=get_free_port)

    compose_files = ["docker-compose.yml", "docker-compose.test.yml"]

    with DockerCompose(
        context=COMPOSE_DIR,
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

            timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
            log_filename = f"docker_compose_test_{timestamp}.log"
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

    logger.info("Docker Compose environment stopped.")


@pytest_asyncio.fixture(scope="session")
async def docker_compose_api_url(
    docker_services: DockerCompose, get_free_port: int
) -> str:
    """Spin up the Docker environment, waits for the API to be live, and returns the base URL of the running service."""
    base_url = f"http://127.0.0.1:{get_free_port}"
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
    test_env_file = find_git_root() / ".env.tests"
    logger.info("Attempting to load test ENV file: %s", test_env_file)
    return load_dotenv(str(test_env_file))


@pytest_asyncio.fixture(scope="session")
async def provider_deployed_ranges_for_provider(
    request: pytest.FixtureRequest,
    docker_compose_api_url: str,
    load_test_env_file: bool,
) -> AsyncGenerator[dict[RangeType, tuple[DeployedRangeSchema, str, str]], None]:
    """Deploys and destroys all ranges for a provider in parallel."""
    provider: OpenLabsProvider = request.param
    provider_upper = provider.value.upper()
    logger.info(
        "Starting parallel deployment of ranges for provider: %s...",
        provider_upper,
    )

    blueprint_map = {
        RangeType.ONE_ALL: valid_blueprint_range_create_payload,
        RangeType.MULTI: valid_blueprint_range_multi_create_payload,
    }
    deploy_job_ids: list[str] = []
    job_to_range_type: dict[str, RangeType] = {}
    destroy_data: dict[RangeType, int] = {}
    yield_data: dict[RangeType, tuple[DeployedRangeSchema, str, str]] = {}

    async with isolated_integration_client(docker_compose_api_url) as client:
        try:
            # Create new user for this provider's deployments
            _, email, password, _ = await register_user(client)
            await login_user(client, email=email, password=password)

            # Configure provider cloud credentials
            creds = get_provider_test_creds(provider)
            if not creds:
                pytest.skip(f"Credentials for {provider_upper} not set.")

            added_creds = await add_cloud_credentials(client, provider, creds)
            if not added_creds:
                pytest.fail(f"Failed configure cloud credentials for {provider_upper}")

            # Deploy ranges
            for range_type, blueprint_dict in blueprint_map.items():
                # Create and configure blueprint
                blueprint_range = BlueprintRangeCreateSchema.model_validate(
                    blueprint_dict
                )
                blueprint_range.provider = provider

                blueprint_payload = blueprint_range.model_dump(mode="json")
                blueprint_header = await add_blueprint_range(client, blueprint_payload)
                if not blueprint_header:
                    pytest.fail(
                        f"Failed to create range blueprint: {blueprint_range.name}"
                    )

                # Deploy range
                job_details = await deploy_range(client, blueprint_header.id)
                if not job_details:
                    logger.error(
                        "Failed to deploy range blueprint: %s", blueprint_header.name
                    )
                    continue

                deploy_job_ids.append(job_details.arq_job_id)
                job_to_range_type[job_details.arq_job_id] = range_type

            # Poll for deployment completion
            deploy_job_results = await wait_for_jobs(
                client, deploy_job_ids, timeout=600
            )

            # Fetch deployed range details
            for job_id in deploy_job_ids:
                current_range_type = job_to_range_type[job_id]
                job = deploy_job_results[job_id]

                # Skip failed deployments for now
                if not job or job.status == OpenLabsJobStatus.FAILED:
                    logger.error(
                        "Failed to deploy %s %s test range!",
                        current_range_type.value.upper(),
                        provider_upper,
                    )
                    continue

                # Skip lost ranges for now
                deployed_range = await get_range(client, job.result["id"])  # type: ignore
                if not deployed_range:
                    logger.error(
                        "Failed to find deployed %s %s test range!",
                        current_range_type.value.upper(),
                        provider_upper,
                    )
                    continue

                # RangeType --> Range, Email, Password
                yield_data[current_range_type] = (
                    deployed_range,
                    email,
                    password,
                )
                destroy_data[current_range_type] = deployed_range.id

            # Here it's safe to fail
            if len(yield_data) != len(blueprint_map):
                pytest.fail(
                    f"Failed to deploy all test ranges on {provider_upper}! See previous logs for details."
                )

            yield yield_data

        finally:
            destroy_job_ids: list[str] = []
            if destroy_data:
                # Send destroy requests
                for range_type, range_id in destroy_data.items():
                    job_details = await destroy_range(client, range_id)
                    if not job_details:
                        logger.critical(
                            "Failed to destroy %s %s test range. Possible dangling resources!",
                            range_type.value.upper(),
                            provider_upper,
                        )
                        continue

                    destroy_job_ids.append(job_details.arq_job_id)

                # Wait for results
                destroy_job_results = await wait_for_jobs(
                    client, destroy_job_ids, timeout=900
                )

                # Check results
                for job_id in destroy_job_ids:
                    job = destroy_job_results[job_id]
                    if not job or job.status == OpenLabsJobStatus.FAILED:
                        logger.critical(
                            "Failed to destroy %s %s test range. Possible dangling resources!",
                            range_type.value.upper(),
                            provider_upper,
                        )
                        continue


@pytest.fixture
def api_client(request: pytest.FixtureRequest) -> AsyncClient:
    """Return the corresponding client fixture.

    Only used for unauthenticated client fixtures.

    """
    return request.getfixturevalue(request.param)  # type: ignore


@pytest.fixture
def auth_api_client(request: pytest.FixtureRequest) -> AsyncClient:
    """Return the corresponding client fixture.

    Only use for authenticated client fixtures.

    """
    return request.getfixturevalue(request.param)  # type: ignore


@pytest.fixture
def mock_range_factory(
    mocker: MockerFixture,
) -> Iterator[Callable[..., MagicMock]]:
    """Provide a factory function to create and patch a customizable AbstractBaseRange mock.

    This fixture patches `RangeFactory.create_range` to return a `MagicMock`
    that is configured based on the arguments passed to the factory function.

    Yields:
        Callable[..., MagicMock]: A function to create and patch the mock.

    """
    from src.app.core.cdktf.ranges.base_range import AbstractBaseRange  # noqa: PLC0415
    from src.app.core.cdktf.ranges.range_factory import RangeFactory  # noqa: PLC0415
    from src.app.core.cdktf.stacks.base_stack import AbstractBaseStack  # noqa: PLC0415

    def _create_and_patch(  # noqa: D417, PLR0913
        # Arguments as specified in the user's original request
        has_secrets: bool = True,
        synthesize: bool = True,
        destroy: bool = True,
        deploy: DeployedRangeCreateSchema | None = None,
        get_provider_stack_class: type[AbstractBaseStack] | None = None,
        get_cred_env_vars: dict[str, Any] | None = None,
    ) -> MagicMock:
        """Patch RangeFactory.create_range and configures the mock's behavior.

        Args:
            (all): Arguments to configure the mock's methods and properties.

        Returns:
            MagicMock: The configured mock object.

        """
        deployed_create_schema = DeployedRangeCreateSchema.model_validate(
            valid_deployed_range_data
        )

        if deploy is None:
            deploy = deployed_create_schema

        if get_provider_stack_class is None:

            class FakeStack(AbstractBaseStack):
                def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
                    pass

                def build_resources(
                    self, *args: Any, **kwargs: Any  # noqa: ANN401
                ) -> None:
                    return None

            # Set the default value
            get_provider_stack_class = FakeStack

        # Fake class to appease unittest mocking
        class _RangeSpec(AbstractBaseRange):
            name: str = ""

        # Fail tests that call non-existent methods/attributes
        mock_range = MagicMock(
            spec_set=_RangeSpec, name="Mocked Range Factory Range Object"
        )

        # Configure mock methods based on args
        mock_range.has_secrets.return_value = has_secrets
        mock_range.synthesize.return_value = synthesize
        mock_range.deploy.return_value = deploy
        mock_range.destroy.return_value = destroy
        mock_range.get_cred_env_vars.return_value = (
            get_cred_env_vars if get_cred_env_vars is not None else {}
        )
        mock_range.get_provider_stack_class.return_value = get_provider_stack_class

        # Patch factory method to return mock
        mocker.patch.object(RangeFactory, "create_range", return_value=mock_range)

        return mock_range

    yield _create_and_patch
