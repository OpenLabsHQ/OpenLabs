import uuid
from ipaddress import IPv4Network

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, CIDR, UUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ..enums.operating_systems import OpenLabsOS
from ..enums.providers import OpenLabsProvider
from ..enums.specs import OpenLabsSpec


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


class RangeMixin(MappedAsDataclass):
    """Common range attributes."""

    name: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[OpenLabsProvider] = mapped_column(
        Enum(OpenLabsProvider), nullable=False
    )
    vnc: Mapped[bool] = mapped_column(Boolean, nullable=False)
    vpn: Mapped[bool] = mapped_column(Boolean, nullable=False)


class VPCMixin(MappedAsDataclass):
    """Common VPC attributes."""

    name: Mapped[str] = mapped_column(String, nullable=False)
    cidr: Mapped[IPv4Network] = mapped_column(CIDR, nullable=False)


class SubnetMixin(MappedAsDataclass):
    """Common Subnet attributes."""

    name: Mapped[str] = mapped_column(String, nullable=False)
    cidr: Mapped[IPv4Network] = mapped_column(CIDR, nullable=False)


class HostMixin(MappedAsDataclass):
    """Common Host attributes."""

    hostname: Mapped[str] = mapped_column(String, nullable=False)
    os: Mapped[OpenLabsOS] = mapped_column(Enum(OpenLabsOS), nullable=False)
    spec: Mapped[OpenLabsSpec] = mapped_column(Enum(OpenLabsSpec), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String))
