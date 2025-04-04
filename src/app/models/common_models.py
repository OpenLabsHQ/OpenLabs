import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ..enums.providers import OpenLabsProvider


class OwnableObjectMixin(MappedAsDataclass):
    """Mixin to provide ownership and ID for each ownable object."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    # User who owns this template
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )


class OpenLabsUserMixin(MappedAsDataclass):
    """Mixin to provide a UUID for each user-based model."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )


class RangeMixin:
    """Common range attributes."""

    name: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[OpenLabsProvider] = mapped_column(
        Enum(OpenLabsProvider), nullable=False
    )
    vnc: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vpn: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
