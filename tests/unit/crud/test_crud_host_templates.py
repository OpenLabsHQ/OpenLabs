import pytest

from src.app.crud.crud_host_templates import delete_host_template

from .crud_mocks import DummyDB, DummyTemplateHost


async def test_no_delete_non_standalone_host_templates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that delete_host_template() returns false when host template is not standalone."""
    dummy_db = DummyDB()

    # Patch host model is_standalone() method to always return False
    dummy_host = DummyTemplateHost()
    monkeypatch.setattr(dummy_host, "is_standalone", lambda: False)

    result = await delete_host_template(dummy_db, dummy_host)  # type: ignore
    assert result is False  # Strict check

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.commit.assert_not_called()
