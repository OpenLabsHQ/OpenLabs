import asyncio
import copy
import logging
import os
import shutil
import socket
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Coroutine, Generator

import httpx
import pytest
import pytest_asyncio
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

from src.app.core.auth.auth import get_current_user
from src.app.core.cdktf.ranges.base_range import AbstractBaseRange
from src.app.core.cdktf.ranges.range_factory import RangeFactory
from src.app.core.cdktf.stacks.base_stack import AbstractBaseStack
from src.app.core.config import settings
from src.app.core.db.database import Base, async_get_db
from src.app.enums.regions import OpenLabsRegion
from src.app.models.user_model import UserModel
from src.app.schemas.secret_schema import SecretSchema
from src.app.schemas.template_range_schema import TemplateRangeSchema
from src.app.schemas.user_schema import UserID
from src.app.utils.cdktf_utils import create_cdktf_dir
from tests.api.v1.config import BASE_ROUTE, base_user_register_payload

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
    Callable[[type[AbstractBaseStack], TemplateRangeSchema, str, OpenLabsRegion], str]
):
    """Get factory to generate CDKTF synthesis for different stack classes."""
    from cdktf import Testing

    def _synthesize(
        stack_cls: type[AbstractBaseStack],
        cyber_range: TemplateRangeSchema,
        stack_name: str = "test_range",
        region: OpenLabsRegion = OpenLabsRegion.US_EAST_1,
    ) -> str:
        """Synthesize generic stack using CDKTF testing library."""
        app = Testing.app()

        # Synthesize the stack using the provided stack class
        return str(
            Testing.synth(
                stack_cls(app, cyber_range, stack_name, settings.CDKTF_DIR, region)
            )
        )

    return _synthesize


@pytest.fixture(scope="module")
def range_factory() -> Callable[
    [type[AbstractBaseRange], TemplateRangeSchema, OpenLabsRegion],
    AbstractBaseRange,
]:
    """Get factory to generate range object sythesis output."""

    def _range_synthesize(
        range_cls: type[AbstractBaseRange],
        template: TemplateRangeSchema,
        region: OpenLabsRegion = OpenLabsRegion.US_EAST_1,
        state_file: None = None,
    ) -> AbstractBaseRange:
        """Create range object and return synth() output."""
        range_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        secrets = SecretSchema()

        return RangeFactory.create_range(
            id=range_id,
            template=template,
            region=region,
            owner_id=UserID(id=owner_id),
            secrets=secrets,
            state_file=state_file,
        )

    return _range_synthesize


@pytest_asyncio.fixture(scope="function")
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


@pytest_asyncio.fixture(scope="function")
async def db_override(
    async_engine: AsyncEngine,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """Fixture to override database dependency in test FastAPI app."""
    # Create a session factory using the captured engine.
    async_session = async_sessionmaker(
        bind=async_engine, expire_on_commit=False, class_=AsyncSession
    )

    async def override_async_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session() as session:
            yield session

    return override_async_get_db


@pytest.fixture(scope="function")
def client_app(
    db_override: Callable[[], AsyncGenerator[AsyncSession, None]],
) -> FastAPI:
    """Create app for client fixture."""
    from src.app.main import app

    app.dependency_overrides[async_get_db] = db_override

    return app


@pytest.fixture(scope="function")
def auth_client_app(
    db_override: Callable[[], AsyncGenerator[AsyncSession, None]],
) -> FastAPI:
    """Create app for auth_client fixture."""
    from src.app.main import app

    app.dependency_overrides[async_get_db] = db_override

    return app


@pytest_asyncio.fixture(scope="function")
async def test_user_id(
    auth_client_app: FastAPI,
) -> uuid.UUID:
    """Register a user for testing auth_client fixture."""
    registration_payload = copy.deepcopy(base_user_register_payload)

    unique_str = str(uuid.uuid4())

    # Create unique email
    email_split = registration_payload["email"].split("@")
    email_split_len = 2  # username and domain from email
    assert len(email_split) == email_split_len
    registration_payload["email"] = f"{email_split[0]}-{unique_str}@{email_split[1]}"

    # Make name unique for debugging
    registration_payload["name"] = f"{registration_payload["name"]} {unique_str}"

    reg_transport = ASGITransport(app=auth_client_app)
    user_id = ""
    async with AsyncClient(
        transport=reg_transport, base_url="http://register"
    ) as client:
        response = await client.post(
            f"{BASE_ROUTE}/auth/register", json=registration_payload
        )
        assert response.status_code == status.HTTP_200_OK, "Failed to register user."

        user_id = response.json()["id"]

        assert user_id, "Failed to retrieve test user ID."

    return uuid.UUID(user_id, version=4)


@pytest.fixture(scope="function")
def auth_override(
    test_user_id: uuid.UUID,
) -> Callable[[], UserModel]:
    """Override get_current_user() auth function."""

    def override_get_current_user() -> UserModel:
        return UserModel(
            id=test_user_id,
            name="Test User",
            email="test@example.com",
            hashed_password="dummy",  # noqa: S106 (Testing only)
            created_at=datetime.now(tz=timezone.utc),
            last_active=datetime.now(tz=timezone.utc),
            is_admin=False,
            public_key=None,
            encrypted_private_key=None,
            key_salt=None,
        )

    return override_get_current_user


@pytest_asyncio.fixture(scope="function")
async def client(
    client_app: FastAPI,
) -> AsyncGenerator[AsyncClient, None]:
    """Get async client fixture connected to the FastAPI app and test database container."""
    transport = ASGITransport(app=client_app)

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # Clean up overrides after the test finishes
    client_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_client(
    auth_client_app: FastAPI,
    auth_override: Callable[[], UserModel],
    test_user_id: uuid.UUID,
) -> AsyncGenerator[AsyncClient, None]:
    """Get authenticated async client fixture conntected to the FastAPI app and test database container."""
    logger.info("Authenticaed tests happening as user: %s", test_user_id)

    auth_client_app.dependency_overrides[get_current_user] = auth_override

    # Use httpx's ASGITransport to run requests against the FastAPI app in-memory
    transport = ASGITransport(app=auth_client_app)

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # Clean up overrides after the test finishes
    auth_client_app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def get_free_port() -> int:
    """Get an unused port on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


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
def docker_services(get_free_port: int) -> Generator[DockerCompose, None, None]:
    """Spin up docker compose environment using `docker-compose.yml` in project root."""
    port_var_name = "API_PORT"

    # Export test config
    os.environ[port_var_name] = str(get_free_port)

    with DockerCompose(
        context=".",
        compose_file_name="docker-compose.yml",
        pull=True,
        build=True,
        wait=True,
        keep_volumes=False,
    ) as compose:
        logger.info("Docker Compose environment started.")

        yield compose

    compose.stop(down=True)
    del os.environ[port_var_name]
    logger.info("Docker Compose environment stopped.")


@pytest_asyncio.fixture(scope="session")
async def integration_client(
    docker_services: DockerCompose, get_free_port: int
) -> AsyncGenerator[AsyncClient, None]:
    """Create async client that connects to live FastAPI docker compose container."""
    base_url = f"http://localhost:{get_free_port}"

    # Wait for docker compose and container to start
    await wait_for_fastapi_service(base_url, timeout=60)

    async with AsyncClient(base_url=base_url) as client:
        yield client
