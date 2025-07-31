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
from src.app.models.permission_models import (
    BlueprintRangePermissionModel,
    DeployedRangePermissionModel,
)

from .crud_mocks import DummyDB

# ==================== Grant Permissions =====================


async def test_grant_blueprint_read_permission(caplog) -> None:
    """Test granting read permission to a blueprint range."""
    from src.app.models.range_models import BlueprintRangeModel
    from src.app.enums.permissions import BlueprintPermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_range
    dummy_db.execute.return_value = mock_result

    blueprint_range_id = 1
    user_id = 2
    requesting_user_id = 1  # Owner

    with caplog.at_level(logging.DEBUG):
        result = await grant_blueprint_permission(
            dummy_db, blueprint_range_id, user_id, BlueprintPermissionType.READ, requesting_user_id
        )

    # Check that permission was added to db
    dummy_db.add.assert_called_once()
    added_permission = dummy_db.add.call_args[0][0]
    assert isinstance(added_permission, BlueprintRangePermissionModel)
    assert added_permission.blueprint_range_id == blueprint_range_id
    assert added_permission.user_id == user_id
    assert added_permission.permission_type == BlueprintPermissionType.READ

    # Check that db operations were called
    dummy_db.flush.assert_called_once()
    dummy_db.refresh.assert_called_once_with(added_permission)

    # Check return value
    assert result == added_permission


async def test_grant_blueprint_write_permission() -> None:
    """Test granting write permission to a blueprint range."""
    from src.app.enums.permissions import BlueprintPermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_range
    dummy_db.execute.return_value = mock_result

    blueprint_range_id = 1
    user_id = 3
    requesting_user_id = 1  # Owner

    result = await grant_blueprint_permission(
        dummy_db, blueprint_range_id, user_id, BlueprintPermissionType.WRITE, requesting_user_id
    )

    # Check that permission was created correctly
    added_permission = dummy_db.add.call_args[0][0]
    assert added_permission.blueprint_range_id == blueprint_range_id
    assert added_permission.user_id == user_id
    assert added_permission.permission_type == BlueprintPermissionType.WRITE

    assert result == added_permission


async def test_grant_deployed_read_permission() -> None:
    """Test granting read permission to a deployed range."""
    from src.app.enums.permissions import DeployedRangePermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_range
    dummy_db.execute.return_value = mock_result

    deployed_range_id = 1
    user_id = 2
    requesting_user_id = 1  # Owner

    result = await grant_deployed_permission(
        dummy_db, deployed_range_id, user_id, DeployedRangePermissionType.READ, requesting_user_id
    )

    # Check that permission was added to db
    dummy_db.add.assert_called_once()
    added_permission = dummy_db.add.call_args[0][0]
    assert isinstance(added_permission, DeployedRangePermissionModel)
    assert added_permission.deployed_range_id == deployed_range_id
    assert added_permission.user_id == user_id
    assert added_permission.permission_type == DeployedRangePermissionType.READ

    # Check that db operations were called
    dummy_db.flush.assert_called_once()
    dummy_db.refresh.assert_called_once_with(added_permission)

    # Check return value
    assert result == added_permission


async def test_grant_deployed_write_permission() -> None:
    """Test granting write permission to a deployed range."""
    from src.app.enums.permissions import DeployedRangePermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_range
    dummy_db.execute.return_value = mock_result

    deployed_range_id = 1
    user_id = 3
    requesting_user_id = 1  # Owner

    result = await grant_deployed_permission(
        dummy_db, deployed_range_id, user_id, DeployedRangePermissionType.WRITE, requesting_user_id
    )

    # Check that permission was created correctly
    added_permission = dummy_db.add.call_args[0][0]
    assert added_permission.deployed_range_id == deployed_range_id
    assert added_permission.user_id == user_id
    assert added_permission.permission_type == DeployedRangePermissionType.WRITE

    assert result == added_permission


async def test_grant_deployed_execute_permission() -> None:
    """Test granting execute permission to a deployed range."""
    from src.app.enums.permissions import DeployedRangePermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_range
    dummy_db.execute.return_value = mock_result

    deployed_range_id = 1
    user_id = 4
    requesting_user_id = 1  # Owner

    result = await grant_deployed_permission(
        dummy_db, deployed_range_id, user_id, DeployedRangePermissionType.EXECUTE, requesting_user_id
    )

    # Check that permission was created correctly
    added_permission = dummy_db.add.call_args[0][0]
    assert added_permission.deployed_range_id == deployed_range_id
    assert added_permission.user_id == user_id
    assert added_permission.permission_type == DeployedRangePermissionType.EXECUTE

    assert result == added_permission


async def test_grant_blueprint_permission_db_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that grant_blueprint_permission handles database errors."""
    from src.app.enums.permissions import BlueprintPermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check
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
        await grant_blueprint_permission(dummy_db, 1, 2, BlueprintPermissionType.READ, requesting_user_id)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_grant_deployed_permission_db_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that grant_deployed_permission handles database errors."""
    from src.app.enums.permissions import DeployedRangePermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check
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
        await grant_deployed_permission(dummy_db, 1, 2, DeployedRangePermissionType.READ, requesting_user_id)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


# ==================== Revoke Permissions =====================


