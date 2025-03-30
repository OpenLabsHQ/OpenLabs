import uuid
from ipaddress import IPv4Address

from sqlalchemy import ARRAY, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .common_models import OwnableObjectMixin


class HostModel(Base, OwnableObjectMixin):
    """SQLAlchemy ORM model for host objects."""

    __tablename__ = "hosts"

    provider_id: Mapped[str] = mapped_column(String, nullable=False)
    hostname: Mapped[str] = mapped_column(String, nullable=False)
    ip: Mapped[IPv4Address] = mapped_column(INET, nullable=False)

    range_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("ranges.id", ondelete="CASCADE"),
        nullable=False,
    )
    range = relationship("RangeModel", back_populates="HostModel")

    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default_factory=list)
