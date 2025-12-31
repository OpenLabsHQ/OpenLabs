from datetime import datetime
from ipaddress import IPv4Address

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..core.db.database import Base
from ..enums.providers import OpenLabsProvider
from ..enums.range_states import RangeState
from ..enums.regions import OpenLabsRegion
from .mixin_models import OwnableObjectMixin


class RangeMixin(MappedAsDataclass):
    """Common range attributes."""

    name: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[OpenLabsProvider] = mapped_column(
        Enum(OpenLabsProvider), nullable=False
    )
    vnc: Mapped[bool] = mapped_column(Boolean, nullable=False)
    vpn: Mapped[bool] = mapped_column(Boolean, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)


# ==================== Blueprints =====================


class BlueprintRangeModel(Base, OwnableObjectMixin, RangeMixin):
    """SQLAlchemy ORM model for blueprint range objects."""

    __tablename__ = "blueprint_ranges"

    # Child relationship
    vpcs = relationship(
        "BlueprintVPCModel",
        back_populates="range",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def is_standalone(self) -> bool:
        """Return whether blueprint range model is standalone.

        Standalone means that the blueprint is not part of a larger blueprint.

        Returns
        -------
            bool: True if standalone. False otherwise.

        """
        # Ranges are currently the highest level blueprint object
        return True


# ==================== Deployed (Instances) =====================


class DeployedRangeModel(Base, OwnableObjectMixin, RangeMixin):
    """Deployed range model class."""

    __tablename__ = "deployed_ranges"

    deployment_id: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    readme: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[RangeState] = mapped_column(Enum(RangeState), nullable=False)
    region: Mapped[OpenLabsRegion] = mapped_column(Enum(OpenLabsRegion), nullable=False)

    # Jumpbox
    jumpbox_resource_id: Mapped[str] = mapped_column(String, nullable=False)
    jumpbox_public_ip: Mapped[IPv4Address] = mapped_column(INET, nullable=False)
    range_private_key: Mapped[str] = mapped_column(String, nullable=False)

    vpcs = relationship(
        "DeployedVPCModel",
        back_populates="range",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
