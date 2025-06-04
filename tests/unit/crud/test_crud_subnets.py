import pytest

from src.app.crud.crud_subnets import delete_blueprint_subnet

from .crud_mocks import DummyBlueprintSubnet, DummyDB


async def test_no_delete_non_standalone_blueprint_subnets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that deleting a non-standalone blueprint subnet fails."""
    dummy_db = DummyDB()

    # Patch host model is_standalone() method to always return False
    dummy_subnet = DummyBlueprintSubnet()
    monkeypatch.setattr(dummy_subnet, "is_standalone", lambda: False)

    # Ensure that we get the dummy subnet from the "db"
    dummy_db.get.return_value = dummy_subnet

    assert not await delete_blueprint_subnet(dummy_db, 1, 100)  # type: ignore

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.commit.assert_not_called()
