from ipaddress import IPv4Network

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import CIDR
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..core.db.database import Base
from .mixin_models import OwnableObjectMixin


class VPCMixin(MappedAsDataclass):
    """Common VPC attributes."""

    name: Mapped[str] = mapped_column(String, nullable=False)
    cidr: Mapped[IPv4Network] = mapped_column(CIDR, nullable=False)


# ==================== Blueprints =====================


class BlueprintVPCModel(Base, OwnableObjectMixin, VPCMixin):
    """SQLAlchemy ORM model for blueprint VPC objects."""

    __tablename__ = "blueprint_vpcs"

    # Parent relationship
    range_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("blueprint_ranges.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    range = relationship("BlueprintRangeModel", back_populates="vpcs")

    # Child relationship
    subnets = relationship(
        "BlueprintSubnetModel",
        back_populates="vpc",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def is_standalone(self) -> bool:
        """Return whether vpc blueprint model is standalone.

        Standalone means that the blueprint is not part of a larger blueprint.

        Returns
        -------
            bool: True if standalone. False otherwise.

        """
        return self.range_id is None


# ==================== Deployed (Instances) =====================


class DeployedVPCModel(Base, OwnableObjectMixin, VPCMixin):
    """SQLAlchemy ORM model for deployed VPC objects."""

    __tablename__ = "deployed_vpcs"

    resource_id: Mapped[str] = mapped_column(String, nullable=False)

    # Parent relationship
    range_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("deployed_ranges.id", ondelete="CASCADE"),
        nullable=False,
    )
    range = relationship("DeployedRangeModel", back_populates="vpcs")

    # Child relationship
    subnets = relationship(
        "DeployedSubnetModel",
        back_populates="vpc",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
