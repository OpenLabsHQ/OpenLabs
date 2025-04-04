import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .mixin_models import OwnableObjectMixin, SubnetMixin


class TemplateSubnetModel(Base, OwnableObjectMixin, SubnetMixin):
    """SQLAlchemy ORM model for template subnet objects."""

    __tablename__ = "subnet_templates"

    # ForeignKey to ensure each Subnet belongs to exactly one VPC
    vpc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vpc_templates.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )

    # Relationship with VPC
    vpc = relationship("TemplateVPCModel", back_populates="subnets")

    # One-to-many relationship with Hosts
    hosts = relationship(
        "TemplateHostModel",
        back_populates="subnet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def is_standalone(self) -> bool:
        """Return whether subnet template model is a standalone model.

        Standalone means that the template is not part of a larger template.

        Returns
        -------
            bool: True if standalone. False otherwise.

        """
        return self.vpc_id is None