async def test_revoke_blueprint_permission_success() -> None:
    """Test successfully revoking a blueprint permission."""
    from src.app.enums.permissions import BlueprintPermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check first (first call)
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range
    
    # Create a mock permission to be found and deleted
    mock_permission = BlueprintRangePermissionModel(
        blueprint_range_id=1,
        user_id=2,
        permission_type=BlueprintPermissionType.READ,
    )
    
    # Mock the permission lookup (second call)
    mock_permission_result = Mock()
    mock_permission_result.scalar_one_or_none.return_value = mock_permission
    
    # Mock the execute method to return different results for different calls
    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]
    
    requesting_user_id = 1  # Owner

    result = await revoke_blueprint_permission(dummy_db, 1, 2, BlueprintPermissionType.READ, requesting_user_id)

    # Check that the permission was deleted
    dummy_db.delete.assert_called_once_with(mock_permission)
    dummy_db.flush.assert_called_once()

    # Check return value
    assert result is True


async def test_revoke_blueprint_permission_not_found() -> None:
    """Test revoking a blueprint permission that doesn't exist."""
    from src.app.enums.permissions import BlueprintPermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check first (first call)
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range
    
    # Mock the permission lookup to return None (permission not found)
    mock_permission_result = Mock()
    mock_permission_result.scalar_one_or_none.return_value = None
    
    # Mock the execute method to return different results for different calls
    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]
    
    requesting_user_id = 1  # Owner

    result = await revoke_blueprint_permission(dummy_db, 1, 2, BlueprintPermissionType.READ, requesting_user_id)

    # Check that delete was not called
    dummy_db.delete.assert_not_called()
    dummy_db.flush.assert_not_called()

    # Check return value
    assert result is False


async def test_revoke_deployed_permission_success() -> None:
    """Test successfully revoking a deployed permission."""
    from src.app.enums.permissions import DeployedRangePermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check first (first call)
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range
    
    # Create a mock permission to be found and deleted
    mock_permission = DeployedRangePermissionModel(
        deployed_range_id=1,
        user_id=2,
        permission_type=DeployedRangePermissionType.EXECUTE,
    )
    
    # Mock the permission lookup (second call)
    mock_permission_result = Mock()
    mock_permission_result.scalar_one_or_none.return_value = mock_permission
    
    # Mock the execute method to return different results for different calls
    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]
    
    requesting_user_id = 1  # Owner

    result = await revoke_deployed_permission(dummy_db, 1, 2, DeployedRangePermissionType.EXECUTE, requesting_user_id)

    # Check that the permission was deleted
    dummy_db.delete.assert_called_once_with(mock_permission)
    dummy_db.flush.assert_called_once()

    # Check return value
    assert result is True


async def test_revoke_deployed_permission_not_found() -> None:
    """Test revoking a deployed permission that doesn't exist."""
    from src.app.enums.permissions import DeployedRangePermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check first (first call)
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range
    
    # Mock the permission lookup to return None (permission not found)
    mock_permission_result = Mock()
    mock_permission_result.scalar_one_or_none.return_value = None
    
    # Mock the execute method to return different results for different calls
    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]
    
    requesting_user_id = 1  # Owner

    result = await revoke_deployed_permission(dummy_db, 1, 2, DeployedRangePermissionType.WRITE, requesting_user_id)

    # Check that delete was not called
    dummy_db.delete.assert_not_called()
    dummy_db.flush.assert_not_called()

    # Check return value
    assert result is False


async def test_revoke_blueprint_permission_db_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that revoke_blueprint_permission handles database errors."""
    from src.app.enums.permissions import BlueprintPermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check first (first call)
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range
    
    # Create a mock permission
    mock_permission = BlueprintRangePermissionModel(
        blueprint_range_id=1,
        user_id=2,
        permission_type=BlueprintPermissionType.READ,
    )
    
    # Mock the permission lookup (second call)
    mock_permission_result = Mock()
    mock_permission_result.scalar_one_or_none.return_value = mock_permission
    
    # Mock the execute method to return different results for different calls
    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)
    
    requesting_user_id = 1  # Owner

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await revoke_blueprint_permission(dummy_db, 1, 2, BlueprintPermissionType.READ, requesting_user_id)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )


async def test_revoke_deployed_permission_db_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that revoke_deployed_permission handles database errors."""
    from src.app.enums.permissions import DeployedRangePermissionType
    
    dummy_db = DummyDB()
    
    # Mock the ownership check first (first call)
    mock_range = Mock()
    mock_range.owner_id = 1
    mock_ownership_result = Mock()
    mock_ownership_result.scalar_one_or_none.return_value = mock_range
    
    # Create a mock permission
    mock_permission = DeployedRangePermissionModel(
        deployed_range_id=1,
        user_id=2,
        permission_type=DeployedRangePermissionType.EXECUTE,
    )
    
    # Mock the permission lookup (second call)
    mock_permission_result = Mock()
    mock_permission_result.scalar_one_or_none.return_value = mock_permission
    
    # Mock the execute method to return different results for different calls
    dummy_db.execute.side_effect = [mock_ownership_result, mock_permission_result]

    # Force a db exception
    test_except_msg = "Fake DB error!"
    dummy_db.flush.side_effect = SQLAlchemyError(test_except_msg)
    
    requesting_user_id = 1  # Owner

    with pytest.raises(SQLAlchemyError, match=test_except_msg):
        await revoke_deployed_permission(dummy_db, 1, 2, DeployedRangePermissionType.EXECUTE, requesting_user_id)

    # Check that we properly logger.exception() db errors
    assert any(
        record.levelno == logging.ERROR
        and record.exc_info is not None
        and test_except_msg in record.message
        for record in caplog.records
    )
