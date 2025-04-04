from datetime import datetime
from ipaddress import IPv4Address
from typing import Any

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import INET, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from ..enums.range_states import RangeState
from ..enums.regions import OpenLabsRegion
from .mixin_models import OwnableObjectMixin, RangeMixin


class RangeModel(Base, OwnableObjectMixin, RangeMixin):
    """Range model class."""

    __tablename__ = "ranges"

    description: Mapped[str | None] = mapped_column(String, nullable=True)
    date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    readme: Mapped[str | None] = mapped_column(String, nullable=True)
    state_file: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    state: Mapped[RangeState] = mapped_column(Enum(RangeState), nullable=False)
    region: Mapped[OpenLabsRegion] = mapped_column(Enum(OpenLabsRegion), nullable=False)

    # Jumpbox
    public_ip: Mapped[IPv4Address] = mapped_column(INET, nullable=False)
    private_key: Mapped[str] = mapped_column(String, nullable=False)

    vpcs = relationship(
        "VPCModel",
        back_populates="range",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
