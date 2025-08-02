from ipaddress import IPv4Address

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .mixin_models import OwnableObjectMixin


class VPNClientModel(Base, OwnableObjectMixin):
    """VPN client model class."""

    __tablename__ = "vpn_clients"

    name: Mapped[str] = mapped_column(String, nullable=False)
    wg_public_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # The assigned IP within the WireGuard network (e.g., 10.250.0.2)
    wg_assigned_ip: Mapped[IPv4Address] = mapped_column(INET, nullable=False)
    wg_config_file: Mapped[str] = mapped_column(Text, nullable=False)

    # Foreign key to the parent range
    range_id: Mapped[int] = mapped_column(
        ForeignKey("deployed_ranges.id", ondelete="CASCADE"), nullable=False
    )

    # Parent relationship
    range = relationship("DeployedRangeModel", back_populates="vpn_clients")

    # Prevent two configs with same IP
    __table_args__ = (
        UniqueConstraint("range_id", "wg_assigned_ip", name="_range_wg_ip_uc"),
    )
