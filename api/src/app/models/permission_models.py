from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..core.db.database import Base
from .mixin_models import OwnableObjectMixin


class BlueprintRangePermissionModel(Base, MappedAsDataclass):
    """Model for blueprint range permission grants to users."""

    __tablename__ = "blueprint_range_permissions"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        init=False,
        comment="Primary key (BIGSERIAL)",
    )

    # The blueprint range being shared
    blueprint_range_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("blueprint_ranges.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The user being granted permission
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Type of permission granted (read, write)
    permission_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    # Relationships
    blueprint_range = relationship("BlueprintRangeModel", back_populates="permissions")
    user = relationship("UserModel")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "blueprint_range_id", 
            "user_id", 
            "permission_type",
            name="uq_blueprint_range_permissions"
        ),
        CheckConstraint(
            "permission_type IN ('read', 'write')",
            name="ck_blueprint_range_permission_type"
        ),
    )


class DeployedRangePermissionModel(Base, MappedAsDataclass):
    """Model for deployed range permission grants to users."""

    __tablename__ = "deployed_range_permissions"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        init=False,
        comment="Primary key (BIGSERIAL)",
    )

    # The deployed range being shared
    deployed_range_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("deployed_ranges.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The user being granted permission
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Type of permission granted (read, write, execute)
    permission_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    # Relationships
    deployed_range = relationship("DeployedRangeModel", back_populates="permissions")
    user = relationship("UserModel")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "deployed_range_id", 
            "user_id", 
            "permission_type",
            name="uq_deployed_range_permissions"
        ),
        CheckConstraint(
            "permission_type IN ('read', 'write', 'execute')",
            name="ck_deployed_range_permission_type"
        ),
    )
