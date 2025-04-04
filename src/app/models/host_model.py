import uuid
from ipaddress import IPv4Address

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .mixin_models import HostMixin, OwnableObjectMixin


class HostModel(Base, OwnableObjectMixin, HostMixin):
    """SQLAlchemy ORM model for host objects."""

    __tablename__ = "hosts"

    # Cloud provider fields
    resource_id: Mapped[str] = mapped_column(String, nullable=False)
    ip_address: Mapped[IPv4Address] = mapped_column(INET, nullable=False)

    # Parent relationship
    subnet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subnets.id", ondelete="CASCADE"),
        nullable=False,
    )
    subnet = relationship("SubnetModel", back_populates="hosts")
