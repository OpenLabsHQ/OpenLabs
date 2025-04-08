import uuid
from typing import Any, AsyncGenerator, Callable

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.scripts.create_admin import initialize_admin_user
from src.scripts.health_check import wait_for_api_ready
from tests.conftest import login_user


async def test_create_admin_script(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    db_override: Callable[[], AsyncGenerator[AsyncSession, None]],
) -> None:
    """Test that create_admin.py script works."""
    original_wait_for_api_ready = wait_for_api_ready

    async def wait_for_api_ready_wrapper(
        *args: Any, **kwargs: Any  # noqa: ANN401
    ) -> bool:
        """Wrap wait_for_api_ready to inject test client fixture."""
        kwargs["client"] = client
        return await original_wait_for_api_ready(*args, **kwargs)

    monkeypatch.setattr(
        "src.scripts.create_admin.wait_for_api_ready", wait_for_api_ready_wrapper
    )

    # New admin
    unique_str = uuid.uuid4()
    admin_email = f"admin-{unique_str}@test.com"
    admin_name = f"Admin-{unique_str}"
    admin_password = f"admin-password-{unique_str}"

    # Patch over settings with new admin user for testing
    monkeypatch.setattr(settings, "ADMIN_EMAIL", admin_email)
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", admin_password)
    monkeypatch.setattr(settings, "ADMIN_NAME", admin_name)

    # Patch database connection
    monkeypatch.setattr("src.scripts.create_admin.async_get_db", db_override)

    # Create admin user
    await initialize_admin_user()

    # Attempt to login as new admin
    assert await login_user(client, admin_email, admin_password)


async def test_create_admin_script_duplicate_user(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    db_override: Callable[[], AsyncGenerator[AsyncSession, None]],
) -> None:
    """Test that create_admin.py script works when the admin user already exists."""
    original_wait_for_api_ready = wait_for_api_ready

    async def wait_for_api_ready_wrapper(
        *args: Any, **kwargs: Any  # noqa: ANN401
    ) -> bool:
        """Wrap wait_for_api_ready to inject test client fixture."""
        kwargs["client"] = client
        return await original_wait_for_api_ready(*args, **kwargs)

    monkeypatch.setattr(
        "src.scripts.create_admin.wait_for_api_ready", wait_for_api_ready_wrapper
    )

    # New admin
    unique_str = uuid.uuid4()
    admin_email = f"admin-{unique_str}@test.com"
    admin_name = f"Admin-{unique_str}"
    admin_password = f"admin-password-{unique_str}"

    # Patch over settings with new admin user for testing
    monkeypatch.setattr(settings, "ADMIN_EMAIL", admin_email)
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", admin_password)
    monkeypatch.setattr(settings, "ADMIN_NAME", admin_name)

    # Patch database connection
    monkeypatch.setattr("src.scripts.create_admin.async_get_db", db_override)

    # Create admin user
    await initialize_admin_user()

    # Create duplicate admin user to test it doesn't fail
    await initialize_admin_user()

    # Attempt to login as new admin
    assert await login_user(client, admin_email, admin_password)


async def test_initialize_admin_user_api_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test initialize_admin_user when the API is not ready."""

    # Mock wait_for_api_ready to return False
    async def mock_wait_for_api_ready(
        *args: Any, **kwargs: Any  # noqa: ANN401
    ) -> bool:
        return False

    monkeypatch.setattr(
        "src.scripts.create_admin.wait_for_api_ready", mock_wait_for_api_ready
    )

    # Mock sys.exit to prevent actual exit
    def mock_exit(code: int) -> None:
        raise SystemExit(code)

    monkeypatch.setattr("sys.exit", mock_exit)

    # Assert that SystemExit is raised with code 1
    with pytest.raises(SystemExit) as excinfo:
        await initialize_admin_user()

    assert excinfo.value.code == 1


async def test_initialize_admin_user_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test initialize_admin_user when an exception occurs during user initialization."""

    # Mock wait_for_api_ready to return True
    async def mock_wait_for_api_ready(
        *args: Any, **kwargs: Any  # noqa: ANN401
    ) -> bool:
        return True

    monkeypatch.setattr(
        "src.scripts.create_admin.wait_for_api_ready", mock_wait_for_api_ready
    )

    # Mock async_get_db to raise an exception
    async def mock_async_get_db() -> AsyncGenerator[None, None]:
        msg = "Database connection error"
        raise Exception(msg)
        yield

    monkeypatch.setattr("src.scripts.create_admin.async_get_db", mock_async_get_db)

    # Mock sys.exit to prevent actual exit
    def mock_exit(code: int) -> None:
        raise SystemExit(code)

    monkeypatch.setattr("sys.exit", mock_exit)

    # Assert that SystemExit is raised with code 1
    with pytest.raises(SystemExit) as excinfo:
        await initialize_admin_user()

    assert excinfo.value.code == 1
