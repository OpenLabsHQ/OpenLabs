import uuid
from ipaddress import IPv4Address

from sqlalchemy import ARRAY, UUID, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..core.db.database import Base
from ..enums.operating_systems import OpenLabsOS
from ..enums.specs import OpenLabsSpec
from .mixin_models import OwnableObjectMixin


class HostMixin(MappedAsDataclass):
    """Common Host attributes."""

    hostname: Mapped[str] = mapped_column(String, nullable=False)
    os: Mapped[OpenLabsOS] = mapped_column(Enum(OpenLabsOS), nullable=False)
    spec: Mapped[OpenLabsSpec] = mapped_column(Enum(OpenLabsSpec), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String))


# ==================== Blueprints =====================


class BlueprintHostModel(Base, OwnableObjectMixin, HostMixin):
    """SQLAlchemy ORM model for blueprint hosts."""

    __tablename__ = "blueprint_hosts"

    # Parent relationship
    subnet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprint_subnets.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    subnet = relationship("BlueprintSubnetModel", back_populates="hosts")

    def is_standalone(self) -> bool:
        """Return whether blueprint host model is standalone.

        Standalone means that the blueprint is not part of a larger blueprint.

        Returns
        -------
            bool: True if standalone. False otherwise.

        """
        return self.subnet_id is None


# ==================== Deployed (Instances) =====================


class DeployedHostModel(Base, OwnableObjectMixin, HostMixin):
    """SQLAlchemy ORM model for deployed host objects."""

    __tablename__ = "deployed_hosts"

    # Cloud provider fields
    resource_id: Mapped[str] = mapped_column(String, nullable=False)
    ip_address: Mapped[IPv4Address] = mapped_column(INET, nullable=False)

    # Parent relationship
    subnet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployed_subnets.id", ondelete="CASCADE"),
        nullable=False,
    )
    subnet = relationship("DeployedSubnetModel", back_populates="hosts")
