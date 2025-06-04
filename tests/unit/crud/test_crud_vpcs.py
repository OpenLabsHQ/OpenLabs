import pytest

from src.app.crud.crud_vpcs import delete_blueprint_vpc

from .crud_mocks import DummyBlueprintVPC, DummyDB


async def test_no_delete_non_standalone_blueprint_vpcs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that deleting non-standalone blueprint VPCs fails."""
    dummy_db = DummyDB()

    # Patch host model is_standalone() method to always return False
    dummy_vpc = DummyBlueprintVPC()
    monkeypatch.setattr(dummy_vpc, "is_standalone", lambda: False)

    # Ensure that we get the dummy VPC from the "db"
    dummy_db.get.return_value = dummy_vpc

    assert not await delete_blueprint_vpc(dummy_db, 1, 100)  # type: ignore

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.commit.assert_not_called()
