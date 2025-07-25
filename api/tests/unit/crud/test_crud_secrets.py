import re
from unittest.mock import MagicMock
import pytest
from pytest_mock import MockerFixture

from src.app.models.secret_model import SecretModel
from .crud_mocks import DummyDB
from src.app.crud.crud_secrets import get_user_secrets, upsert_user_secrets
from src.app.schemas.secret_schema import SecretSchema


@pytest.fixture
def crud_secrets_path() -> str:
    """Return the dot path of the tested crud secrets file."""
    return "src.app.crud.crud_secrets"


async def test_upsert_user_secrets() -> None:
    """Test that updating user secrets works correctly."""
    mock_db = DummyDB()
    fake_secrets = SecretSchema()
    mock_user_id = 1

    await upsert_user_secrets(db=mock_db, secrets=fake_secrets, user_id=mock_user_id)

    # Check we upsert correctly
    mock_db.merge.assert_awaited_once()

    # Check we are upserting the creds for the correct user
    called_with_object = mock_db.merge.call_args[0][0]

    # 5. Assert that the object has the correct attributes
    assert isinstance(called_with_object, SecretModel)
    assert called_with_object.user_id == mock_user_id


async def test_get_user_secrets_success(mocker: MockerFixture) -> None:
    """Tests successfully retrieving user secrets when they exist."""
    dummy_db = DummyDB()
    user_id = 123
    mock_secret_model = MagicMock()

    # Mock the full database call to return mock model
    mock_result = dummy_db.execute.return_value
    mock_result.scalars = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_secret_model

    # Patch validation of secrets
    mock_validate = mocker.patch.object(
        SecretSchema, "model_validate", return_value="validated_secrets"
    )

    result = await get_user_secrets(db=dummy_db, user_id=user_id)
    assert result == "validated_secrets"
    mock_validate.assert_called_once_with(mock_secret_model)

    # Verify the fetching secrets for correct user
    stmt = dummy_db.execute.call_args[0][0]
    assert str(SecretModel.user_id == user_id) in str(stmt.whereclause)


async def test_get_user_secrets_not_found(caplog: pytest.LogCaptureFixture) -> None:
    """Tests that None is returned and a message is logged when secrets are not found."""
    dummy_db = DummyDB()
    user_id = 404

    # Mock the database to return no results
    dummy_db.execute.return_value = None

    result = await get_user_secrets(db=dummy_db, user_id=user_id)
    assert result is None
    assert re.search(f"failed to fetch secrets.*{user_id}", caplog.text, re.IGNORECASE)
