import logging
import random
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.exc import SQLAlchemyError

from src.app.crud.crud_hosts import (
    build_blueprint_host_models,
    build_deployed_host_models,
    create_blueprint_host,
    delete_blueprint_host,
    get_blueprint_host,
    get_blueprint_host_headers,
)
from src.app.models.host_models import BlueprintHostModel
from src.app.schemas.host_schemas import (
    BlueprintHostCreateSchema,
    BlueprintHostSchema,
    DeployedHostCreateSchema,
)
from tests.unit.api.v1.config import (
    valid_blueprint_host_create_payload,
    valid_deployed_host_data,
)

from .crud_mocks import DummyBlueprintHost, DummyDB

pytestmark = pytest.mark.unit


# ==================== Blueprints =====================


@pytest.mark.parametrize(
    "is_admin, standalone_only, expect_owner_filter, expect_subnet_filter",
    [
        (False, True, True, True),
        (True, True, False, True),
        (False, False, True, False),
        (True, False, False, False),
    ],
)
async def test_get_blueprint_host_headers_filters(
    is_admin: bool,
    standalone_only: bool,
    expect_owner_filter: bool,
    expect_subnet_filter: bool,
) -> None:
    """Test the blueprint host headers crud function filters results appropriately."""
    dummy_db = DummyDB()

    # Build mock of result.mappings().all()
    mock_sqlalchemy_result = MagicMock(name="SQLAlchemyResult")
    mock_mappings_object = MagicMock(name="MappingsObject")
    mock_mappings_object.all.return_value = []
    mock_sqlalchemy_result.mappings.return_value = mock_mappings_object

    # Configure return of mock result
    dummy_db.execute.return_value = mock_sqlalchemy_result

    user_id = 1
    await get_blueprint_host_headers(
        dummy_db, user_id=user_id, is_admin=is_admin, standalone_only=standalone_only
    )

    # Build filter clauses
    ownership_clause = str(BlueprintHostModel.owner_id == user_id)
    standalone_clause = str(BlueprintHostModel.subnet_id.is_(None))
    where_clause = str(dummy_db.execute.call_args[0][0].whereclause)

    assert (ownership_clause in where_clause) == expect_owner_filter
    assert (standalone_clause in where_clause) == expect_subnet_filter


async def test_no_get_unauthorized_blueprint_hosts() -> None:
    """Test that the crud function returns none when the user doesn't own the host blueprint."""
    dummy_db = DummyDB()
    dummy_host = DummyBlueprintHost()

    # Ensure that User's ID doesn't match the host's owner
    user_id = 1
    dummy_host.owner_id = user_id + 1
    assert user_id != dummy_host.owner_id

    # Ensure that we get the dummy host from the "db"
    dummy_db.get.return_value = dummy_host

    assert not await get_blueprint_host(
        dummy_db, host_id=1, user_id=user_id, is_admin=False
    )


async def test_admin_get_all_blueprint_hosts(
    mocker: MockerFixture,
) -> None:
    """Test that the crud function returns blueprint hosts when the user doesn't own the host blueprint but is admin."""
    dummy_db = DummyDB()
    dummy_host = DummyBlueprintHost()

    # Ensure that User's ID doesn't match the host's owner
    user_id = 1
    dummy_host.owner_id = user_id + 1
    assert user_id != dummy_host.owner_id

    # Ensure that we get the dummy host from the "db"
    dummy_db.get.return_value = dummy_host

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintHostSchema, "model_validate", return_value=dummy_host
    )

    assert await get_blueprint_host(dummy_db, host_id=1, user_id=user_id, is_admin=True)
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintHost)


