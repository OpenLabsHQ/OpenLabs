"""Test permission system behavior including admin boundaries and security isolation."""

from unittest.mock import Mock

import pytest

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


class TestAdminPermissions:
    """Test admin permission behavior per end-to-end encryption model."""

    def test_admin_has_full_blueprint_access(self) -> None:
        """Admins can read and write any blueprint (not encrypted)."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        admin_user = Mock()
        admin_user.id = 2
        admin_user.is_admin = True

        assert can_read_blueprint(range_model, admin_user.id, admin_user) is True
        assert can_write_blueprint(range_model, admin_user.id, admin_user) is True

    def test_admin_has_read_only_deployed_access(self) -> None:
        """Admins can only read deployed ranges (due to encryption)."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        admin_user = Mock()
        admin_user.id = 2
        admin_user.is_admin = True

        assert can_read_deployed(range_model, admin_user.id, admin_user) is True
        assert can_write_deployed(range_model, admin_user.id, admin_user) is False
        assert can_execute_deployed(range_model, admin_user.id, admin_user) is False

    def test_encryption_boundary_prevents_admin_deployed_modifications(self) -> None:
        """E2E encryption prevents admin write/execute on deployed ranges."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        admin_user = Mock()
        admin_user.id = 2
        admin_user.is_admin = True

        # Admin cannot modify or execute deployed ranges due to encryption
        assert can_write_deployed(range_model, admin_user.id, admin_user) is False
        assert can_execute_deployed(range_model, admin_user.id, admin_user) is False
        # But can still read metadata
        assert can_read_deployed(range_model, admin_user.id, admin_user) is True

    def test_owner_always_has_full_access_regardless_of_admin_status(self) -> None:
        """Owners always have full access regardless of admin status."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        # Test owner who is also admin
        admin_owner = Mock()
        admin_owner.id = 1
        admin_owner.is_admin = True

        assert can_read_blueprint(range_model, admin_owner.id, admin_owner) is True
        assert can_write_blueprint(range_model, admin_owner.id, admin_owner) is True
        assert can_read_deployed(range_model, admin_owner.id, admin_owner) is True
        assert can_write_deployed(range_model, admin_owner.id, admin_owner) is True
        assert can_execute_deployed(range_model, admin_owner.id, admin_owner) is True


class TestPermissionIsolation:
    """Test that permissions are properly isolated and don't grant unintended access."""

    @pytest.mark.parametrize(
        "permission_type,expected_read,expected_write",
        [
            (BlueprintPermissionType.READ.value, True, False),
            (BlueprintPermissionType.WRITE.value, True, True),
        ],
    )
    def test_blueprint_permission_boundaries(
        self, permission_type: str, expected_read: bool, expected_write: bool
    ) -> None:
        """Blueprint permissions grant appropriate access levels."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [Mock(user_id=2, permission_type=permission_type)]

        assert can_read_blueprint(range_model, 2) is expected_read
        assert can_write_blueprint(range_model, 2) is expected_write

    @pytest.mark.parametrize(
        "permission_type,expected_read,expected_write,expected_execute",
        [
            (DeployedRangePermissionType.READ.value, True, False, False),
            (DeployedRangePermissionType.WRITE.value, True, True, False),
            (DeployedRangePermissionType.EXECUTE.value, True, False, True),
        ],
    )
    def test_deployed_permission_boundaries(
        self,
        permission_type: str,
        expected_read: bool,
        expected_write: bool,
        expected_execute: bool,
    ) -> None:
        """Deployed range permissions grant appropriate access levels."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [Mock(user_id=2, permission_type=permission_type)]

        assert can_read_deployed(range_model, 2) is expected_read
        assert can_write_deployed(range_model, 2) is expected_write
        assert can_execute_deployed(range_model, 2) is expected_execute

    def test_no_permission_denies_all_access(self) -> None:
        """Users without permissions cannot access ranges."""
        blueprint_range = Mock()
        blueprint_range.owner_id = 1
        blueprint_range.permissions = []

        deployed_range = Mock()
        deployed_range.owner_id = 1
        deployed_range.permissions = []

        user_id = 2  # Not owner, no permissions

        # Blueprint access denied
        assert can_read_blueprint(blueprint_range, user_id) is False
        assert can_write_blueprint(blueprint_range, user_id) is False

        # Deployed range access denied
        assert can_read_deployed(deployed_range, user_id) is False
        assert can_write_deployed(deployed_range, user_id) is False
        assert can_execute_deployed(deployed_range, user_id) is False

    def test_wrong_user_permission_denies_access(self) -> None:
        """Permissions granted to other users don't grant access."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [
            Mock(user_id=3, permission_type=BlueprintPermissionType.WRITE.value)
        ]

        user_id = 2  # Different user than permission grant

        assert can_read_blueprint(range_model, user_id) is False
        assert can_write_blueprint(range_model, user_id) is False

    def test_multiple_permissions_work_correctly(self) -> None:
        """Multiple permission grants work independently."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = [
            Mock(user_id=2, permission_type=DeployedRangePermissionType.READ.value),
            Mock(user_id=3, permission_type=DeployedRangePermissionType.EXECUTE.value),
            Mock(user_id=4, permission_type=DeployedRangePermissionType.WRITE.value),
        ]

        # User 2: read only
        assert can_read_deployed(range_model, 2) is True
        assert can_write_deployed(range_model, 2) is False
        assert can_execute_deployed(range_model, 2) is False

        # User 3: read + execute (execute includes read)
        assert can_read_deployed(range_model, 3) is True
        assert can_write_deployed(range_model, 3) is False
        assert can_execute_deployed(range_model, 3) is True

        # User 4: read + write
        assert can_read_deployed(range_model, 4) is True
        assert can_write_deployed(range_model, 4) is True
        assert can_execute_deployed(range_model, 4) is False


class TestOwnerPermissions:
    """Test that owners always have full access regardless of explicit grants."""

    def test_owner_bypasses_explicit_permissions(self) -> None:
        """Owners have access even without explicit permission grants."""
        blueprint_range = Mock()
        blueprint_range.owner_id = 1
        blueprint_range.permissions = []  # No explicit permissions

        deployed_range = Mock()
        deployed_range.owner_id = 1
        deployed_range.permissions = []  # No explicit permissions

        owner_id = 1

        # Owner has full blueprint access
        assert can_read_blueprint(blueprint_range, owner_id) is True
        assert can_write_blueprint(blueprint_range, owner_id) is True

        # Owner has full deployed range access
        assert can_read_deployed(deployed_range, owner_id) is True
        assert can_write_deployed(deployed_range, owner_id) is True
        assert can_execute_deployed(deployed_range, owner_id) is True
