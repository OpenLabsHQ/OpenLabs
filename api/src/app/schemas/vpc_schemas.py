from ipaddress import IPv4Network
from typing import Self, Sequence

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from ..validators.names import OPENLABS_NAME_REGEX
from ..validators.network import all_subnets_contained, mutually_exclusive_networks_v4
from .subnet_schemas import (
    BlueprintSubnetCreateSchema,
    BlueprintSubnetSchema,
    DeployedSubnetCreateSchema,
    DeployedSubnetSchema,
    SubnetCommonSchema,
)


class VPCCommonSchema(BaseModel):
    """Common VPC attributes."""

    name: str = Field(
        ...,
        description="VPC name.",
        pattern=OPENLABS_NAME_REGEX,
        examples=["example-vpc-1"],
    )
    cidr: IPv4Network = Field(
        ..., description="CIDR range", examples=["192.168.0.0/16"]
    )


class VPCCreateValidationMixin(BaseModel):
    """Mixin class with common validation for all VPC creation schemas."""

    # Forward references
    name: str
    cidr: IPv4Network
    subnets: Sequence[SubnetCommonSchema]

    @field_validator("cidr")
    @classmethod
    def validate_vpc_private_cidr_range(cls, cidr: IPv4Network) -> IPv4Network:
        """Check VPC CIDR ranges are private."""
        if not cidr.is_private:
            msg = "VPCs should only use private CIDR ranges."
            raise ValueError(msg)
        return cidr

    @model_validator(mode="after")
    def validate_unique_subnet_names(self) -> Self:
        """Check subnet names are unique."""
        if not self.subnets:
            return self

        subnet_names = [subnet.name for subnet in self.subnets]
        if len(subnet_names) != len(set(subnet_names)):
            msg = f"All subnet in VPC: {self.name} must have unique names."
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def validate_subnets_contained(self) -> Self:
        """Check that the VPC CIDR contains all subnet CIDRs."""
        subnet_cidrs = [subnet.cidr for subnet in self.subnets]
        if not all_subnets_contained(self.cidr, subnet_cidrs):
            msg = f"All subnets in VPC: {self.name} should be contained within: {self.cidr}"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def validate_mutually_exclusive_subnets(self) -> Self:
        """Check that subnets do not overlap."""
        subnet_cidrs = [subnet.cidr for subnet in self.subnets]
        if not mutually_exclusive_networks_v4(subnet_cidrs):
            msg = f"All subnets in VPC: {self.name} should be mutually exclusive (not overlap)."
            raise ValueError(msg)

        return self


# ==================== Blueprints =====================


class BlueprintVPCBaseSchema(VPCCommonSchema):
    """Base pydantic class for all blueprint VPC objects."""

    pass


class BlueprintVPCCreateSchema(BlueprintVPCBaseSchema, VPCCreateValidationMixin):
    """Schema to create blueprint VPC objects."""

    subnets: list[BlueprintSubnetCreateSchema] = Field(
        ..., description="All blueprint subnets in VPC."
    )


class BlueprintVPCSchema(BlueprintVPCBaseSchema):
    """Blueprint VPC object."""

    id: int = Field(..., description="Blueprint VPC unique identifier.")
    subnets: list[BlueprintSubnetSchema] = Field(
        ..., description="All blueprint subnets in the VPC."
    )

    model_config = ConfigDict(from_attributes=True)


class BlueprintVPCHeaderSchema(BlueprintVPCBaseSchema):
    """Header schema for blueprint VPC objects."""

    id: int = Field(..., description="Blueprint VPC unique identifier.")

    model_config = ConfigDict(from_attributes=True)


# ==================== Deployed (Instances) =====================


class DeployedVPCBaseSchema(VPCCommonSchema):
    """Base pydantic class for all deployed VPC objects."""

    resource_id: str = Field(
        ...,
        min_length=1,
        description="Deplyed VPC cloud resource ID.",
        examples=["vpc-05c770240dd042b88"],
    )


class DeployedVPCCreateSchema(DeployedVPCBaseSchema, VPCCreateValidationMixin):
    """Schema to create deployed VPC objects."""

    subnets: list[DeployedSubnetCreateSchema] = Field(
        ..., description="Deployed subnets within VPC."
    )


class DeployedVPCSchema(DeployedVPCBaseSchema):
    """Deployed VPC object."""

    id: int = Field(..., description="Deployed VPC unique identifier.")
    subnets: list[DeployedSubnetSchema] = Field(
        ..., description="All deployed subnets in the VPC."
    )

    model_config = ConfigDict(from_attributes=True)


class DeployedVPCHeaderSchema(DeployedVPCBaseSchema):
    """Header schema for deployed VPC objects."""

    id: int = Field(..., description="Deployed VPC unique identifier.")

    model_config = ConfigDict(from_attributes=True)
