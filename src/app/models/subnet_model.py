import uuid
from ipaddress import IPv4Network

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import CIDR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .common_models import OwnableObjectMixin


class SubnetModel(Base, OwnableObjectMixin):
    """SQLAlchemy ORM model for subnet objects."""

    __tablename__ = "subnets"

    # Cloud provider fields
    resource_id: Mapped[str] = mapped_column(String, nullable=True)

    # Common fields
    name: Mapped[str] = mapped_column(String, nullable=False)
    cidr: Mapped[IPv4Network] = mapped_column(CIDR, nullable=False)

    range_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("ranges.id", ondelete="CASCADE"),
        nullable=False,
    )
    range = relationship("RangeModel", back_populates="subnets")
