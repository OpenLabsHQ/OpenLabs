import uuid

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .mixin_models import OwnableObjectMixin, SubnetMixin


class SubnetModel(Base, OwnableObjectMixin, SubnetMixin):
    """SQLAlchemy ORM model for subnet objects."""

    __tablename__ = "subnets"

    resource_id: Mapped[str] = mapped_column(String, nullable=False)

    # Parent relationship
    vpc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vpcs.id", ondelete="CASCADE"),
        nullable=False,
    )
    vpc = relationship("VPCModel", back_populates="subnets")

    # Child relationship
    hosts = relationship(
        "HostModel",
        back_populates="subnet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
