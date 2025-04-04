from datetime import datetime
from ipaddress import IPv4Address
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from ..enums.range_states import RangeState
from ..enums.regions import OpenLabsRegion
from .common_models import OwnableObjectMixin


class RangeModel(Base, OwnableObjectMixin):
    """Range model class."""

    __tablename__ = "ranges"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    template: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    readme: Mapped[str] = mapped_column(String, nullable=True)
    state_file: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    state: Mapped[RangeState] = mapped_column(Enum(RangeState), nullable=False)
    region: Mapped[OpenLabsRegion] = mapped_column(Enum(OpenLabsRegion), nullable=False)

    # Jumpbox
    public_ip: Mapped[IPv4Address] = mapped_column(INET, nullable=True)
    private_key: Mapped[str] = mapped_column(String, nullable=True)

    vpcs = relationship(
        "VPCModel",
        back_populates="range",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    subnets = relationship(
        "SubnetModel",
        back_populates="range",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    hosts = relationship(
        "HostModel",
        back_populates="range",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
