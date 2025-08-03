import logging
import random
from unittest.mock import MagicMock, Mock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError

from src.app.crud.crud_ranges import (
    build_blueprint_range_models,
    build_deployed_range_models,
    create_blueprint_range,
    create_deployed_range,
    delete_blueprint_range,
    delete_deployed_range,
    get_blueprint_range,
    get_blueprint_range_headers,
    get_deployed_range,
    get_deployed_range_headers,
    get_deployed_range_key,
)
from src.app.models.range_models import BlueprintRangeModel, DeployedRangeModel
from src.app.schemas.range_schemas import (
    BlueprintRangeCreateSchema,
    BlueprintRangeHeaderSchema,
    BlueprintRangeSchema,
    DeployedRangeCreateSchema,
    DeployedRangeHeaderSchema,
    DeployedRangeSchema,
)
from tests.common.api.v1.config import (
    valid_blueprint_range_create_payload,
    valid_deployed_range_data,
)

from .crud_mocks import DummyBlueprintRange, DummyDB, DummyDeployedRange

# ==================== Blueprints =====================


@pytest.mark.parametrize(
    "is_admin, expect_owner_filter",
    [
        (False, True),
        (True, False),
    ],
)
async def test_get_blueprint_vpc_headers_filters(
    is_admin: bool,
    expect_owner_filter: bool,
) -> None:
    """Test the blueprint range headers crud function filters results appropriately."""
    dummy_db = DummyDB()

    # Build mock of result.mappings().all()
    mock_sqlalchemy_result = MagicMock(name="SQLAlchemyResult")
    mock_mappings_object = MagicMock(name="MappingsObject")
    mock_mappings_object.all.return_value = []
    mock_sqlalchemy_result.mappings.return_value = mock_mappings_object

    # Configure return of mock result
    dummy_db.execute.return_value = mock_sqlalchemy_result

    user_id = 1
    await get_blueprint_range_headers(dummy_db, user_id=user_id, is_admin=is_admin)

    # Build filter clauses
    ownership_clause = str(BlueprintRangeModel.owner_id == user_id)
    where_clause = str(dummy_db.execute.call_args[0][0].whereclause)

    assert (ownership_clause in where_clause) == expect_owner_filter


async def test_no_get_unauthorized_blueprint_ranges() -> None:
    """Test that the crud function returns none when the user doesn't own the range blueprint."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    # Ensure that User's ID doesn't match the range's owner
    user_id = 1
    dummy_range.owner_id = user_id + 1
    assert user_id != dummy_range.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    assert not await get_blueprint_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )


async def test_owner_get_blueprint_ranges(
    mocker: MockerFixture,
) -> None:
    """Test that the crud function returns blueprint ranges when the correct owner requests them."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    # Ensure that User's ID matches the range's owner
    user_id = 1
    dummy_range.owner_id = user_id
    assert user_id == dummy_range.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintRangeSchema, "model_validate", return_value=dummy_range
    )

    assert await get_blueprint_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintRange)


async def test_admin_get_all_blueprint_ranges(
    mocker: MockerFixture,
) -> None:
    """Test that the crud function returns blueprint ranges when the user doesn't own the range blueprint but is admin."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    # Ensure that User's ID doesn't match the range's owner
    user_id = 1
    dummy_range.owner_id = user_id + 1
    assert user_id != dummy_range.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintRangeSchema, "model_validate", return_value=dummy_range
    )

    assert await get_blueprint_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=True
    )
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintRange)


async def test_get_non_existent_blueprint_range() -> None:
    """Test that the crud function returns None when the blueprint range doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the VPC doesn't exist
    dummy_db.get.return_value = None

    assert not await get_blueprint_range(dummy_db, range_id=1, user_id=-1)


