import pytest

from src.app.crud.crud_ranges import delete_blueprint_range, delete_deployed_range

from .crud_mocks import DummyBlueprintRange, DummyDB, DummyDeployedRange


async def test_no_delete_non_standalone_blueprint_ranges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that deleting non-standalone ranges fails."""
    dummy_db = DummyDB()

    # Patch host model is_standalone() method to always return False
    dummy_range = DummyBlueprintRange()
    monkeypatch.setattr(dummy_range, "is_standalone", lambda: False)

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    assert not await delete_blueprint_range(dummy_db, 1, 100)  # type: ignore

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.commit.assert_not_called()


async def test_delete_range_exception_return_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that delete_range() returns False when an exception is raised internally."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    # Force exception to be thrown
    exception_msg = "Forced exception for tesitng."
    dummy_db.flush.side_effect = Exception(exception_msg)

    # Make sure our user owns the range
    user_id = 1
    dummy_range.owner_id = user_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    # Ignoring type mismatches with testing mocks
    with pytest.raises(Exception, match=exception_msg):
        await delete_deployed_range(dummy_db, range_id=1, user_id=user_id)  # type: ignore
