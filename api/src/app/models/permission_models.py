from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship, declared_attr

from ..core.db.database import Base


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
    def user(cls):
        return relationship("UserModel")


class BlueprintRangePermissionModel(Base, PermissionMixin):
    """Model for blueprint range permission grants to users."""

    __tablename__ = "blueprint_range_permissions"

    # The blueprint range being shared
    blueprint_range_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("blueprint_ranges.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    blueprint_range = relationship("BlueprintRangeModel", back_populates="permissions")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "blueprint_range_id",
            "user_id",
            "permission_type",
            name="uq_blueprint_range_permissions",
        ),
        CheckConstraint(
            "permission_type IN ('read', 'write')",
            name="ck_blueprint_range_permission_type",
        ),
    )


class DeployedRangePermissionModel(Base, PermissionMixin):
    """Model for deployed range permission grants to users."""

    __tablename__ = "deployed_range_permissions"

    # The deployed range being shared
    deployed_range_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("deployed_ranges.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    deployed_range = relationship("DeployedRangeModel", back_populates="permissions")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "deployed_range_id",
            "user_id",
            "permission_type",
            name="uq_deployed_range_permissions",
        ),
        CheckConstraint(
            "permission_type IN ('read', 'write', 'execute')",
            name="ck_deployed_range_permission_type",
        ),
    )