async def test_build_blueprint_range_models() -> None:
    """Test that the we can build blueprint range models from blueprint range creation schemas."""
    blueprint_range_create_schema = BlueprintRangeCreateSchema.model_validate(
        valid_blueprint_range_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    blueprint_range_models = build_blueprint_range_models(
        [blueprint_range_create_schema], user_id
    )

    assert len(blueprint_range_models) == 1
    assert blueprint_range_models[0].owner_id == user_id
    assert blueprint_range_models[0].name == blueprint_range_create_schema.name


async def test_create_blueprint_ranges_too_many_models(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function for blueprint ranges raises an exception if we get back more models than input schemas."""
    dummy_db = DummyDB()

    blueprint_range_create_schema = BlueprintRangeCreateSchema.model_validate(
        valid_blueprint_range_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Return too many "models"
    mocker.patch(
        "src.app.crud.crud_ranges.build_blueprint_range_models",
        return_value=["fake", "list"],
    )

    with pytest.raises(
        RuntimeError, match="range blueprint models from a single schema"
    ):
        await create_blueprint_range(dummy_db, blueprint_range_create_schema, user_id)


async def test_create_blueprint_range_raises_db_exceptions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the creation crud function for blueprint ranges passes on db exceptions and logs them."""
    dummy_db = DummyDB()

    blueprint_range_create_schema = BlueprintRangeCreateSchema.model_validate(
        valid_blueprint_range_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await create_blueprint_range(dummy_db, blueprint_range_create_schema, user_id)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_create_blueprint_range_raises_generic_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the creation crud function for blueprint ranges passes on generic exceptions and logs them."""
    dummy_db = DummyDB()

    blueprint_range_create_schema = BlueprintRangeCreateSchema.model_validate(
        valid_blueprint_range_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Force a db exception
    test_except_msg = "Fake generic error!"
    dummy_db.flush.side_effect = RuntimeError(test_except_msg)

    with pytest.raises(RuntimeError, match=test_except_msg):
        await create_blueprint_range(dummy_db, blueprint_range_create_schema, user_id)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_delete_non_existent_blueprint_range() -> None:
    """Test that the delete crud function returns None when the blueprint range doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the VPC doesn't exist
    dummy_db.get.return_value = None

    assert not await delete_blueprint_range(dummy_db, range_id=1, user_id=-1)
    dummy_db.delete.assert_not_called()


async def test_no_delete_unauthorized_blueprint_ranges() -> None:
    """Test that the delete crud function returns none when the user doesn't own the range blueprint."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    # Ensure that User's ID doesn't match the range's owner
    user_id = 1
    dummy_range.owner_id = user_id + 1
    assert user_id != dummy_range.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    assert not await delete_blueprint_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )
    dummy_db.delete.assert_not_called()


async def test_admin_delete_all_blueprint_ranges(
    mocker: MockerFixture,
) -> None:
    """Test that the delete crud function returns blueprint ranges when the user doesn't own the range blueprint but is admin."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    # Ensure that User's ID doesn't match the range's owner
    user_id = 1
    dummy_range.owner_id = user_id + 1
    assert user_id != dummy_range.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintRangeHeaderSchema, "model_validate", return_value=dummy_range
    )

    assert await delete_blueprint_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=True
    )
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintRange)

    # Check it was deleted
    dummy_db.delete.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_delete_blueprint_range_raises_db_exceptions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the delete crud function for blueprint ranges passes on db exceptions and logs them."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    # Ensure that we get the dummy range from "db"
    dummy_db.get.return_value = dummy_range

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await delete_blueprint_range(dummy_db, range_id=1, user_id=1, is_admin=True)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_delete_blueprint_range_raises_generic_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the delete crud function for blueprint ranges passes on generic exceptions and logs them."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    # Ensure that we get the dummy range from "db"
    dummy_db.get.return_value = dummy_range

    # Force a db exception
    test_except_msg = "Fake generic error!"
    dummy_db.flush.side_effect = RuntimeError(test_except_msg)

    with pytest.raises(RuntimeError, match=test_except_msg):
        await delete_blueprint_range(dummy_db, range_id=1, user_id=1, is_admin=True)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


# ==================== Deployed (Instances) =====================


async def test_build_deployed_range_models() -> None:
    """Test that the we can build deployed range models from range creation schemas."""
    deployed_range_create_schema = DeployedRangeCreateSchema.model_validate(
        valid_deployed_range_data, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    deployed_range_models = build_deployed_range_models(
        [deployed_range_create_schema], user_id
    )

    assert len(deployed_range_models) == 1
    assert deployed_range_models[0].owner_id == user_id
    assert deployed_range_models[0].name == deployed_range_create_schema.name


@pytest.mark.parametrize(
    "is_admin, expect_owner_filter",
    [
        (False, True),
        (True, False),
    ],
)
async def test_get_deployed_range_headers_filters(
    is_admin: bool,
    expect_owner_filter: bool,
) -> None:
    """Test the deployed range headers crud function filters results appropriately."""
    dummy_db = DummyDB()

    # Build mock of result.mappings().all()
    mock_sqlalchemy_result = MagicMock(name="SQLAlchemyResult")
    mock_mappings_object = MagicMock(name="MappingsObject")
    mock_mappings_object.all.return_value = []
    mock_sqlalchemy_result.mappings.return_value = mock_mappings_object

    # Configure return of mock result
    dummy_db.execute.return_value = mock_sqlalchemy_result

    user_id = 1
    await get_deployed_range_headers(dummy_db, user_id=user_id, is_admin=is_admin)

    # Build filter clauses
    ownership_clause = str(DeployedRangeModel.owner_id == user_id)
    where_clause = str(dummy_db.execute.call_args[0][0].whereclause)

    assert (ownership_clause in where_clause) == expect_owner_filter


async def test_no_get_unauthorized_deployed_ranges() -> None:
    """Test that the crud function returns none when the user doesn't own the deployed range."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    # Ensure that User's ID doesn't match the range's owner
    user_id = 1
    dummy_range.owner_id = user_id + 1
    assert user_id != dummy_range.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    assert not await get_deployed_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )


async def test_owner_get_deployed_ranges(
    mocker: MockerFixture,
) -> None:
    """Test that the crud function returns deployed ranges when the correct owner requests them."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    # Ensure that User's ID matches the range's owner
    user_id = 1
    dummy_range.owner_id = user_id
    assert user_id == dummy_range.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        DeployedRangeSchema, "model_validate", return_value=dummy_range
    )

    assert await get_deployed_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyDeployedRange)


