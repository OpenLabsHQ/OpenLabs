import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ..core.db.database import Base
from ..enums.permissions import PermissionEntityType, PermissionType


class TemplatePermissionModel(Base, MappedAsDataclass):
    """SQLAlchemy ORM model for template permissions."""

    __tablename__ = "template_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    # The template this permission applies to
    # We need polymorphic references as permissions can apply to any template type
    template_type: Mapped[str] = mapped_column(String, nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # The entity this permission is granted to
    entity_type: Mapped[PermissionEntityType] = mapped_column(
        Enum(PermissionEntityType),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # The type of permission
    permission_type: Mapped[PermissionType] = mapped_column(
        Enum(PermissionType),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        init=False,
    )
