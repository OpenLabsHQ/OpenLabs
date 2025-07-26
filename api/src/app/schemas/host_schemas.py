from ipaddress import IPv4Address
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from src.app.enums.operating_systems import OpenLabsOS
from src.app.enums.specs import OpenLabsSpec

from ..enums.operating_systems import OS_SIZE_THRESHOLD
from ..validators.network import is_valid_disk_size, is_valid_hostname


class HostCommonSchema(BaseModel):
    """Common host attributes."""

    hostname: str = Field(
        ...,
        description="Hostname of host",
        min_length=1,
        max_length=63,  # GCP Max
        examples=["example-host-1"],
    )
    os: OpenLabsOS = Field(
        ...,
        description="Operating system of host",
        examples=[OpenLabsOS.DEBIAN_11, OpenLabsOS.KALI, OpenLabsOS.WINDOWS_2022],
    )
    spec: OpenLabsSpec = Field(
        ...,
        description="Ram and CPU size",
        examples=[OpenLabsSpec.TINY, OpenLabsSpec.SMALL],
    )
    size: int = Field(
        ..., description="Size in GB of disk", gt=0, examples=[8, 32, 40, 65]
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional list of tags",
        examples=[["web", "linux"]],
    )

    @field_validator("tags")
    @classmethod
    def unique_tags(cls, tags: list[str]) -> list[str]:
        """Validate all tags are unique."""
        if len(tags) != len(set(tags)):
            msg = "Host tags should be unique."
            raise ValueError(msg)
        return tags

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, tags: list[str]) -> list[str]:
        """Validate no empty tags."""
        if any(tag.strip() == "" for tag in tags):
            msg = "Host tags must not be empty."
            raise ValueError(msg)
        return tags

    @field_validator("tags")
    @classmethod
    def validate_tag_length(cls, tags: list[str]) -> list[str]:
        """Validate tags are 63 characters or less."""
        max_tag_length = 63  # GCP max
        for tag in tags:
            if len(tag) > max_tag_length:
                msg = f"Tags must be 63 characters or less. Shorten tag: {tag}"
                raise ValueError(msg)
        return tags

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, hostname: str) -> str:
        """Check VM hostname is conforms to RFC1035."""
        if not is_valid_hostname(hostname):
            msg = f"Invalid hostname: {hostname}"
            raise ValueError(msg)
        return hostname

    @model_validator(mode="after")
    def validate_size(self) -> Self:
        """Check VM disk size is sufficient."""
        if not is_valid_disk_size(self.os, self.size):
            msg = f"Disk size {self.size}GB too small for OS: {self.os.value}. Minimum disk size: {OS_SIZE_THRESHOLD[self.os]}GB."
            raise ValueError(msg)

        return self


# ==================== Blueprints =====================


class BlueprintHostBaseSchema(HostCommonSchema):
    """Base pydantic class for all blueprint host objects."""

    pass


class BlueprintHostCreateSchema(BlueprintHostBaseSchema):
    """Schema to create blueprint host objects."""

    model_config = ConfigDict(from_attributes=True)


class BlueprintHostSchema(BlueprintHostBaseSchema):
    """Blueprint host object."""

    id: int = Field(..., description="Blueprint host unique identifier.")

    model_config = ConfigDict(from_attributes=True)


class BlueprintHostHeaderSchema(BlueprintHostBaseSchema):
    """Header schema for blueprint host objects."""

    id: int = Field(..., description="Blueprint host unique identifier.")

    model_config = ConfigDict(from_attributes=True)


# ==================== Deployed (Instances) =====================


class DeployedHostBaseSchema(HostCommonSchema):
    """Base pydantic class for all deployed host objects."""

    resource_id: str = Field(
        ...,
        min_length=1,
        description="Host cloud resource ID.",
        examples=["i-05c770240dd042b88"],
    )
    ip_address: IPv4Address = Field(
        ..., description="IP address of deployed host.", examples=["192.168.1.59"]
    )


class DeployedHostCreateSchema(DeployedHostBaseSchema):
    """Schema to create deployed host objects."""

    model_config = ConfigDict(from_attributes=True)


class DeployedHostSchema(DeployedHostBaseSchema):
    """Deployed host object."""

    id: int = Field(..., description="Deployed host unique identifier.")

    model_config = ConfigDict(from_attributes=True)


class DeployedHostHeaderSchema(DeployedHostBaseSchema):
    """Header schema for deployed host objects."""

    id: int = Field(..., description="Deployed host unique identifier.")

    model_config = ConfigDict(from_attributes=True)