async def test_admin_get_all_deployed_ranges(
    mocker: MockerFixture,
) -> None:
    """Test that the crud function returns deployed ranges when the user doesn't own the deployed range but is admin."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    # Ensure that User's ID doesn't match the range's owner
    user_id = 1
    dummy_range.owner_id = user_id + 1
    assert user_id != dummy_range.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        DeployedRangeSchema, "model_validate", return_value=dummy_range
    )

    assert await get_deployed_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=True
    )
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyDeployedRange)


async def test_get_non_existent_deployed_range() -> None:
    """Test that the crud function returns None when the deployed range doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the VPC doesn't exist
    dummy_db.get.return_value = None

    assert not await get_deployed_range(dummy_db, range_id=1, user_id=-1)


@pytest.mark.parametrize(
    "is_admin, user_owns_range",
    [
        (False, True),  # Regular user, owns range - should get key
        (False, False),  # Regular user, doesn't own range - should not get key
        (True, False),  # Admin user, doesn't own range - should get key
    ],
)
async def test_get_deployed_range_key_permissions(
    is_admin: bool,
    user_owns_range: bool,
) -> None:
    """Test the deployed range key crud function respects permissions."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    range_id = 1
    user_id = 1

    # Set ownership based on test parameters
    if user_owns_range:
        dummy_range.owner_id = user_id
    else:
        dummy_range.owner_id = user_id + 1

    # Configure return of mock result
    dummy_db.get.return_value = dummy_range
    dummy_db.scalar.return_value = "fake_private_key"

    result = await get_deployed_range_key(
        dummy_db, range_id=range_id, user_id=user_id, is_admin=is_admin
    )

    # Check if we should expect a result
    should_have_access = is_admin or user_owns_range

    if should_have_access:
        assert result is not None
        assert result.range_private_key == "fake_private_key"
    else:
        assert result is None


async def test_get_non_existent_deployed_range_key() -> None:
    """Test that the crud function returns None when the deployed range key doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the VPC doesn't exist
    dummy_db.scalar.return_value = None

    assert not await get_deployed_range_key(dummy_db, range_id=1, user_id=-1)


