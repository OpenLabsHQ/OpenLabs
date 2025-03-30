import uuid
from ipaddress import IPv4Network

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import CIDR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .common_models import OwnableObjectMixin


class VPCModel(Base, OwnableObjectMixin):
    """SQLAlchemy ORM model for VPC objects."""

    __tablename__ = "vpcs"

    provider_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    cidr: Mapped[IPv4Network] = mapped_column(CIDR, nullable=False)

    range_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("ranges.id", ondelete="CASCADE"),
        nullable=False,
    )
    range = relationship("RangeModel", back_populates="VPCModel")
