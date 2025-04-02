import uuid
from unittest.mock import MagicMock

import pytest

from src.app.crud.crud_ranges import delete_range, is_range_owner
from src.app.schemas.range_schema import RangeID

from .crud_mocks import DummyDB, DummyRangeModel


async def test_delete_range_exception_return_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that delete_range() returns False when an exception is raised internally."""
    dummy_db = DummyDB()
    dummy_range = DummyRangeModel()

    # Force exception to be thrown
    dummy_db.commit.side_effect = Exception("Forced exception for testing.")

    # Ignoring type mismatches with testing mocks
    result = await delete_range(dummy_db, dummy_range)  # type: ignore

    assert result is False


async def test_is_range_owner_returns_true() -> None:
    """Test that is_range_owner() returns True when it returns a result with a range owned by the user."""
    dummy_db = DummyDB()

    # Create a dummy result with a non-None value returned by scalar_one_or_none()
    dummy_result = MagicMock()
    dummy_result.scalar_one_or_none.return_value = object()
    dummy_db.execute.return_value = dummy_result

    dummy_range_id = RangeID(id=uuid.uuid4())
    dummy_user_id = uuid.uuid4()

    # Ignoring type mismatches with testing mocks
    result = await is_range_owner(dummy_db, dummy_range_id, dummy_user_id)  # type: ignore

    assert result is True


async def test_is_range_owner_returns_false() -> None:
    """Test that the is_range_owner() return False when it returns no results of a range owned the user."""
    dummy_db = DummyDB()
    # Create a dummy result with None returned by scalar_one_or_none() to simulate no result
    dummy_result = MagicMock()
    dummy_result.scalar_one_or_none.return_value = None
    dummy_db.execute.return_value = dummy_result

    dummy_range_id = RangeID(id=uuid.uuid4())
    dummy_user_id = uuid.uuid4()

    # Ignoring type mismatches with testing mocks
    result = await is_range_owner(dummy_db, dummy_range_id, dummy_user_id)  # type: ignore
    assert result is False
