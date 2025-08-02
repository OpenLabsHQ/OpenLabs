from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    declared_attr,
    mapped_column,
    relationship,
)

from ..core.db.database import Base
from ..enums.permissions import BlueprintPermissionType, DeployedRangePermissionType


class PermissionMixin(MappedAsDataclass):
    """Mixin class for common permission fields."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        init=False,
        comment="Primary key (BIGSERIAL)",
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    permission_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    @declared_attr
    def user(self) -> relationship:
        """User relationship."""
        return relationship("UserModel", init=False)


class BlueprintRangePermissionModel(Base, PermissionMixin):
    """Model for blueprint range permission grants to users."""

    __tablename__ = "blueprint_range_permissions"

    blueprint_range_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("blueprint_ranges.id", ondelete="CASCADE"),
        nullable=False,
    )

    blueprint_range = relationship("BlueprintRangeModel", back_populates="permissions")
    __table_args__ = (
        UniqueConstraint(
            "blueprint_range_id",
            "user_id",
            "permission_type",
            name="uq_blueprint_range_permissions",
        ),
        CheckConstraint(
            f"permission_type IN {BlueprintPermissionType.values()}",
            name="ck_blueprint_range_permission_type",
        ),
    )


class DeployedRangePermissionModel(Base, PermissionMixin):
    """Model for deployed range permission grants to users."""

    __tablename__ = "deployed_range_permissions"

    deployed_range_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("deployed_ranges.id", ondelete="CASCADE"),
        nullable=False,
    )

    deployed_range = relationship("DeployedRangeModel", back_populates="permissions")
    __table_args__ = (
        UniqueConstraint(
            "deployed_range_id",
            "user_id",
            "permission_type",
            name="uq_deployed_range_permissions",
        ),
        CheckConstraint(
            f"permission_type IN {DeployedRangePermissionType.values()}",
            name="ck_deployed_range_permission_type",
        ),
    )
