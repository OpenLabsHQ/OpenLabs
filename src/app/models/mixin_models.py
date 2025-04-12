from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column


class OwnableObjectMixin(MappedAsDataclass):
    """Mixin to provide ownership and ID for each ownable object."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        init=False,  # Allow DB to generate ID
        comment="Primary key (BIGSERIAL)",
    )

    # User who owns this template
    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )


class OpenLabsUserMixin(MappedAsDataclass):
    """Mixin to provide an ID for each user-based model."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        init=False,  # Allow DB to generate ID
        comment="Primary key (BIGSERIAL)",
    )
