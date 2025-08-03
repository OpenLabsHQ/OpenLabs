from unittest.mock import Mock

from src.app.crud.crud_ranges import (
    can_execute_deployed,
    can_read_blueprint,
    can_read_deployed,
    can_write_blueprint,
    can_write_deployed,
)
from src.app.enums.permissions import (
    BlueprintPermissionType,
    DeployedRangePermissionType,
)


class TestPermissionIsolation:
    """Test that permissions are properly isolated and don't grant unintended access."""

    def test_blueprint_read_permission_isolation(self) -> None:
        """Test that blueprint read permission only grants read access."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [
            Mock(user_id=2, permission_type=BlueprintPermissionType.READ.value)
        ]

        assert can_read_blueprint(range_model, 2) is True
        assert can_write_blueprint(range_model, 2) is False

    def test_blueprint_write_permission_includes_read(self) -> None:
        """Test that blueprint write permission includes read access."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [
            Mock(user_id=2, permission_type=BlueprintPermissionType.WRITE.value)
        ]

        assert can_read_blueprint(range_model, 2) is True
        assert can_write_blueprint(range_model, 2) is True

    def test_deployed_read_permission_isolation(self) -> None:
        """Test that deployed read permission only grants read access."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [
            Mock(user_id=2, permission_type=DeployedRangePermissionType.READ.value)
        ]

        assert can_read_deployed(range_model, 2) is True
        assert can_write_deployed(range_model, 2) is False
        assert can_execute_deployed(range_model, 2) is False

    def test_deployed_write_permission_includes_read(self) -> None:
        """Test that deployed write permission includes read access."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [
            Mock(user_id=2, permission_type=DeployedRangePermissionType.WRITE.value)
        ]

        assert can_read_deployed(range_model, 2) is True
        assert can_write_deployed(range_model, 2) is True
        assert can_execute_deployed(range_model, 2) is False

    def test_deployed_execute_permission_isolation(self) -> None:
        """Test that deployed execute permission is completely isolated."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [
            Mock(user_id=2, permission_type=DeployedRangePermissionType.EXECUTE.value)
        ]

        assert can_read_deployed(range_model, 2) is False
        assert can_write_deployed(range_model, 2) is False
        assert can_execute_deployed(range_model, 2) is True

    def test_no_permission_denies_all_access(self) -> None:
        """Test that users with no permissions are denied all access."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        assert can_read_deployed(range_model, 2) is False
        assert can_write_deployed(range_model, 2) is False
        assert can_execute_deployed(range_model, 2) is False

    def test_wrong_user_permission_denies_access(self) -> None:
        """Test that permissions for other users don't grant access."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [
            Mock(user_id=3, permission_type=DeployedRangePermissionType.READ.value)
        ]

        assert can_read_deployed(range_model, 2) is False
        assert can_write_deployed(range_model, 2) is False
        assert can_execute_deployed(range_model, 2) is False

    def test_owner_always_has_all_permissions(self) -> None:
        """Test that owners always have all permissions regardless of explicit grants."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        assert can_read_deployed(range_model, 1) is True
        assert can_write_deployed(range_model, 1) is True
        assert can_execute_deployed(range_model, 1) is True

    def test_multiple_permissions_work_correctly(self) -> None:
        """Test that users with multiple permissions get all granted access."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [
            Mock(user_id=2, permission_type=DeployedRangePermissionType.READ.value),
            Mock(user_id=2, permission_type=DeployedRangePermissionType.EXECUTE.value),
        ]

        assert can_read_deployed(range_model, 2) is True
        assert can_write_deployed(range_model, 2) is False
        assert can_execute_deployed(range_model, 2) is True

    def test_permission_boundaries_are_strict(self) -> None:
        """Test edge cases to ensure permission boundaries are strictly enforced."""
        range_model = Mock()
        range_model.owner_id = 1

        # User with only execute should not get read/write
        range_model.permissions = [
            Mock(user_id=2, permission_type=DeployedRangePermissionType.EXECUTE.value)
        ]
        assert can_read_deployed(range_model, 2) is False
        assert can_write_deployed(range_model, 2) is False
        assert can_execute_deployed(range_model, 2) is True

        # User with only read should not get write/execute
        range_model.permissions = [
            Mock(user_id=2, permission_type=DeployedRangePermissionType.READ.value)
        ]
        assert can_read_deployed(range_model, 2) is True
        assert can_write_deployed(range_model, 2) is False
        assert can_execute_deployed(range_model, 2) is False

        # User with only write should get read but not execute
        range_model.permissions = [
            Mock(user_id=2, permission_type=DeployedRangePermissionType.WRITE.value)
        ]
        assert can_read_deployed(range_model, 2) is True
        assert can_write_deployed(range_model, 2) is True
        assert can_execute_deployed(range_model, 2) is False
