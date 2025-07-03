import logging
import random
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError

from src.app.crud.crud_vpcs import (
    build_blueprint_vpc_models,
    build_deployed_vpc_models,
    create_blueprint_vpc,
    delete_blueprint_vpc,
    get_blueprint_vpc,
    get_blueprint_vpc_headers,
)
from src.app.models.vpc_models import BlueprintVPCModel
from src.app.schemas.vpc_schemas import (
    BlueprintVPCCreateSchema,
    BlueprintVPCHeaderSchema,
    BlueprintVPCSchema,
    DeployedVPCCreateSchema,
)
from tests.unit.api.v1.config import (
    valid_blueprint_vpc_create_payload,
    valid_deployed_vpc_data,
)

from .crud_mocks import DummyBlueprintVPC, DummyDB

pytestmark = pytest.mark.unit


# ==================== Blueprints =====================


@pytest.mark.parametrize(
    "is_admin, standalone_only, expect_owner_filter, expect_range_filter",
    [
        (False, True, True, True),
        (True, True, False, True),
        (False, False, True, False),
        (True, False, False, False),
    ],
)
async def test_get_blueprint_vpc_headers_filters(
    is_admin: bool,
    standalone_only: bool,
    expect_owner_filter: bool,
    expect_range_filter: bool,
) -> None:
    """Test the blueprint VPC headers crud function filters results appropriately."""
    dummy_db = DummyDB()

    # Build mock of result.mappings().all()
    mock_sqlalchemy_result = MagicMock(name="SQLAlchemyResult")
    mock_mappings_object = MagicMock(name="MappingsObject")
    mock_mappings_object.all.return_value = []
    mock_sqlalchemy_result.mappings.return_value = mock_mappings_object

    # Configure return of mock result
    dummy_db.execute.return_value = mock_sqlalchemy_result

    user_id = 1
    await get_blueprint_vpc_headers(
        dummy_db, user_id=user_id, is_admin=is_admin, standalone_only=standalone_only
    )

    # Build filter clauses
    ownership_clause = str(BlueprintVPCModel.owner_id == user_id)
    standalone_clause = str(BlueprintVPCModel.range_id.is_(None))
    where_clause = str(dummy_db.execute.call_args[0][0].whereclause)

    assert (ownership_clause in where_clause) == expect_owner_filter
    assert (standalone_clause in where_clause) == expect_range_filter


async def test_no_get_unauthorized_blueprint_vpcs() -> None:
    """Test that the crud function returns none when the user doesn't own the VPC blueprint."""
    dummy_db = DummyDB()
    dummy_vpc = DummyBlueprintVPC()

    # Ensure that User's ID doesn't match the VPC's owner
    user_id = 1
    dummy_vpc.owner_id = user_id + 1
    assert user_id != dummy_vpc.owner_id

    # Ensure that we get the dummy VPC from the "db"
    dummy_db.get.return_value = dummy_vpc

    assert not await get_blueprint_vpc(
        dummy_db, vpc_id=1, user_id=user_id, is_admin=False
    )


async def test_admin_get_all_blueprint_vpcs(
    mocker: MockerFixture,
) -> None:
    """Test that the crud function returns blueprint VPCs when the user doesn't own the VPC blueprint but is admin."""
    dummy_db = DummyDB()
    dummy_vpc = DummyBlueprintVPC()

    # Ensure that User's ID doesn't match the VPC's owner
    user_id = 1
    dummy_vpc.owner_id = user_id + 1
    assert user_id != dummy_vpc.owner_id

    # Ensure that we get the dummy VPC from the "db"
    dummy_db.get.return_value = dummy_vpc

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintVPCSchema, "model_validate", return_value=dummy_vpc
    )

    assert await get_blueprint_vpc(dummy_db, vpc_id=1, user_id=user_id, is_admin=True)
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintVPC)


