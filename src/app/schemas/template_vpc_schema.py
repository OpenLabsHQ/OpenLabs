import uuid
from ipaddress import IPv4Network

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from .template_subnet_schema import TemplateSubnetBaseSchema
from .vpc_common_schema import VPCCommonSchema


class TemplateVPCBaseSchema(VPCCommonSchema):
    """Template VPC object for OpenLabs."""

    subnets: list[TemplateSubnetBaseSchema] = Field(
        ..., description="Contained subnets"
    )

    @field_validator("subnets")
    @classmethod
    def validate_unique_subnet_names(
        cls, subnets: list[TemplateSubnetBaseSchema]
    ) -> list[TemplateSubnetBaseSchema]:
        """Check subnet names are unique.

        Args:
        ----
            cls: TemplateVPCBaseSchema object.
            subnets (list[TemplateSubnetBaseSchema]): Subnet objects.

        Returns:
        -------
            list[TemplateSubnetBaseSchema]: Subnet objects.

        """
        subnet_names = [subnet.name for subnet in subnets]
        if len(subnet_names) != len(set(subnet_names)):
            msg = "All subnet names must be unique."
            raise ValueError(msg)
        return subnets

    @field_validator("subnets")
    @classmethod
    def validate_subnets_contained(
        cls, subnets: list[TemplateSubnetBaseSchema], info: ValidationInfo
    ) -> list[TemplateSubnetBaseSchema]:
        """Check that the VPC CIDR contains all subnet CIDRs.

        Args:
        ----
            cls: TemplateVPCBaseSchema object.
            subnets (list[TemplateSubnetBaseSchema]): Subnet objects.
            info (ValidationInfo): Info of object currently being validated.

        Returns:
        -------
            list[TemplateSubnetBaseSchema]: List of subnet objects.

        """
        vpc_cidr = info.data.get("cidr")

        if not vpc_cidr:
            msg = "VPC missing CIDR."
            raise ValueError(msg)

        for subnet in subnets:
            if not subnet.cidr.subnet_of(vpc_cidr):
                msg = f"The following subnet is not contained in the VPC subnet {vpc_cidr}: {subnet.cidr}"
                raise ValueError(msg)

        return subnets


class TemplateVPCID(BaseModel):
    """Identity class for the template VPC object."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="Unique VPC identifier."
    )

    model_config = ConfigDict(from_attributes=True)


class TemplateVPCSchema(TemplateVPCBaseSchema, TemplateVPCID):
    """Template VPC object for OpenLabs."""

    model_config = ConfigDict(from_attributes=True)


class TemplateVPCHeaderSchema(TemplateVPCID):
    """Header (non-nested object) information for the TemplateVPCSchema."""

    cidr: IPv4Network = Field(
        ..., description="CIDR range", examples=["192.168.0.0/16"]
    )
    name: str = Field(
        ..., description="VPC name", min_length=1, examples=["example-vpc-1"]
    )
