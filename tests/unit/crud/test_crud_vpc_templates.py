import pytest

from src.app.crud.crud_vpc_templates import delete_vpc_template

from .crud_mocks import DummyDB, DummyTemplateVPC


async def test_no_delete_non_standalone_vpc_templates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that delete_vpc_template() returns false when VPC template is not standalone."""
    dummy_db = DummyDB()

    # Patch host model is_standalone() method to always return False
    dummy_vpc = DummyTemplateVPC()
    monkeypatch.setattr(dummy_vpc, "is_standalone", lambda: False)

    result = await delete_vpc_template(dummy_db, dummy_vpc)  # type: ignore
    assert result is False  # Strict check

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.commit.assert_not_called()
