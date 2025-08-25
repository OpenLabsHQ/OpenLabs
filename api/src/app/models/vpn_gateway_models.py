from ipaddress import IPv4Network

from sqlalchemy import (
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, ExcludeConstraint
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..core.db.database import Base
from ..enums.vpns import OpenLabsVPNType
from ..validators.network import DNSEntry
from .mixin_models import OwnableObjectMixin


class VPNGatewayMixin(MappedAsDataclass):
    """VPN gateway class."""

    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[OpenLabsVPNType] = mapped_column(String(50), nullable=False)
    dns_servers: Mapped[list[DNSEntry]] = mapped_column(ARRAY(String))


class BlueprintVPNGatewayModel(Base, VPNGatewayMixin, OwnableObjectMixin):
    """Blueprint for a VPN Gateway."""

    __tablename__ = "blueprint_vpn_gateways"

    cidr: Mapped[IPv4Network | None] = mapped_column(INET, nullable=True)
    range_id: Mapped[int] = mapped_column(
        ForeignKey("blueprint_ranges.id", ondelete="CASCADE"), nullable=False
    )
    range = relationship("BlueprintRangeModel", back_populates="vpn_gateways")

    vpn_clients = relationship(
        "BlueprintVPNClientModel",
        back_populates="gateway",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        # VPN gateways names should be unique within a range
        UniqueConstraint("range_id", "name", name="_range_gateway_name_uc"),
    )


class DeployedVPNGatewayModel(Base, VPNGatewayMixin, OwnableObjectMixin):
    """Base class for all deployed VPN gateways using single-table inheritance."""

    __tablename__ = "deployed_vpn_gateways"

    cidr: Mapped[IPv4Network] = mapped_column(INET, nullable=False)
    range_id: Mapped[int] = mapped_column(
        ForeignKey("deployed_ranges.id", ondelete="CASCADE"), nullable=False
    )
    range = relationship("DeployedRangeModel", back_populates="vpn_gateways")

    # A gateway has many clients
    vpn_clients = relationship(
        "DeployedVPNClientModel",
        back_populates="gateway",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": "vpn_gateway",  # Identity for the base class
        "polymorphic_on": type,  # Column to determine the subclass
    }

    __table_args__ = (
        # VPN gateways names should be unique within a range
        UniqueConstraint("range_id", "name", name="_range_gateway_name_uc"),
        # VPN gateway cidr blocks should not overlap
        ExcludeConstraint(
            ("range_id", "="),
            ("cidr", "&&"),
            name="exclude_overlapping_gateway_cidrs",
        ),
    )


class WireguardGatewayModel(DeployedVPNGatewayModel):
    """A deployed WireGuard gateway with its specific server keys."""

    wg_server_public_key: Mapped[str] = mapped_column(String, nullable=True)

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": OpenLabsVPNType.WIREGUARD.value,
    }
