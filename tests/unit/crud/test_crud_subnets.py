import logging
import random
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError

from src.app.crud.crud_subnets import (
    build_blueprint_subnet_models,
    build_deployed_subnet_models,
    create_blueprint_subnet,
    delete_blueprint_subnet,
    get_blueprint_subnet,
    get_blueprint_subnet_headers,
)
from src.app.models.subnet_models import BlueprintSubnetModel
from src.app.schemas.subnet_schemas import (
    BlueprintSubnetCreateSchema,
    BlueprintSubnetHeaderSchema,
    BlueprintSubnetSchema,
    DeployedSubnetCreateSchema,
)
from tests.unit.api.v1.config import (
    valid_blueprint_subnet_create_payload,
    valid_deployed_subnet_data,
)

from .crud_mocks import DummyBlueprintSubnet, DummyDB

# ==================== Blueprints =====================


@pytest.mark.parametrize(
    "is_admin, standalone_only, expect_owner_filter, expect_vpc_filter",
    [
        (False, True, True, True),
        (True, True, False, True),
        (False, False, True, False),
        (True, False, False, False),
    ],
)
async def test_get_blueprint_subnet_headers_filters(
    is_admin: bool,
    standalone_only: bool,
    expect_owner_filter: bool,
    expect_vpc_filter: bool,
) -> None:
    """Test the blueprint subnets headers crud function filters results appropriately."""
    dummy_db = DummyDB()

    # Build mock of result.mappings().all()
    mock_sqlalchemy_result = MagicMock(name="SQLAlchemyResult")
    mock_mappings_object = MagicMock(name="MappingsObject")
    mock_mappings_object.all.return_value = []
    mock_sqlalchemy_result.mappings.return_value = mock_mappings_object

    # Configure return of mock result
    dummy_db.execute.return_value = mock_sqlalchemy_result

    user_id = 1
    await get_blueprint_subnet_headers(
        dummy_db, user_id=user_id, is_admin=is_admin, standalone_only=standalone_only
    )

    # Build filter clauses
    ownership_clause = str(BlueprintSubnetModel.owner_id == user_id)
    standalone_clause = str(BlueprintSubnetModel.vpc_id.is_(None))
    where_clause = str(dummy_db.execute.call_args[0][0].whereclause)

    assert (ownership_clause in where_clause) == expect_owner_filter
    assert (standalone_clause in where_clause) == expect_vpc_filter


async def test_no_get_unauthorized_blueprint_subnets() -> None:
    """Test that the crud function returns none when the user doesn't own the subnet blueprint."""
    dummy_db = DummyDB()
    dummy_subnet = DummyBlueprintSubnet()

    # Ensure that User's ID doesn't match the subnets's owner
    user_id = 1
    dummy_subnet.owner_id = user_id + 1
    assert user_id != dummy_subnet.owner_id

    # Ensure that we get the dummy subnet from the "db"
    dummy_db.get.return_value = dummy_subnet

    assert not await get_blueprint_subnet(
        dummy_db, subnet_id=1, user_id=user_id, is_admin=False
    )


async def test_admin_get_all_blueprint_subnets(
    mocker: MockerFixture,
) -> None:
    """Test that the crud function returns blueprint subnets when the user doesn't own the subnet blueprint but is admin."""
    dummy_db = DummyDB()
    dummy_subnet = DummyBlueprintSubnet()

    # Ensure that User's ID doesn't match the subnet's owner
    user_id = 1
    dummy_subnet.owner_id = user_id + 1
    assert user_id != dummy_subnet.owner_id

    # Ensure that we get the dummy subnet from the "db"
    dummy_db.get.return_value = dummy_subnet

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintSubnetSchema, "model_validate", return_value=dummy_subnet
    )

    assert await get_blueprint_subnet(
        dummy_db, subnet_id=1, user_id=user_id, is_admin=True
    )
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintSubnet)


