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

# ==================== Grant Blueprint Permissions =====================


@pytest.mark.parametrize(
    "permission_type,user_id",
    [
        (BlueprintPermissionType.READ, 2),
        (BlueprintPermissionType.WRITE, 3),
    ],
)
async def test_grant_blueprint_permission(
    permission_type: BlueprintPermissionType,
    user_id: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test granting permissions to blueprint ranges."""
    dummy_db = DummyDB()

    mock_range = Mock()
    mock_range.owner_id = 1
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_range
    dummy_db.execute.return_value = mock_result

    range_id = 1
    requesting_user_id = 1  # Owner

    with caplog.at_level(logging.DEBUG):
        result = await grant_blueprint_permission(
            dummy_db, range_id, user_id, permission_type, requesting_user_id
        )

    dummy_db.add.assert_called_once()
    added_permission = dummy_db.add.call_args[0][0]
    assert isinstance(added_permission, BlueprintRangePermissionModel)
    assert added_permission.user_id == user_id
    assert added_permission.permission_type == permission_type
    assert added_permission.blueprint_range_id == range_id

    dummy_db.flush.assert_called_once()
    dummy_db.refresh.assert_called_once_with(added_permission)
    assert result == added_permission


async def test_grant_blueprint_permission_db_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that grant_blueprint_permission handles database errors."""
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
        await grant_blueprint_permission(
            dummy_db, 1, 2, BlueprintPermissionType.READ, requesting_user_id
        )

    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


# ==================== Grant Deployed Permissions =====================


@pytest.mark.parametrize(
    "permission_type,user_id",
    [
        (DeployedRangePermissionType.READ, 2),
        (DeployedRangePermissionType.WRITE, 3),
        (DeployedRangePermissionType.EXECUTE, 4),
    ],
)
async def test_grant_deployed_permission(
    permission_type: DeployedRangePermissionType,
    user_id: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test granting permissions to deployed ranges."""
    dummy_db = DummyDB()

    mock_range = Mock()
    mock_range.owner_id = 1
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_range
    dummy_db.execute.return_value = mock_result

    range_id = 1
    requesting_user_id = 1  # Owner

    with caplog.at_level(logging.DEBUG):
        result = await grant_deployed_permission(
            dummy_db, range_id, user_id, permission_type, requesting_user_id
        )

    dummy_db.add.assert_called_once()
    added_permission = dummy_db.add.call_args[0][0]
    assert isinstance(added_permission, DeployedRangePermissionModel)
    assert added_permission.user_id == user_id
    assert added_permission.permission_type == permission_type
    assert added_permission.deployed_range_id == range_id

    dummy_db.flush.assert_called_once()
    dummy_db.refresh.assert_called_once_with(added_permission)
    assert result == added_permission


async def test_grant_deployed_permission_db_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that grant_deployed_permission handles database errors."""
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
        await grant_deployed_permission(
            dummy_db, 1, 2, DeployedRangePermissionType.READ, requesting_user_id
        )

    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


# ==================== Revoke Blueprint Permissions =====================


@pytest.mark.parametrize(
    "permission_type,permission_exists",
    [
        (BlueprintPermissionType.READ, True),
        (BlueprintPermissionType.READ, False),
        (BlueprintPermissionType.WRITE, True),
    ],
)
async def test_revoke_blueprint_permission(
    permission_type: BlueprintPermissionType,
    permission_exists: bool,
) -> None:
    """Test revoking permissions from blueprint ranges."""
    dummy_db = DummyDB()

    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range

    mock_permission_result = Mock()
    if permission_exists:
        mock_permission = BlueprintRangePermissionModel(
            blueprint_range_id=1, user_id=2, permission_type=permission_type
        )
        mock_permission_result.scalar_one_or_none.return_value = mock_permission
    else:
        mock_permission_result.scalar_one_or_none.return_value = None

    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]

    requesting_user_id = 1  # Owner

    result = await revoke_blueprint_permission(
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


async def test_revoke_blueprint_permission_db_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that revoke_blueprint_permission handles database errors."""
    dummy_db = DummyDB()

    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range

    mock_permission = BlueprintRangePermissionModel(
        blueprint_range_id=1, user_id=2, permission_type=BlueprintPermissionType.READ
    )

    mock_permission_result = Mock()
    mock_permission_result.scalar_one_or_none.return_value = mock_permission

    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    requesting_user_id = 1  # Owner

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await revoke_blueprint_permission(
            dummy_db, 1, 2, BlueprintPermissionType.READ, requesting_user_id
        )

    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


# ==================== Revoke Deployed Permissions =====================


@pytest.mark.parametrize(
    "permission_type,permission_exists",
    [
        (DeployedRangePermissionType.EXECUTE, True),
        (DeployedRangePermissionType.WRITE, False),
        (DeployedRangePermissionType.READ, True),
    ],
)
async def test_revoke_deployed_permission(
    permission_type: DeployedRangePermissionType,
    permission_exists: bool,
) -> None:
    """Test revoking permissions from deployed ranges."""
    dummy_db = DummyDB()

    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range

    mock_permission_result = Mock()
    if permission_exists:
        mock_permission = DeployedRangePermissionModel(
            deployed_range_id=1, user_id=2, permission_type=permission_type
        )
        mock_permission_result.scalar_one_or_none.return_value = mock_permission
    else:
        mock_permission_result.scalar_one_or_none.return_value = None

    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]

    requesting_user_id = 1  # Owner

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


async def test_revoke_deployed_permission_db_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that revoke_deployed_permission handles database errors."""
    dummy_db = DummyDB()

    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range

    mock_permission = DeployedRangePermissionModel(
        deployed_range_id=1,
        user_id=2,
        permission_type=DeployedRangePermissionType.EXECUTE,
    )

    mock_permission_result = Mock()
    mock_permission_result.scalar_one_or_none.return_value = mock_permission

    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)

    requesting_user_id = 1  # Owner

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await revoke_deployed_permission(
            dummy_db, 1, 2, DeployedRangePermissionType.EXECUTE, requesting_user_id
        )

    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )
