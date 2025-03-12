import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable, Generator
from fastapi import status

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
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


def skip_if_env(var: str, reason: str) -> pytest.MarkDecorator:
    """Return a pytest mark to skip tests if the specified environment variable is set.

    Args:
    ----
        var (str): Environment var to check if set.
        reason (str): Reason why test is being skipped.

    Returns:
    -------
        pytest.MarkDecorator: Pytest skip test decorator.

    """
    return pytest.mark.skipif(os.getenv(var) is not None, reason=reason)


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
    """Create async database engine for the entire test session.

    Args:
    ----
        postgres_container (str): Postgres container connection string.

    Returns:
    -------
        AsyncGenerator[AsyncEngine, None]: Async database engine.

    """
    engine = create_async_engine(postgres_container, echo=False, future=True)
    yield engine
    await engine.dispose()


async def override_get_current_user(user_id: uuid.UUID) -> UserModel:
    """Override get_current_user() auth function."""
    return UserModel(
        id=user_id,
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


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
async def client(
    db_override: Callable[[], AsyncGenerator[AsyncSession, None]],
) -> AsyncGenerator[AsyncClient, None]:
    """Get async client fixture connected to the FastAPI app and test database container."""
    from src.app.main import app

    app.dependency_overrides[async_get_db] = db_override

    # Use httpx's ASGITransport to run requests against the FastAPI app in-memory
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # Clean up overrides after the test finishes
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(
    db_override: Callable[[], AsyncGenerator[AsyncSession, None]],
) -> AsyncGenerator[AsyncClient, None]:
    """Get authenticated async client fixture conntected to the FastAPI app and test database container."""
    from src.app.main import app

    # Override database dependency
    app.dependency_overrides[async_get_db] = db_override

    response = await client.post( ## FIX HERE FOR HAVING AUTH_CLIENT REGISTER A USER TO USE FOR UPLOADING TEMPLATES TO DATABASE AND PULLING FROM DATABASE
        f"{BASE_ROUTE}/auth/register", json=base_user_register_payload
    )

    assert response.status_code == status.HTTP_200_OK
    user_id = response.json()["id"]

    # Override authentication depdency
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Use httpx's ASGITransport to run requests against the FastAPI app in-memory
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # Clean up overrides after the test finishes
    app.dependency_overrides.clear()
