import uuid
from ipaddress import IPv4Address

from sqlalchemy import ARRAY, UUID, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from ..enums.operating_systems import OpenLabsOS
from ..enums.specs import OpenLabsSpec
from .common_models import OwnableObjectMixin


class HostModel(Base, OwnableObjectMixin):
    """SQLAlchemy ORM model for host objects."""

    __tablename__ = "hosts"

    # Cloud provider fields
    resource_id: Mapped[str] = mapped_column(String, nullable=True)
    ip: Mapped[IPv4Address] = mapped_column(INET, nullable=True)

    # Common fields
    hostname: Mapped[str] = mapped_column(String, nullable=False)
    os: Mapped[OpenLabsOS] = mapped_column(Enum(OpenLabsOS), nullable=False)
    spec: Mapped[OpenLabsSpec] = mapped_column(Enum(OpenLabsSpec), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String))

    range_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("ranges.id", ondelete="CASCADE"),
        nullable=False,
    )
    range = relationship("RangeModel", back_populates="hosts")
