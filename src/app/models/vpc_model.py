import uuid

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .mixin_models import OwnableObjectMixin, VPCMixin


class VPCModel(Base, OwnableObjectMixin, VPCMixin):
    """SQLAlchemy ORM model for VPC objects."""

    __tablename__ = "vpcs"

    resource_id: Mapped[str] = mapped_column(String, nullable=False)

    # Parent relationship
    range_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("ranges.id", ondelete="CASCADE"),
        nullable=False,
    )
    range = relationship("RangeModel", back_populates="vpcs")

    # Child relationship
    subnets = relationship(
        "SubnetModel",
        back_populates="vpc",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
