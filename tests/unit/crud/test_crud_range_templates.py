import pytest

from src.app.crud.crud_range_templates import delete_range_template

from .crud_mocks import DummyDB, DummyTemplateRange


async def test_no_delete_non_standalone_range_templates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that delete_range_template() returns false when range template is not standalone."""
    dummy_db = DummyDB()

    # Patch host model is_standalone() method to always return False
    dummy_range = DummyTemplateRange()
    monkeypatch.setattr(dummy_range, "is_standalone", lambda: False)

    result = await delete_range_template(dummy_db, dummy_range)  # type: ignore
    assert result is False  # Strict check

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.commit.assert_not_called()
