import logging
import random
import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest
from arq import ArqRedis
from sqlalchemy.ext.asyncio import AsyncEngine

from src.app.core.worker.hooks import shutdown, startup


@pytest.fixture
def arq_hook_path() -> str:
    """Return dot path of ARQ worker hook functions."""
    return "src.app.core.worker.hooks"


@pytest.fixture
def mock_context() -> dict[str, Any]:
    """Generate a randomized ARQ context dictionary."""
    arq_job_id = str(uuid.uuid4()).replace("-", "")
    job_try = random.randint(1, 100)  # noqa: S311
    fake_redis = AsyncMock(spec=ArqRedis)
    return {"job_id": arq_job_id, "job_try": job_try, "redis": fake_redis}


async def test_arq_hook_startup_log(caplog: pytest.LogCaptureFixture) -> None:
    """Test that something gets logged when an ARQ worker starts."""
    fake_context = {"blah": "Blah"}

    await startup(fake_context)

    # Look for something that says "start"
    startup_msg = "start"

    assert any(
        record.levelno == logging.INFO and startup_msg in record.message.lower()
        for record in caplog.records
    ), "Nothing was logged in the ARQ startup function."


async def test_arq_hook_shutdown_log(caplog: pytest.LogCaptureFixture) -> None:
    """Test that something gets logged when an ARQ worker shutsdown."""
    fake_context = {"blah": "Blah"}

    await shutdown(fake_context)

    # Look for something that says "stop"
    shutdown_msg = "stop"

    assert any(
        record.levelno == logging.INFO and shutdown_msg in record.message.lower()
        for record in caplog.records
    ), "Nothing was logged in the ARQ shutdown function."


async def test_arq_hook_shutdown_dispose_db(
    monkeypatch: pytest.MonkeyPatch, arq_hook_path: str
) -> None:
    """Test that the shutdown hook disposes of the database engine."""
    fake_context = {"blah": "Blah"}

    # Patch over real engine
    mock_async_engine = AsyncMock(spec=AsyncEngine)
    mock_dispose = AsyncMock()
    mock_async_engine.dispose = mock_dispose
    monkeypatch.setattr(f"{arq_hook_path}.async_engine", mock_async_engine)

    await shutdown(fake_context)

    # Ensure we dispose
    mock_dispose.assert_awaited_once()