async def test_create_deployed_ranges_too_many_models(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function for deployed ranges raises an exception if we get back more models than input schemas."""
    dummy_db = DummyDB()

    blueprint_range_create_schema = BlueprintRangeCreateSchema.model_validate(
        valid_blueprint_range_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Return too many "models"
    mocker.patch(
        "src.app.crud.crud_ranges.build_blueprint_range_models",
        return_value=["fake", "list"],
    )

    with pytest.raises(
        RuntimeError, match="range blueprint models from a single schema"
    ):
        await create_blueprint_range(dummy_db, blueprint_range_create_schema, user_id)


async def test_create_deployed_range_too_many_models(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function for deployed ranges raises an exception if we get back more models than input schemas."""
    dummy_db = DummyDB()

    deployed_range_create_schema = DeployedRangeCreateSchema.model_validate(
        valid_deployed_range_data, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Return too many "models"
    mocker.patch(
        "src.app.crud.crud_ranges.build_deployed_range_models",
        return_value=["fake", "list"],
    )

    with pytest.raises(
        RuntimeError, match="deployed range models from a single schema"
    ):
        await create_deployed_range(dummy_db, deployed_range_create_schema, user_id)


async def test_create_deployed_range_raises_db_exceptions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the creation crud function for deployed ranges passes on db exceptions and logs them."""
    dummy_db = DummyDB()

    deployed_range_create_schema = DeployedRangeCreateSchema.model_validate(
        valid_deployed_range_data, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await create_deployed_range(dummy_db, deployed_range_create_schema, user_id)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_create_deployed_range_raises_generic_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the creation crud function for deployed ranges passes on generic exceptions and logs them."""
    dummy_db = DummyDB()

    deployed_range_create_schema = DeployedRangeCreateSchema.model_validate(
        valid_deployed_range_data, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Force a db exception
    test_except_msg = "Fake generic error!"
    dummy_db.flush.side_effect = RuntimeError(test_except_msg)

    with pytest.raises(RuntimeError, match=test_except_msg):
        await create_deployed_range(dummy_db, deployed_range_create_schema, user_id)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_delete_non_existent_deployed_range() -> None:
    """Test that the delete crud function returns None when the deployed range doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the VPC doesn't exist
    dummy_db.get.return_value = None

    assert not await delete_deployed_range(dummy_db, range_id=1, user_id=-1)
    dummy_db.delete.assert_not_called()


async def test_no_delete_unauthorized_deployed_ranges() -> None:
    """Test that the delete crud function returns none when the user doesn't own the deployed range."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    # Ensure that User's ID doesn't match the range's owner
    user_id = 1
    dummy_range.owner_id = user_id + 1
    assert user_id != dummy_range.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    assert not await delete_deployed_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )
    dummy_db.delete.assert_not_called()


async def test_admin_delete_all_deployed_ranges(
    mocker: MockerFixture,
) -> None:
    """Test that the delete crud function returns deployed ranges when the user doesn't own the deployed range but is admin."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    # Ensure that User's ID doesn't match the range's owner
    user_id = 1
    dummy_range.owner_id = user_id + 1
    assert user_id != dummy_range.owner_id

    # Ensure that we get the dummy range from the "db"
    dummy_db.get.return_value = dummy_range

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        DeployedRangeHeaderSchema, "model_validate", return_value=dummy_range
    )

    assert await delete_deployed_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=True
    )
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyDeployedRange)

    # Check it was deleted
    dummy_db.delete.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_delete_deployed_range_raises_db_exceptions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the delete crud function for deployed ranges passes on db exceptions and logs them."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    # Ensure that we get the dummy range from "db"
    dummy_db.get.return_value = dummy_range

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await delete_deployed_range(dummy_db, range_id=1, user_id=1, is_admin=True)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_delete_deployed_range_raises_generic_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the delete crud function for deployed ranges passes on generic exceptions and logs them."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    # Ensure that we get the dummy range from "db"
    dummy_db.get.return_value = dummy_range

    # Force a db exception
    test_except_msg = "Fake generic error!"
    dummy_db.flush.side_effect = RuntimeError(test_except_msg)

    with pytest.raises(RuntimeError, match=test_except_msg):
        await delete_deployed_range(dummy_db, range_id=1, user_id=1, is_admin=True)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


# ==================== Permission Integration Tests =====================


class MockPermission(Mock):
    """Mock permission object for testing."""

    def __init__(
        self, user_id: int, permission_type: str, *args: object, **kwargs: object
    ) -> None:
        """Initialize mock permission."""
        super().__init__(*args, **kwargs)
        self.user_id = user_id
        self.permission_type = permission_type


async def test_get_blueprint_range_with_read_permission(mocker: MockerFixture) -> None:
    """Test that users with read permission can access blueprint ranges."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    user_id = 2
    dummy_range.owner_id = 1  # Different owner
    dummy_range.permissions = [MockPermission(user_id, "read")]

    dummy_db.get.return_value = dummy_range
    mock_model_validate = mocker.patch.object(
        BlueprintRangeSchema, "model_validate", return_value=dummy_range
    )

    result = await get_blueprint_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )

    assert result is not None
    mock_model_validate.assert_called_once()


async def test_get_blueprint_range_denied_no_permission(mocker: MockerFixture) -> None:
    """Test that users without permission cannot access blueprint ranges."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    user_id = 2
    dummy_range.owner_id = 1  # Different owner
    dummy_range.permissions = []  # No permissions

    dummy_db.get.return_value = dummy_range
    mock_model_validate = mocker.patch.object(
        BlueprintRangeSchema, "model_validate", return_value=dummy_range
    )

    result = await get_blueprint_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )

    assert result is None
    mock_model_validate.assert_not_called()


async def test_get_deployed_range_with_read_permission(mocker: MockerFixture) -> None:
    """Test that users with read permission can access deployed ranges."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    user_id = 2
    dummy_range.owner_id = 1  # Different owner
    dummy_range.permissions = [MockPermission(user_id, "read")]

    dummy_db.get.return_value = dummy_range
    mock_model_validate = mocker.patch.object(
        DeployedRangeSchema, "model_validate", return_value=dummy_range
    )

    result = await get_deployed_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )

    assert result is not None
    mock_model_validate.assert_called_once()


