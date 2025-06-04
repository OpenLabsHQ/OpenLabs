import pytest

from src.app.crud.crud_hosts import delete_blueprint_host

from .crud_mocks import DummyBlueprintHost, DummyDB


async def test_no_delete_non_standalone_host_templates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that delete_host_template() returns false when host template is not standalone."""
    dummy_db = DummyDB()

    # Patch host model is_standalone() method to always return False
    dummy_host = DummyBlueprintHost()
    monkeypatch.setattr(dummy_host, "is_standalone", lambda: False)

    # Ensure that we get the dummy host from the "db"
    dummy_db.get.return_value = dummy_host

    assert not await delete_blueprint_host(dummy_db, dummy_host, 100)  # type: ignore

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.commit.assert_not_called()
