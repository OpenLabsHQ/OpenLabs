from ipaddress import IPv4Network

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from ..validators.network import all_subnets_contained, mutually_exclusive_networks_v4
from .subnet_schemas import (
    BlueprintSubnetCreateSchema,
    BlueprintSubnetSchema,
    DeployedSubnetCreateSchema,
    DeployedSubnetSchema,
)


class VPCCommonSchema(BaseModel):
    """Common VPC attributes."""

    name: str = Field(
        ...,
        description="VPC name.",
        min_length=1,
        max_length=63,  # GCP Max
        examples=["example-vpc-1"],
    )
    cidr: IPv4Network = Field(
        ..., description="CIDR range", examples=["192.168.0.0/16"]
    )


# ==================== Blueprints =====================


class BlueprintVPCBaseSchema(VPCCommonSchema):
    """Base pydantic class for all blueprint VPC objects."""

    pass


class BlueprintVPCCreateSchema(BlueprintVPCBaseSchema):
    """Schema to create blueprint VPC objects."""

    subnets: list[BlueprintSubnetCreateSchema] = Field(
        ..., description="All blueprint subnets in VPC."
    )

    @field_validator("cidr")
    @classmethod
    def validate_vpc_private_cidr_range(cls, cidr: IPv4Network) -> IPv4Network:
        """Check VPC CIDR ranges are private."""
        if not cidr.is_private:
            msg = "VPCs should only use private CIDR ranges."
            raise ValueError(msg)
        return cidr

    @field_validator("subnets")
    @classmethod
    def validate_unique_subnet_names(
        cls, subnets: list[BlueprintSubnetCreateSchema], info: ValidationInfo
    ) -> list[BlueprintSubnetCreateSchema]:
        """Check subnet names are unique."""
        subnet_names = [subnet.name for subnet in subnets]

        if len(subnet_names) != len(set(subnet_names)):
            vpc_name = info.data.get("name")
            if not vpc_name:
                msg = "VPC is missing a name."
                raise ValueError(msg)

            msg = f"All subnet in VPC: {vpc_name} must have unique names."
            raise ValueError(msg)

        return subnets

    @field_validator("subnets")
    @classmethod
    def validate_subnets_contained(
        cls, subnets: list[BlueprintSubnetCreateSchema], info: ValidationInfo
    ) -> list[BlueprintSubnetCreateSchema]:
        """Check that the VPC CIDR contains all subnet CIDRs."""
        vpc_name = info.data.get("name")
        if not vpc_name:
            msg = "VPC is missing a name."
            raise ValueError(msg)

        vpc_cidr = info.data.get("cidr")
        if not vpc_cidr:
            msg = f"VPC: {vpc_name} missing CIDR."
            raise ValueError(msg)

        subnet_cidrs = [subnet.cidr for subnet in subnets]
        if not all_subnets_contained(vpc_cidr, subnet_cidrs):
            msg = (
                f"All subnets in VPC: {vpc_name} should be contained within: {vpc_cidr}"
            )
            raise ValueError(msg)

        return subnets

    @field_validator("subnets")
    @classmethod
    def validate_mutually_exclusive_subnets(
        cls, subnets: list[BlueprintSubnetCreateSchema], info: ValidationInfo
    ) -> list[BlueprintSubnetCreateSchema]:
        """Check that subnets do not overlap."""
        subnet_cidrs = [subnet.cidr for subnet in subnets]

        if not mutually_exclusive_networks_v4(subnet_cidrs):
            vpc_name = info.data.get("name")
            if not vpc_name:
                msg = "VPC is missing a name."
                raise ValueError(msg)

            msg = f"All subnets in VPC: {vpc_name} should be mutually exclusive (not overlap)."
            raise ValueError(msg)

        return subnets


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


class DeployedVPCCreateSchema(DeployedVPCBaseSchema):
    """Schema to create deployed VPC objects."""

    subnets: list[DeployedSubnetCreateSchema] = Field(
        ..., description="Deployed subnets within VPC."
    )

    @field_validator("cidr")
    @classmethod
    def validate_vpc_private_cidr_range(cls, cidr: IPv4Network) -> IPv4Network:
        """Check VPC CIDR ranges are private."""
        if not cidr.is_private:
            msg = "VPCs should only use private CIDR ranges."
            raise ValueError(msg)
        return cidr

    @field_validator("subnets")
    @classmethod
    def validate_unique_subnet_names(
        cls, subnets: list[DeployedSubnetCreateSchema], info: ValidationInfo
    ) -> list[DeployedSubnetCreateSchema]:
        """Check subnet names are unique."""
        subnet_names = [subnet.name for subnet in subnets]

        if len(subnet_names) != len(set(subnet_names)):
            vpc_name = info.data.get("name")
            if not vpc_name:
                msg = "VPC is missing a name."
                raise ValueError(msg)

            msg = f"All subnet in VPC: {vpc_name} must have unique names."
            raise ValueError(msg)

        return subnets

    @field_validator("subnets")
    @classmethod
    def validate_subnets_contained(
        cls, subnets: list[DeployedSubnetCreateSchema], info: ValidationInfo
    ) -> list[DeployedSubnetCreateSchema]:
        """Check that the VPC CIDR contains all subnet CIDRs."""
        vpc_name = info.data.get("name")
        if not vpc_name:
            msg = "VPC is missing a name."
            raise ValueError(msg)

        vpc_cidr = info.data.get("cidr")
        if not vpc_cidr:
            msg = f"VPC: {vpc_name} missing CIDR."
            raise ValueError(msg)

        subnet_cidrs = [subnet.cidr for subnet in subnets]
        if not all_subnets_contained(vpc_cidr, subnet_cidrs):
            msg = (
                f"All subnets in VPC: {vpc_name} should be contained within: {vpc_cidr}"
            )
            raise ValueError(msg)

        return subnets

    @field_validator("subnets")
    @classmethod
    def validate_mutually_exclusive_subnets(
        cls, subnets: list[DeployedSubnetCreateSchema], info: ValidationInfo
    ) -> list[DeployedSubnetCreateSchema]:
        """Check that subnets do not overlap."""
        subnet_cidrs = [subnet.cidr for subnet in subnets]

        if not mutually_exclusive_networks_v4(subnet_cidrs):
            vpc_name = info.data.get("name")
            if not vpc_name:
                msg = "VPC is missing a name."
                raise ValueError(msg)

            msg = f"All subnets in VPC: {vpc_name} should be mutually exclusive (not overlap)."
            raise ValueError(msg)

        return subnets


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
