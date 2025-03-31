import pytest

from src.app.crud.crud_subnet_templates import delete_subnet_template

from .crud_mocks import DummyDB, DummyTemplateSubnet


async def test_no_delete_non_standalone_subnet_templates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that delete_subnet_template() returns false when subnet template is not standalone."""
    dummy_db = DummyDB()

    # Patch host model is_standalone() method to always return False
    dummy_subnet = DummyTemplateSubnet()
    monkeypatch.setattr(dummy_subnet, "is_standalone", lambda: False)

    result = await delete_subnet_template(dummy_db, dummy_subnet)  # type: ignore
    assert result is False  # Strict check

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.commit.assert_not_called()