async def test_get_non_existent_blueprint_vpc() -> None:
    """Test that the crud function returns None when the blueprint VPC doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the VPC doesn't exist
    dummy_db.get.return_value = None

    assert not await get_blueprint_vpc(dummy_db, vpc_id=1, user_id=-1)


async def test_build_blueprint_vpc_models() -> None:
    """Test that the we can build blueprint VPC models from blueprint VPC creation schemas."""
    blueprint_vpc_create_schema = BlueprintVPCCreateSchema.model_validate(
        valid_blueprint_vpc_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    blueprint_vpc_models = build_blueprint_vpc_models(
        [blueprint_vpc_create_schema], user_id
    )

    assert len(blueprint_vpc_models) == 1
    assert blueprint_vpc_models[0].owner_id == user_id
    assert blueprint_vpc_models[0].name == blueprint_vpc_create_schema.name


async def test_create_blueprint_vpcs_too_many_models(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function for blueprint VPCs raises an exception if we get back more models than input schemas."""
    dummy_db = DummyDB()

    blueprint_vpc_create_schema = BlueprintVPCCreateSchema.model_validate(
        valid_blueprint_vpc_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Return too many "models"
    mocker.patch(
        "src.app.crud.crud_vpcs.build_blueprint_vpc_models",
        return_value=["fake", "list"],
    )

    with pytest.raises(RuntimeError, match="VPC blueprint models from a single schema"):
        await create_blueprint_vpc(
            dummy_db, blueprint_vpc_create_schema, user_id, range_id=None
        )


async def test_create_blueprint_vpc_raises_db_exceptions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the creation crud function for blueprint VPCs passes on db exceptions and logs them."""
    dummy_db = DummyDB()

    blueprint_vpc_create_schema = BlueprintVPCCreateSchema.model_validate(
        valid_blueprint_vpc_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await create_blueprint_vpc(
            dummy_db, blueprint_vpc_create_schema, user_id, range_id=None
        )

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_create_blueprint_vpc_raises_generic_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the creation crud function for blueprint VPCs passes on generic exceptions and logs them."""
    dummy_db = DummyDB()

    blueprint_vpc_create_schema = BlueprintVPCCreateSchema.model_validate(
        valid_blueprint_vpc_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Force a db exception
    test_except_msg = "Fake generic error!"
    dummy_db.flush.side_effect = RuntimeError(test_except_msg)

    with pytest.raises(RuntimeError, match=test_except_msg):
        await create_blueprint_vpc(
            dummy_db, blueprint_vpc_create_schema, user_id, range_id=None
        )

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_create_blueprint_vpc_non_standalone(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function returns non-standalone blueprint VPCs."""
    dummy_db = DummyDB()
    dummy_vpc = DummyBlueprintVPC()

    # Build a dummy VPC
    mocker.patch(
        "src.app.crud.crud_vpcs.build_blueprint_vpc_models",
        return_value=[dummy_vpc],
    )

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintVPCHeaderSchema, "model_validate", return_value=dummy_vpc
    )

    user_id = random.randint(1, 100)  # noqa: S311
    range_id = random.randint(1, 100)  # noqa: S311

    # Clear any range ID
    dummy_vpc.range_id = None

    assert await create_blueprint_vpc(dummy_db, dummy_vpc, user_id, range_id=range_id)
    assert dummy_vpc.range_id == range_id

    # Check we make it to the end
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintVPC)

    # Check we save it to the database
    dummy_db.add.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_create_blueprint_vpc_standalone(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function returns standalone blueprint VPCs."""
    dummy_db = DummyDB()
    dummy_vpc = DummyBlueprintVPC()

    # Build a dummy VPC
    mocker.patch(
        "src.app.crud.crud_vpcs.build_blueprint_vpc_models",
        return_value=[dummy_vpc],
    )

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintVPCHeaderSchema, "model_validate", return_value=dummy_vpc
    )

    range_id = random.randint(1, 100)  # noqa: S311
    user_id = random.randint(1, 100)  # noqa: S311

    # Test that the range_id doesn't change since it's standalone
    dummy_vpc.range_id = range_id

    assert await create_blueprint_vpc(dummy_db, dummy_vpc, user_id, range_id=None)
    assert dummy_vpc.range_id == range_id

    # Check we make it to the end
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintVPC)

    # Check we save it to the database
    dummy_db.add.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_delete_non_existent_blueprint_vpc() -> None:
    """Test that the delete crud function returns None when the blueprint VPC doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the VPC doesn't exist
    dummy_db.get.return_value = None

    assert not await delete_blueprint_vpc(dummy_db, vpc_id=1, user_id=-1)
    dummy_db.delete.assert_not_called()


async def test_no_delete_unauthorized_blueprint_vpcs() -> None:
    """Test that the delete crud function returns none when the user doesn't own the VPC blueprint."""
    dummy_db = DummyDB()
    dummy_vpc = DummyBlueprintVPC()

    # Ensure that User's ID doesn't match the VPC's owner
    user_id = 1
    dummy_vpc.owner_id = user_id + 1
    assert user_id != dummy_vpc.owner_id

    # Ensure that we get the dummy VPC from the "db"
    dummy_db.get.return_value = dummy_vpc

    assert not await delete_blueprint_vpc(
        dummy_db, vpc_id=1, user_id=user_id, is_admin=False
    )
    dummy_db.delete.assert_not_called()


async def test_admin_delete_all_blueprint_vpcs(
    mocker: MockerFixture,
) -> None:
    """Test that the delete crud function returns blueprint VPCs when the user doesn't own the VPC blueprint but is admin."""
    dummy_db = DummyDB()
    dummy_vpc = DummyBlueprintVPC()

    # Ensure that User's ID doesn't match the VPC's owner
    user_id = 1
    dummy_vpc.owner_id = user_id + 1
    assert user_id != dummy_vpc.owner_id

    # Ensure that we get the dummy VPC from the "db"
    dummy_db.get.return_value = dummy_vpc

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintVPCHeaderSchema, "model_validate", return_value=dummy_vpc
    )

    assert await delete_blueprint_vpc(
        dummy_db, vpc_id=1, user_id=user_id, is_admin=True
    )
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintVPC)

    # Check it was deleted
    dummy_db.delete.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_delete_blueprint_vpc_raises_db_exceptions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the delete crud function for blueprint VPCs passes on db exceptions and logs them."""
    dummy_db = DummyDB()
    dummy_vpc = DummyBlueprintVPC()

    # Ensure that we get the dummy VPC from "db"
    dummy_db.get.return_value = dummy_vpc

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await delete_blueprint_vpc(dummy_db, vpc_id=1, user_id=1, is_admin=True)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_delete_blueprint_vpc_raises_generic_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the delete crud function for blueprint VPCs passes on generic exceptions and logs them."""
    dummy_db = DummyDB()
    dummy_vpc = DummyBlueprintVPC()

    # Ensure that we get the dummy VPC from "db"
    dummy_db.get.return_value = dummy_vpc

    # Force a db exception
    test_except_msg = "Fake generic error!"
    dummy_db.flush.side_effect = RuntimeError(test_except_msg)

    with pytest.raises(RuntimeError, match=test_except_msg):
        await delete_blueprint_vpc(dummy_db, vpc_id=1, user_id=1, is_admin=True)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize(
    "is_admin",
    [True, False],
)
async def test_no_delete_non_standalone_blueprint_vpcs(
    monkeypatch: pytest.MonkeyPatch,
    is_admin: bool,
) -> None:
    """Test that attempting to delete a non-standalone blueprint VPC fails."""
    dummy_db = DummyDB()

    # Patch VPC model is_standalone() method to always return False
    dummy_vpc = DummyBlueprintVPC()
    monkeypatch.setattr(dummy_vpc, "is_standalone", lambda: False)

    # Ensure that we get the dummy VPC from the "db"
    dummy_db.get.return_value = dummy_vpc

    assert not await delete_blueprint_vpc(dummy_db, 1, 100, is_admin=is_admin)

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.flush.assert_not_called()


# ==================== Deployed (Instances) =====================


async def test_build_deployed_vpc_models() -> None:
    """Test that the we can build deployed VPC models from VPC creation schemas."""
    deployed_vpc_create_schema = DeployedVPCCreateSchema.model_validate(
        valid_deployed_vpc_data, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    deployed_vpc_models = build_deployed_vpc_models(
        [deployed_vpc_create_schema], user_id
    )

    assert len(deployed_vpc_models) == 1
    assert deployed_vpc_models[0].owner_id == user_id
    assert deployed_vpc_models[0].resource_id == deployed_vpc_create_schema.resource_id
