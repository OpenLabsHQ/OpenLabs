from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
)

from ..enums.providers import OpenLabsProvider
from ..enums.range_states import RangeState
from ..enums.regions import OpenLabsRegion
from ..validators.network import mutually_exclusive_networks_v4
from .vpc_schemas import (
    BlueprintVPCCreateSchema,
    BlueprintVPCSchema,
    DeployedVPCCreateSchema,
    DeployedVPCSchema,
)


class RangeCommonSchema(BaseModel):
    """Common range attributes."""

    provider: OpenLabsProvider = Field(
        ...,
        description="Cloud provider for range.",
        examples=[OpenLabsProvider.AWS, OpenLabsProvider.AZURE],
    )
    name: str = Field(
        ..., min_length=1, max_length=63, examples=["openlabs-practice-1"]
    )
    vnc: bool = Field(default=False, description="Automatic VNC configuration.")
    vpn: bool = Field(default=False, description="Automatic VPN configuration.")


# ==================== Blueprints =====================


class BlueprintRangeBaseSchema(RangeCommonSchema):
    """Base pydantic class for blueprint range objects."""

    description: str | None = Field(
        default=None,
        max_length=300,  # Bluesky post limit
        description="Description of blueprint range.",
        examples=["This is my test range."],
    )

    pass


class BlueprintRangeCreateSchema(BlueprintRangeBaseSchema):
    """Schema to create blueprint range objects."""

    vpcs: list[BlueprintVPCCreateSchema] = Field(
        ..., description="All blueprint VPCs in range."
    )
    readers: list[int] = Field(
        default=[], description="List of user IDs with read access to this blueprint."
    )
    writers: list[int] = Field(
        default=[], description="List of user IDs with write access to this blueprint."
    )

    @field_validator("vpcs")
    @classmethod
    def validate_unique_vpc_names(
        cls, vpcs: list[BlueprintVPCCreateSchema], info: ValidationInfo
    ) -> list[BlueprintVPCCreateSchema]:
        """Check VPC names are unique."""
        vpc_names = [vpc.name for vpc in vpcs]

        if len(vpc_names) != len(set(vpc_names)):
            msg = "All VPCs in the range must have unique names."
            raise ValueError(msg)

        return vpcs

    @field_validator("vpcs")
    @classmethod
    def validate_mutually_exclusive_vpcs(
        cls, vpcs: list[BlueprintVPCCreateSchema], info: ValidationInfo
    ) -> list[BlueprintVPCCreateSchema]:
        """Check that VPCs do not overlap."""
        vpc_cidrs = [vpc.cidr for vpc in vpcs]

        if not mutually_exclusive_networks_v4(vpc_cidrs):

            msg = "All VPCs in range should be mutually exclusive (not overlap)."
            raise ValueError(msg)

        return vpcs


class BlueprintRangeSchema(BlueprintRangeBaseSchema):
    """Blueprint range object."""

    id: int = Field(..., description="Blueprint range unique identifier.")
    vpcs: list[BlueprintVPCSchema] = Field(
        ..., description="All blueprint VPCs in range."
    )

    @computed_field
    def readers(self) -> list[int]:
        """Get list of user IDs with read access."""
        if not hasattr(self, "permissions"):
            return []
        return [
            perm.user_id for perm in self.permissions if perm.permission_type == "read"
        ]

    @computed_field
    def writers(self) -> list[int]:
        """Get list of user IDs with write access."""
        if not hasattr(self, "permissions"):
            return []
        return [
            perm.user_id for perm in self.permissions if perm.permission_type == "write"
        ]

    model_config = ConfigDict(from_attributes=True)


class BlueprintRangeHeaderSchema(BlueprintRangeBaseSchema):
    """Header schema for blueprint range objects."""

    id: int = Field(..., description="Blueprint range unique identifier.")

    model_config = ConfigDict(from_attributes=True)


# ==================== Deployed (Instances) =====================


class DeployedRangeBaseSchema(RangeCommonSchema):
    """Base pydantic class for all deployed range objects."""

    description: str | None = Field(
        default=None,
        max_length=300,  # Bluesky post limit
        description="Description of range.",
        examples=["This is my test range."],
    )
    date: datetime = Field(
        description="Time range was created.",
        examples=[datetime(2025, 2, 5, tzinfo=timezone.utc)],
    )
    readme: str | None = Field(
        default=None, description="Markdown readme for deployed range."
    )
    state_file: dict[str, Any] = Field(..., description="Terraform state file.")
    state: RangeState = Field(
        ...,
        description="State of deployed range.",
        examples=[RangeState.ON, RangeState.OFF, RangeState.STARTING],
    )
    region: OpenLabsRegion = Field(
        ..., description="Cloud region of deployed range."
    )  # Add 3 more fields, Jumpbox cloud resource id, Jumpbox public IP address, SSH private key for range

    # Jumpbox attributes
    jumpbox_resource_id: str = Field(
        ...,
        min_length=1,
        description="Deplyed jumpbox host cloud resource ID.",
        examples=["i-05c770240dd042b88"],
    )
    jumpbox_public_ip: IPv4Address = Field(
        ...,
        description="Public IP address of deployed jumpbox.",
        examples=["1.1.1.1", "34.156.17.99"],
    )
    range_private_key: str = Field(
        ...,
        min_length=1,
        description="SSH private key for the range.",
    )


