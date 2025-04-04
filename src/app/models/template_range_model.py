from sqlalchemy.orm import relationship

from ..core.db.database import Base
from .mixin_models import OwnableObjectMixin, RangeMixin


class TemplateRangeModel(Base, OwnableObjectMixin, RangeMixin):
    """SQLAlchemy ORM model for template range objects."""

    __tablename__ = "range_templates"

    # One-to-many relationship with VPCs
    vpcs = relationship(
        "TemplateVPCModel",
        back_populates="range",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def is_standalone(self) -> bool:
        """Return whether host template model is a standalone model.

        Standalone means that the template is not part of a larger template.

        Returns
        -------
            bool: True if standalone. False otherwise.

        """
        # Ranges are currently the highest level template object
        return True
