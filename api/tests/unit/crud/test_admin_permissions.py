from unittest.mock import Mock

from src.app.crud.crud_ranges import (
    can_execute_deployed,
    can_read_blueprint,
    can_read_deployed,
    can_write_blueprint,
    can_write_deployed,
)
from src.app.enums.permissions import (
    DeployedRangePermissionType,
)


class TestAdminPermissions:
    """Test admin permission behavior per end-to-end encryption model."""

    def test_admin_has_full_blueprint_access(self) -> None:
        """Test that admins can read and write any blueprint (not encrypted)."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        # Admin user (different from owner)
        admin_user = Mock()
        admin_user.id = 2
        admin_user.is_admin = True

        # Admin should have full access to blueprints
        assert can_read_blueprint(range_model, admin_user.id, admin_user) is True
        assert can_write_blueprint(range_model, admin_user.id, admin_user) is True

    def test_admin_has_read_only_deployed_access(self) -> None:
        """Test that admins can only read deployed ranges (due to encryption)."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        # Admin user (different from owner)
        admin_user = Mock()
        admin_user.id = 2
        admin_user.is_admin = True

        # Admin should only have read access to deployed ranges
        assert can_read_deployed(range_model, admin_user.id, admin_user) is True
        assert can_write_deployed(range_model, admin_user.id, admin_user) is False
        assert can_execute_deployed(range_model, admin_user.id, admin_user) is False

    def test_admin_permissions_override_no_explicit_grants(self) -> None:
        """Test admin permissions work even without explicit permission grants."""
        blueprint_range = Mock()
        blueprint_range.owner_id = 1
        blueprint_range.permissions = []

        deployed_range = Mock()
        deployed_range.owner_id = 1
        deployed_range.permissions = []

        admin_user = Mock()
        admin_user.id = 3
        admin_user.is_admin = True

        # Admin should override lack of explicit permissions
        assert can_read_blueprint(blueprint_range, admin_user.id, admin_user) is True
        assert can_write_blueprint(blueprint_range, admin_user.id, admin_user) is True
        assert can_read_deployed(deployed_range, admin_user.id, admin_user) is True
        assert can_write_deployed(deployed_range, admin_user.id, admin_user) is False
        assert can_execute_deployed(deployed_range, admin_user.id, admin_user) is False

    def test_non_admin_follows_normal_permission_rules(self) -> None:
        """Test that non-admin users still follow normal permission rules."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        regular_user = Mock()
        regular_user.id = 2
        regular_user.is_admin = False

        # Regular user should have no access without explicit permissions
        assert can_read_blueprint(range_model, regular_user.id, regular_user) is False
        assert can_write_blueprint(range_model, regular_user.id, regular_user) is False
        assert can_read_deployed(range_model, regular_user.id, regular_user) is False
        assert can_write_deployed(range_model, regular_user.id, regular_user) is False
        assert can_execute_deployed(range_model, regular_user.id, regular_user) is False

    def test_owner_still_has_full_access_regardless_of_admin_status(self) -> None:
        """Test that owners always have full access regardless of admin status."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        # Owner who is not admin
        owner_user = Mock()
        owner_user.id = 1
        owner_user.is_admin = False

        # Owner should have full access regardless of admin status
        assert can_read_blueprint(range_model, owner_user.id, owner_user) is True
        assert can_write_blueprint(range_model, owner_user.id, owner_user) is True
        assert can_read_deployed(range_model, owner_user.id, owner_user) is True
        assert can_write_deployed(range_model, owner_user.id, owner_user) is True
        assert can_execute_deployed(range_model, owner_user.id, owner_user) is True

    def test_admin_and_owner_same_user(self) -> None:
        """Test behavior when user is both admin and owner."""
        range_model = Mock()
        range_model.owner_id = 1
        range_model.permissions = []

        admin_owner = Mock()
        admin_owner.id = 1
        admin_owner.is_admin = True

        # Should have full access (owner privileges take precedence)
        assert can_read_blueprint(range_model, admin_owner.id, admin_owner) is True
        assert can_write_blueprint(range_model, admin_owner.id, admin_owner) is True
        assert can_read_deployed(range_model, admin_owner.id, admin_owner) is True
        assert can_write_deployed(range_model, admin_owner.id, admin_owner) is True
        assert can_execute_deployed(range_model, admin_owner.id, admin_owner) is True

    def test_encryption_boundary_prevents_admin_deployed_modifications(self) -> None:
        """Test that encryption boundary prevents admin modifications to deployed ranges."""
        deployed_range = Mock()
        deployed_range.owner_id = 1
        deployed_range.permissions = [
            Mock(user_id=3, permission_type=DeployedRangePermissionType.WRITE.value),
            Mock(user_id=4, permission_type=DeployedRangePermissionType.EXECUTE.value),
        ]

        admin_user = Mock()
        admin_user.id = 2
        admin_user.is_admin = True

        # Admin can read but cannot write/execute due to encryption
        assert can_read_deployed(deployed_range, admin_user.id, admin_user) is True
        assert can_write_deployed(deployed_range, admin_user.id, admin_user) is False
        assert can_execute_deployed(deployed_range, admin_user.id, admin_user) is False

        # Regular users with explicit permissions should still work
        assert can_write_deployed(deployed_range, 3) is True
        assert can_execute_deployed(deployed_range, 4) is True