async def test_get_non_existent_blueprint_host() -> None:
    """Test that the crud function returns None when the blueprint host doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the host doesn't exist
    dummy_db.get.return_value = None

    assert not await get_blueprint_host(dummy_db, host_id=1, user_id=-1)


async def test_build_blueprint_host_models() -> None:
    """Test that the we can build blueprint host models from blueprint host creation schemas."""
    blueprint_host_create_schema = BlueprintHostCreateSchema.model_validate(
        valid_blueprint_host_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    blueprint_host_models = build_blueprint_host_models(
        [blueprint_host_create_schema], user_id
    )

    assert len(blueprint_host_models) == 1
    assert blueprint_host_models[0].owner_id == user_id
    assert blueprint_host_models[0].hostname == blueprint_host_create_schema.hostname


async def test_create_blueprint_host_too_many_models(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function for blueprint hosts raises an exception if we get back more models than input schemas."""
    dummy_db = DummyDB()

    blueprint_host_create_schema = BlueprintHostCreateSchema.model_validate(
        valid_blueprint_host_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Return too many "models"
    mocker.patch(
        "src.app.crud.crud_hosts.build_blueprint_host_models",
        return_value=["fake", "list"],
    )

    with pytest.raises(
        RuntimeError, match="host blueprint models from a single schema"
    ):
        await create_blueprint_host(
            dummy_db, blueprint_host_create_schema, user_id, subnet_id=None
        )


async def test_create_blueprint_host_raises_db_exceptions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the creation crud function for blueprint hosts passes on db exceptions and logs them."""
    dummy_db = DummyDB()

    blueprint_host_create_schema = BlueprintHostCreateSchema.model_validate(
        valid_blueprint_host_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await create_blueprint_host(
            dummy_db, blueprint_host_create_schema, user_id, subnet_id=None
        )

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_create_blueprint_host_raises_generic_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the creation crud function for blueprint hosts passes on generic exceptions and logs them."""
    dummy_db = DummyDB()

    blueprint_host_create_schema = BlueprintHostCreateSchema.model_validate(
        valid_blueprint_host_create_payload, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    # Force a db exception
    test_except_msg = "Fake generic error!"
    dummy_db.flush.side_effect = RuntimeError(test_except_msg)

    with pytest.raises(RuntimeError, match=test_except_msg):
        await create_blueprint_host(
            dummy_db, blueprint_host_create_schema, user_id, subnet_id=None
        )

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_create_blueprint_host_non_standalone(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function returns non-standalone blueprint hosts."""
    dummy_db = DummyDB()
    dummy_host = DummyBlueprintHost()

    # Build a dummy host
    mocker.patch(
        "src.app.crud.crud_hosts.build_blueprint_host_models",
        return_value=[dummy_host],
    )

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintHostSchema, "model_validate", return_value=dummy_host
    )

    user_id = random.randint(1, 100)  # noqa: S311
    subnet_id = random.randint(1, 100)  # noqa: S311

    # Clear any subnet ID
    dummy_host.subnet_id = None

    assert await create_blueprint_host(
        dummy_db, dummy_host, user_id, subnet_id=subnet_id
    )
    assert dummy_host.subnet_id == subnet_id

    # Check we make it to the end
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintHost)

    # Check we save it to the database
    dummy_db.add.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_create_blueprint_host_standalone(
    mocker: MockerFixture,
) -> None:
    """Test that the creation crud function returns standalone blueprint hosts."""
    dummy_db = DummyDB()
    dummy_host = DummyBlueprintHost()

    # Build a dummy host
    mocker.patch(
        "src.app.crud.crud_hosts.build_blueprint_host_models",
        return_value=[dummy_host],
    )

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintHostSchema, "model_validate", return_value=dummy_host
    )

    subnet_id = random.randint(1, 100)  # noqa: S311
    user_id = random.randint(1, 100)  # noqa: S311

    # Test that the subnet_id doesn't change since it's standalone
    dummy_host.subnet_id = subnet_id

    assert await create_blueprint_host(dummy_db, dummy_host, user_id, subnet_id=None)
    assert dummy_host.subnet_id == subnet_id

    # Check we make it to the end
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintHost)

    # Check we save it to the database
    dummy_db.add.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_delete_non_existent_blueprint_host() -> None:
    """Test that the delete crud function returns None when the blueprint host doesn't exist in the database."""
    dummy_db = DummyDB()

    # Ensure that the "db" returns nothing like the host doesn't exist
    dummy_db.get.return_value = None

    assert not await delete_blueprint_host(dummy_db, host_id=1, user_id=-1)
    dummy_db.delete.assert_not_called()


async def test_no_delete_unauthorized_blueprint_hosts() -> None:
    """Test that the delete crud function returns none when the user doesn't own the host blueprint."""
    dummy_db = DummyDB()
    dummy_host = DummyBlueprintHost()

    # Ensure that User's ID doesn't match the host's owner
    user_id = 1
    dummy_host.owner_id = user_id + 1
    assert user_id != dummy_host.owner_id

    # Ensure that we get the dummy host from the "db"
    dummy_db.get.return_value = dummy_host

    assert not await delete_blueprint_host(
        dummy_db, host_id=1, user_id=user_id, is_admin=False
    )
    dummy_db.delete.assert_not_called()


async def test_admin_delete_all_blueprint_hosts(
    mocker: MockerFixture,
) -> None:
    """Test that the delete crud function returns blueprint hosts when the user doesn't own the host blueprint but is admin."""
    dummy_db = DummyDB()
    dummy_host = DummyBlueprintHost()

    # Ensure that User's ID doesn't match the host's owner
    user_id = 1
    dummy_host.owner_id = user_id + 1
    assert user_id != dummy_host.owner_id

    # Ensure that we get the dummy host from the "db"
    dummy_db.get.return_value = dummy_host

    # Patch pydantic validation
    mock_model_validate = mocker.patch.object(
        BlueprintHostSchema, "model_validate", return_value=dummy_host
    )

    assert await delete_blueprint_host(
        dummy_db, host_id=1, user_id=user_id, is_admin=True
    )
    mock_model_validate.assert_called_once()
    args, _ = mock_model_validate.call_args
    assert isinstance(args[0], DummyBlueprintHost)

    # Check it was deleted
    dummy_db.delete.assert_called_once()
    dummy_db.flush.assert_called_once()


async def test_delete_blueprint_host_raises_db_exceptions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the delete crud function for blueprint hosts passes on db exceptions and logs them."""
    dummy_db = DummyDB()
    dummy_host = DummyBlueprintHost()

    # Ensure that we get the dummy host from "db"
    dummy_db.get.return_value = dummy_host

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await delete_blueprint_host(dummy_db, host_id=1, user_id=1, is_admin=True)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_delete_blueprint_host_raises_generic_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the delete crud function for blueprint hosts passes on generic exceptions and logs them."""
    dummy_db = DummyDB()
    dummy_host = DummyBlueprintHost()

    # Ensure that we get the dummy host from "db"
    dummy_db.get.return_value = dummy_host

    # Force a db exception
    test_except_msg = "Fake generic error!"
    dummy_db.flush.side_effect = RuntimeError(test_except_msg)

    with pytest.raises(RuntimeError, match=test_except_msg):
        await delete_blueprint_host(dummy_db, host_id=1, user_id=1, is_admin=True)

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
async def test_no_delete_non_standalone_blueprint_hosts(
    monkeypatch: pytest.MonkeyPatch,
    is_admin: bool,
) -> None:
    """Test that attempting to delete a non-standalone blueprint host fails."""
    dummy_db = DummyDB()

    # Patch host model is_standalone() method to always return False
    dummy_host = DummyBlueprintHost()
    monkeypatch.setattr(dummy_host, "is_standalone", lambda: False)

    # Ensure that we get the dummy host from the "db"
    dummy_db.get.return_value = dummy_host

    assert not await delete_blueprint_host(dummy_db, 1, 100, is_admin=is_admin)

    # Verify that delete and commit were not called
    dummy_db.delete.assert_not_called()
    dummy_db.flush.assert_not_called()


# ==================== Deployed (Instances) =====================


async def test_build_deployed_host_models() -> None:
    """Test that the we can build deployed host models from host creation schemas."""
    deployed_host_create_schema = DeployedHostCreateSchema.model_validate(
        valid_deployed_host_data, from_attributes=True
    )
    user_id = random.randint(1, 100)  # noqa: S311

    deployed_host_models = build_deployed_host_models(
        [deployed_host_create_schema], user_id
    )

    assert len(deployed_host_models) == 1
    assert deployed_host_models[0].owner_id == user_id
    assert (
        deployed_host_models[0].resource_id == deployed_host_create_schema.resource_id
    )
