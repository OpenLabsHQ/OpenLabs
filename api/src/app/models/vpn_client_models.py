from ipaddress import IPv4Address

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..core.db.database import Base
from ..enums.vpns import OpenLabsVPNType
from .mixin_models import OwnableObjectMixin


class VPNClientMixin(MappedAsDataclass):
    """VPN client class."""

    name: Mapped[str] = mapped_column(String, nullable=False)


class BlueprintVPNClientModel(Base, VPNClientMixin, OwnableObjectMixin):
    """Blueprint VPN client base class."""

    __tablename__ = "blueprint_vpn_clients"
    vpn_gateway_id: Mapped[int] = mapped_column(
        ForeignKey("blueprint_vpn_gateways.id", ondelete="CASCADE"), nullable=False
    )
    gateway = relationship("BlueprintVPNGatewayModel", back_populates="vpn_clients")

    __table_args__ = (
        # A client name must be unique within its gateway
        UniqueConstraint("vpn_gateway_id", "name", name="_gateway_name_uc"),
    )


class DeployedVPNClientModel(Base, VPNClientMixin, OwnableObjectMixin):
    """Deployed VPN client base class."""

    __tablename__ = "deployed_vpn_clients"

    assigned_ip: Mapped[IPv4Address] = mapped_column(INET, nullable=False)
    vpn_gateway_id: Mapped[int] = mapped_column(
        ForeignKey("deployed_vpn_gateways.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    gateway = relationship("DeployedVPNGatewayModel", back_populates="vpn_clients")

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": "vpn_client",
        "polymorphic_on": type,
    }

    __table_args__ = (
        # A client IP must be unique within its gateway
        UniqueConstraint("vpn_gateway_id", "assigned_ip", name="_gateway_ip_uc"),
        # A client name must be unique within its gateway
        UniqueConstraint("vpn_gateway_id", "name", name="_gateway_name_uc"),
    )


class WireguardClientModel(DeployedVPNClientModel):
    """Wireguard VPN client class."""

    wg_client_public_key: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )
    wg_client_private_key: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": OpenLabsVPNType.WIREGUARD.value,
    }