async def test_get_deployed_range_denied_no_permission(mocker: MockerFixture) -> None:
    """Test that users without permission cannot access deployed ranges."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    user_id = 2
    dummy_range.owner_id = 1  # Different owner
    dummy_range.permissions = []  # No permissions

    dummy_db.get.return_value = dummy_range
    mock_model_validate = mocker.patch.object(
        DeployedRangeSchema, "model_validate", return_value=dummy_range
    )

    result = await get_deployed_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )

    assert result is None
    mock_model_validate.assert_not_called()


async def test_delete_blueprint_range_with_write_permission(
    mocker: MockerFixture,
) -> None:
    """Test that users with write permission can delete blueprint ranges."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    user_id = 2
    dummy_range.owner_id = 1  # Different owner
    dummy_range.permissions = [MockPermission(user_id, "write")]

    dummy_db.get.return_value = dummy_range
    mock_model_validate = mocker.patch.object(
        BlueprintRangeHeaderSchema, "model_validate", return_value=dummy_range
    )

    result = await delete_blueprint_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )

    assert result is not None
    dummy_db.delete.assert_called_once_with(dummy_range)
    mock_model_validate.assert_called_once()


async def test_delete_blueprint_range_denied_no_permission(
    mocker: MockerFixture,
) -> None:
    """Test that users without permission cannot delete blueprint ranges."""
    dummy_db = DummyDB()
    dummy_range = DummyBlueprintRange()

    user_id = 2
    dummy_range.owner_id = 1  # Different owner
    dummy_range.permissions = []  # No permissions

    dummy_db.get.return_value = dummy_range
    mock_model_validate = mocker.patch.object(
        BlueprintRangeHeaderSchema, "model_validate", return_value=dummy_range
    )

    result = await delete_blueprint_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )

    assert result is None
    dummy_db.delete.assert_not_called()
    mock_model_validate.assert_not_called()


async def test_delete_deployed_range_with_write_permission(
    mocker: MockerFixture,
) -> None:
    """Test that users with write permission can delete deployed ranges."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    user_id = 2
    dummy_range.owner_id = 1  # Different owner
    dummy_range.permissions = [MockPermission(user_id, "write")]

    dummy_db.get.return_value = dummy_range
    mock_model_validate = mocker.patch.object(
        DeployedRangeHeaderSchema, "model_validate", return_value=dummy_range
    )

    result = await delete_deployed_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )

    assert result is not None
    dummy_db.delete.assert_called_once_with(dummy_range)
    mock_model_validate.assert_called_once()


async def test_delete_deployed_range_denied_no_permission(
    mocker: MockerFixture,
) -> None:
    """Test that users without permission cannot delete deployed ranges."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    user_id = 2
    dummy_range.owner_id = 1  # Different owner
    dummy_range.permissions = []  # No permissions

    dummy_db.get.return_value = dummy_range
    mock_model_validate = mocker.patch.object(
        DeployedRangeHeaderSchema, "model_validate", return_value=dummy_range
    )

    result = await delete_deployed_range(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )

    assert result is None
    dummy_db.delete.assert_not_called()
    mock_model_validate.assert_not_called()


async def test_get_deployed_range_key_with_execute_permission() -> None:
    """Test that users with execute permission can access deployed range keys."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    user_id = 2
    dummy_range.owner_id = 1  # Different owner
    dummy_range.permissions = [MockPermission(user_id, "execute")]

    dummy_db.get.return_value = dummy_range
    dummy_db.scalar.return_value = "fake_private_key"

    result = await get_deployed_range_key(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )

    assert result is not None
    assert result.range_private_key == "fake_private_key"


async def test_get_deployed_range_key_denied_no_permission() -> None:
    """Test that users without execute permission cannot access deployed range keys."""
    dummy_db = DummyDB()
    dummy_range = DummyDeployedRange()

    user_id = 2
    dummy_range.owner_id = 1  # Different owner
    dummy_range.permissions = []  # No permissions

    dummy_db.get.return_value = dummy_range

    result = await get_deployed_range_key(
        dummy_db, range_id=1, user_id=user_id, is_admin=False
    )

    assert result is None
    dummy_db.scalar.assert_not_called()  # Should not even try to get the key
