import logging
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.app.crud.crud_permissions import (
    grant_blueprint_permission,
    grant_deployed_permission,
    revoke_blueprint_permission,
    revoke_deployed_permission,
)
from src.app.enums.permissions import (
    BlueprintPermissionType,
    DeployedRangePermissionType,
)
from src.app.models.permission_models import (
    BlueprintRangePermissionModel,
    DeployedRangePermissionModel,
)

from .crud_mocks import DummyDB

# ==================== Grant Permissions =====================


@pytest.mark.parametrize(
    "range_type,permission_type,expected_model_class,user_id",
    [
        ("blueprint", BlueprintPermissionType.READ, BlueprintRangePermissionModel, 2),
        ("blueprint", BlueprintPermissionType.WRITE, BlueprintRangePermissionModel, 3),
        ("deployed", DeployedRangePermissionType.READ, DeployedRangePermissionModel, 2),
        (
            "deployed",
            DeployedRangePermissionType.WRITE,
            DeployedRangePermissionModel,
            3,
        ),
        (
            "deployed",
            DeployedRangePermissionType.EXECUTE,
            DeployedRangePermissionModel,
            4,
        ),
    ],
)
async def test_grant_permission(
    range_type: str,
    permission_type: BlueprintPermissionType | DeployedRangePermissionType,
    expected_model_class: type,
    user_id: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test granting permissions to ranges."""
    dummy_db = DummyDB()

    mock_range = Mock()
    mock_range.owner_id = 1
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_range
    dummy_db.execute.return_value = mock_result

    range_id = 1
    requesting_user_id = 1  # Owner

    with caplog.at_level(logging.DEBUG):
        if range_type == "blueprint":
            result = await grant_blueprint_permission(
                dummy_db, range_id, user_id, permission_type, requesting_user_id
            )
        else:
            result = await grant_deployed_permission(
                dummy_db, range_id, user_id, permission_type, requesting_user_id
            )

    dummy_db.add.assert_called_once()
    added_permission = dummy_db.add.call_args[0][0]
    assert isinstance(added_permission, expected_model_class)
    assert added_permission.user_id == user_id
    assert added_permission.permission_type == permission_type

    if range_type == "blueprint":
        assert added_permission.blueprint_range_id == range_id
    else:
        assert added_permission.deployed_range_id == range_id

    dummy_db.flush.assert_called_once()
    dummy_db.refresh.assert_called_once_with(added_permission)
    assert result == added_permission


@pytest.mark.parametrize(
    "range_type,permission_type",
    [
        ("blueprint", BlueprintPermissionType.READ),
        ("deployed", DeployedRangePermissionType.READ),
    ],
)
async def test_grant_permission_db_error(
    range_type: str,
    permission_type: BlueprintPermissionType | DeployedRangePermissionType,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that grant permission functions handle database errors."""
    dummy_db = DummyDB()

    mock_range = Mock()
    mock_range.owner_id = 1
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_range
    dummy_db.execute.return_value = mock_result

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    requesting_user_id = 1  # Owner

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        if range_type == "blueprint":
            await grant_blueprint_permission(
                dummy_db, 1, 2, permission_type, requesting_user_id
            )
        else:
            await grant_deployed_permission(
                dummy_db, 1, 2, permission_type, requesting_user_id
            )

    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


# ==================== Revoke Permissions =====================


@pytest.mark.parametrize(
    "range_type,permission_type,expected_model_class,permission_exists",
    [
        (
            "blueprint",
            BlueprintPermissionType.READ,
            BlueprintRangePermissionModel,
            True,
        ),
        (
            "blueprint",
            BlueprintPermissionType.READ,
            BlueprintRangePermissionModel,
            False,
        ),
        (
            "deployed",
            DeployedRangePermissionType.EXECUTE,
            DeployedRangePermissionModel,
            True,
        ),
        (
            "deployed",
            DeployedRangePermissionType.WRITE,
            DeployedRangePermissionModel,
            False,
        ),
    ],
)
async def test_revoke_permission(
    range_type: str,
    permission_type: BlueprintPermissionType | DeployedRangePermissionType,
    expected_model_class: type,
    permission_exists: bool,
) -> None:
    """Test revoking permissions from ranges."""
    dummy_db = DummyDB()

    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range

    mock_permission_result = Mock()
    if permission_exists:
        if range_type == "blueprint":
            mock_permission = BlueprintRangePermissionModel(
                blueprint_range_id=1, user_id=2, permission_type=permission_type
            )
        else:
            mock_permission = DeployedRangePermissionModel(
                deployed_range_id=1, user_id=2, permission_type=permission_type
            )
        mock_permission_result.scalar_one_or_none.return_value = mock_permission
    else:
        mock_permission_result.scalar_one_or_none.return_value = None

    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]

    requesting_user_id = 1  # Owner

    if range_type == "blueprint":
        result = await revoke_blueprint_permission(
            dummy_db, 1, 2, permission_type, requesting_user_id
        )
    else:
        result = await revoke_deployed_permission(
            dummy_db, 1, 2, permission_type, requesting_user_id
        )

    if permission_exists:
        dummy_db.delete.assert_called_once_with(mock_permission)
        dummy_db.flush.assert_called_once()
        assert result is True
    else:
        dummy_db.delete.assert_not_called()
        dummy_db.flush.assert_not_called()
        assert result is False


@pytest.mark.parametrize(
    "range_type,permission_type,expected_model_class",
    [
        ("blueprint", BlueprintPermissionType.READ, BlueprintRangePermissionModel),
        ("deployed", DeployedRangePermissionType.EXECUTE, DeployedRangePermissionModel),
    ],
)
async def test_revoke_permission_db_error(
    range_type: str,
    permission_type: BlueprintPermissionType | DeployedRangePermissionType,
    expected_model_class: type,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that revoke permission functions handle database errors."""
    dummy_db = DummyDB()

    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range

    if range_type == "blueprint":
        mock_permission = BlueprintRangePermissionModel(
            blueprint_range_id=1, user_id=2, permission_type=permission_type
        )
    else:
        mock_permission = DeployedRangePermissionModel(
            deployed_range_id=1, user_id=2, permission_type=permission_type
        )

    mock_permission_result = Mock()
    mock_permission_result.scalar_one_or_none.return_value = mock_permission

    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    requesting_user_id = 1  # Owner

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        if range_type == "blueprint":
            await revoke_blueprint_permission(
                dummy_db, 1, 2, permission_type, requesting_user_id
            )
        else:
            await revoke_deployed_permission(
                dummy_db, 1, 2, permission_type, requesting_user_id
            )

    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )
