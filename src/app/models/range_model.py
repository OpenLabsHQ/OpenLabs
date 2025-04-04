from ipaddress import IPv4Address

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .common_models import OwnableObjectMixin, RangeMixin


class RangeModel(Base, OwnableObjectMixin, RangeMixin):
    """Range model class."""

    __tablename__ = "ranges"

    # Jumpbox
    public_ip: Mapped[IPv4Address] = mapped_column(INET, nullable=False)
    private_key: Mapped[str] = mapped_column(String, nullable=False)

    vpcs = relationship(
        "VPCModel",
        back_populates="range",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