class DeployedRangeCreateSchema(DeployedRangeBaseSchema):
    """Schema to create deployed range object."""

    vpcs: list[DeployedVPCCreateSchema] = Field(
        ..., description="Deployed VPCs in the range."
    )
    readers: list[int] = Field(
        default=[],
        description="List of user IDs with read access to this deployed range.",
    )
    writers: list[int] = Field(
        default=[],
        description="List of user IDs with write access to this deployed range.",
    )
    executors: list[int] = Field(
        default=[],
        description="List of user IDs with execute access to this deployed range.",
    )

    @field_validator("vpcs")
    @classmethod
    def validate_unique_vpc_names(
        cls, vpcs: list[DeployedVPCCreateSchema], info: ValidationInfo
    ) -> list[DeployedVPCCreateSchema]:
        """Check VPC names are unique."""
        vpc_names = [vpc.name for vpc in vpcs]

        if len(vpc_names) != len(set(vpc_names)):
            msg = "All VPCs in the range must have unique names."
            raise ValueError(msg)

        return vpcs

    @field_validator("vpcs")
    @classmethod
    def validate_mutually_exclusive_vpcs(
        cls, vpcs: list[DeployedVPCCreateSchema], info: ValidationInfo
    ) -> list[DeployedVPCCreateSchema]:
        """Check that VPCs do not overlap."""
        vpc_cidrs = [vpc.cidr for vpc in vpcs]

        if not mutually_exclusive_networks_v4(vpc_cidrs):

            msg = "All VPCs in range should be mutually exclusive (not overlap)."
            raise ValueError(msg)

        return vpcs


class DeployedRangeSchema(DeployedRangeBaseSchema):
    """Deployed range object."""

    id: int = Field(..., description="Deployed range unique identifier.")
    vpcs: list[DeployedVPCSchema] = Field(
        ..., description="All deployed VPCs in the range."
    )

    @computed_field
    def readers(self) -> list[int]:
        """Get list of user IDs with read access."""
        if not hasattr(self, "permissions"):
            return []
        return [
            perm.user_id for perm in self.permissions if perm.permission_type == "read"
        ]

    @computed_field
    def writers(self) -> list[int]:
        """Get list of user IDs with write access."""
        if not hasattr(self, "permissions"):
            return []
        return [
            perm.user_id for perm in self.permissions if perm.permission_type == "write"
        ]

    @computed_field
    def executors(self) -> list[int]:
        """Get list of user IDs with execute access."""
        if not hasattr(self, "permissions"):
            return []
        return [
            perm.user_id
            for perm in self.permissions
            if perm.permission_type == "execute"
        ]

    model_config = ConfigDict(from_attributes=True)


class DeployedRangeHeaderSchema(RangeCommonSchema):
    """Header schema for depoyed range objects.

    Inherits from the common range schema to avoid sending
    the terraform state file and other expensive fields in
    the deployed range schema.

    """

    id: int = Field(..., description="Deployed range unique identifier.")
    description: str | None = Field(
        default=None,
        max_length=300,  # Bluesky post limit
        description="Description of range.",
        examples=["This is my test range."],
    )
    date: datetime = Field(
        description="Time range was created.",
        examples=[datetime(2025, 2, 5, tzinfo=timezone.utc)],
    )
    state: RangeState = Field(
        ...,
        description="State of deployed range.",
        examples=[RangeState.ON, RangeState.OFF, RangeState.STARTING],
    )
    region: OpenLabsRegion = Field(..., description="Cloud region of deployed range.")

    model_config = ConfigDict(from_attributes=True)


class DeployRangeSchema(BaseModel):
    """Payload schema for deploying ranges."""

    name: str = Field(
        ..., min_length=1, max_length=63, description="Name of deployed range."
    )
    description: str | None = Field(
        default=None,
        max_length=300,  # Bluesky post limit
        description="Description of deployed range.",
        examples=["This is my test range."],
    )
    blueprint_id: int = Field(..., description="ID of blueprint range to deploy.")
    region: OpenLabsRegion = Field(..., description="Cloud region of deployed range.")


class DeployedRangeKeySchema(BaseModel):
    """Deployed range SSH key schema."""

    range_private_key: str = Field(
        ...,
        min_length=1,
        description="SSH private key for the range.",
    )

    model_config = ConfigDict(from_attributes=True)