async def test_get_non_existent_subnet_host() -> None:
    """Test that the crud function returns None when the blueprint subnet doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the host doesn't exist
    dummy_db.get.return_value = None

    assert not await get_blueprint_subnet(dummy_db, subnet_id=1, user_id=-1)


async def test_build_blueprint_subnet_models() -> None:
    """Test that the we can build blueprint subnet models from blueprint subnet creation schemas."""
    blueprint_subnet_create_schema = BlueprintSubnetCreateSchema.model_validate(
        valid_blueprint_subnet_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    blueprint_subnet_models = build_blueprint_subnet_models(
        [blueprint_subnet_create_schema], user_id
    )

    assert len(blueprint_subnet_models) == 1
    assert blueprint_subnet_models[0].owner_id == user_id
    assert blueprint_subnet_models[0].name == blueprint_subnet_create_schema.name


async def test_create_blueprint_subnet_too_many_models(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function for blueprint subnets raises an exception if we get back more models than input schemas."""
    dummy_db = DummyDB()

    blueprint_subnet_create_schema = BlueprintSubnetCreateSchema.model_validate(
        valid_blueprint_subnet_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Return too many "models"
    mocker.patch(
        "src.app.crud.crud_subnets.build_blueprint_subnet_models",
        return_value=["fake", "list"],
    )

    with pytest.raises(
        RuntimeError, match="subnet blueprint models from a single schema"
    ):
        await create_blueprint_subnet(
            dummy_db, blueprint_subnet_create_schema, user_id, vpc_id=None
        )


async def test_create_blueprint_subnet_raises_db_exceptions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the creation crud function for blueprint subnets passes on db exceptions and logs them."""
    dummy_db = DummyDB()

    blueprint_subnet_create_schema = BlueprintSubnetCreateSchema.model_validate(
        valid_blueprint_subnet_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await create_blueprint_subnet(
            dummy_db, blueprint_subnet_create_schema, user_id, vpc_id=None
        )

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_create_blueprint_subnet_raises_generic_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the creation crud function for blueprint subnets passes on generic exceptions and logs them."""
    dummy_db = DummyDB()

    blueprint_subnet_create_schema = BlueprintSubnetCreateSchema.model_validate(
        valid_blueprint_subnet_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Force a db exception
    test_except_msg = "Fake generic error!"
    dummy_db.flush.side_effect = RuntimeError(test_except_msg)

    with pytest.raises(RuntimeError, match=test_except_msg):
        await create_blueprint_subnet(
            dummy_db, blueprint_subnet_create_schema, user_id, vpc_id=None
        )

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_create_blueprint_subnet_non_standalone(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function returns non-standalone blueprint subnets."""
    dummy_db = DummyDB()
    dummy_subnet = DummyBlueprintSubnet()

    # Build a dummy subnet
    mocker.patch(
        "src.app.crud.crud_subnets.build_blueprint_subnet_models",
        return_value=[dummy_subnet],
    )

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintSubnetHeaderSchema, "model_validate", return_value=dummy_subnet
    )

    user_id = random.randint(1, 100)  # noqa: S311
    vpc_id = random.randint(1, 100)  # noqa: S311

    # Clear any VPC ID
    dummy_subnet.vpc_id = None

    assert await create_blueprint_subnet(dummy_db, dummy_subnet, user_id, vpc_id=vpc_id)
    assert dummy_subnet.vpc_id == vpc_id

    # Check we make it to the end
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintSubnet)

    # Check we save it to the database
    dummy_db.add.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_create_blueprint_subnet_standalone(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function returns standalone blueprint subnets."""
    dummy_db = DummyDB()
    dummy_subnet = DummyBlueprintSubnet()

    # Build a dummy subnet
    mocker.patch(
        "src.app.crud.crud_subnets.build_blueprint_subnet_models",
        return_value=[dummy_subnet],
    )

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintSubnetHeaderSchema, "model_validate", return_value=dummy_subnet
    )

    vpc_id = random.randint(1, 100)  # noqa: S311
    user_id = random.randint(1, 100)  # noqa: S311

    # Test that the vpc_id doesn't change since it's standalone
    dummy_subnet.vpc_id = vpc_id

    assert await create_blueprint_subnet(dummy_db, dummy_subnet, user_id, vpc_id=None)
    assert dummy_subnet.vpc_id == vpc_id

    # Check we make it to the end
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintSubnet)

    # Check we save it to the database
    dummy_db.add.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_delete_non_existent_blueprint_subnet() -> None:
    """Test that the delete crud function returns None when the blueprint subnet doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the subnet doesn't exist
    dummy_db.get.return_value = None

    assert not await delete_blueprint_subnet(dummy_db, subnet_id=1, user_id=-1)
    dummy_db.delete.assert_not_called()


async def test_no_delete_unauthorized_blueprint_subnets() -> None:
    """Test that the delete crud function returns none when the user doesn't own the subnet blueprint."""
    dummy_db = DummyDB()
    dummy_subnet = DummyBlueprintSubnet()

    # Ensure that User's ID doesn't match the subnet's owner
    user_id = 1
    dummy_subnet.owner_id = user_id + 1
    assert user_id != dummy_subnet.owner_id

    # Ensure that we get the dummy subnet from the "db"
    dummy_db.get.return_value = dummy_subnet

    assert not await delete_blueprint_subnet(
        dummy_db, subnet_id=1, user_id=user_id, is_admin=False
    )
    dummy_db.delete.assert_not_called()


async def test_admin_delete_all_blueprint_subnets(
    mocker: MockerFixture,
) -> None:
    """Test that the delete crud function returns blueprint subnets when the user doesn't own the subnet blueprint but is admin."""
    dummy_db = DummyDB()
    dummy_subnet = DummyBlueprintSubnet()

    # Ensure that User's ID doesn't match the subnet's owner
    user_id = 1
    dummy_subnet.owner_id = user_id + 1
    assert user_id != dummy_subnet.owner_id

    # Ensure that we get the dummy subnet from the "db"
    dummy_db.get.return_value = dummy_subnet

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintSubnetHeaderSchema, "model_validate", return_value=dummy_subnet
    )

    assert await delete_blueprint_subnet(
        dummy_db, subnet_id=1, user_id=user_id, is_admin=True
    )
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintSubnet)

    # Check it was deleted
    dummy_db.delete.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_delete_blueprint_subnet_raises_db_exceptions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the delete crud function for blueprint subnets passes on db exceptions and logs them."""
    dummy_db = DummyDB()
    dummy_subnet = DummyBlueprintSubnet()

    # Ensure that we get the dummy subnet from "db"
    dummy_db.get.return_value = dummy_subnet

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await delete_blueprint_subnet(dummy_db, subnet_id=1, user_id=1, is_admin=True)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_delete_blueprint_subnet_raises_generic_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the delete crud function for blueprint subnets passes on generic exceptions and logs them."""
    dummy_db = DummyDB()
    dummy_subnet = DummyBlueprintSubnet()

    # Ensure that we get the dummy subnet from "db"
    dummy_db.get.return_value = dummy_subnet

    # Force a db exception
    test_except_msg = "Fake generic error!"
    dummy_db.flush.side_effect = RuntimeError(test_except_msg)

    with pytest.raises(RuntimeError, match=test_except_msg):
        await delete_blueprint_subnet(dummy_db, subnet_id=1, user_id=1, is_admin=True)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_no_delete_non_standalone_blueprint_subnets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that attempting to delete a non-standalone blueprint subnet fails."""
    dummy_db = DummyDB()

    # Patch subnet model is_standalone() method to always return False
    dummy_subnet = DummyBlueprintSubnet()
    monkeypatch.setattr(dummy_subnet, "is_standalone", lambda: False)

    # Ensure that we get the dummy subnet from the "db"
    dummy_db.get.return_value = dummy_subnet

    assert not await delete_blueprint_subnet(dummy_db, 1, 100)

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.flush.assert_not_called()


# ==================== Deployed (Instances) =====================


async def test_build_deployed_subnet_models() -> None:
    """Test that the we can build deployed subnet models from subnet creation schemas."""
    deployed_subnet_create_schema = DeployedSubnetCreateSchema.model_validate(
        valid_deployed_subnet_data, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    deployed_subnet_models = build_deployed_subnet_models(
        [deployed_subnet_create_schema], user_id
    )

    assert len(deployed_subnet_models) == 1
    assert deployed_subnet_models[0].owner_id == user_id
    assert (
        deployed_subnet_models[0].resource_id
        == deployed_subnet_create_schema.resource_id
    )
