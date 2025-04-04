import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .mixin_models import HostMixin, OwnableObjectMixin


class TemplateHostModel(Base, OwnableObjectMixin, HostMixin):
    """SQLAlchemy ORM model for template host."""

    __tablename__ = "host_templates"

    # Relationship with Subnet
    subnet = relationship("TemplateSubnetModel", back_populates="hosts")

    # ForeignKey to ensure each Host belongs to exactly one Subnet
    subnet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subnet_templates.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )

    def is_standalone(self) -> bool:
        """Return whether host template model is a standalone model.

        Standalone means that the template is not part of a larger template.

        Returns
        -------
            bool: True if standalone. False otherwise.

        """
        return self.subnet_id is None
