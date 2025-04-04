import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .subnet_schema import SubnetBaseSchema
from .vpc_common_schema import VPCCommonSchema


class VPCBaseSchema(VPCCommonSchema):
    """Deployed VPC base schema."""

    resource_id: str = Field(
        ...,
        min_length=1,
        description="VPC cloud resource ID.",
        examples=["	vpc-05c770240dd042b88"],
    )

    subnets: list[SubnetBaseSchema] = Field(..., description="Contained subnets")

    @field_validator("subnets")
    @classmethod
    def validate_unique_subnet_names(
        cls, subnets: list[SubnetBaseSchema]
    ) -> list[SubnetBaseSchema]:
        """Check subnet names are unique.

        Args:
        ----
            cls: VPCBaseSchema object.
            subnets (list[SubnetBaseSchema]): Subnet objects.

        Returns:
        -------
            list[SubnetBaseSchema]: Subnet objects.

        """
        subnet_names = [subnet.name for subnet in subnets]
        if len(subnet_names) != len(set(subnet_names)):
            msg = "All subnet names must be unique."
            raise ValueError(msg)
        return subnets


class VPCID(BaseModel):
    """Identity class for the VPC object."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="Unique VPC identifier."
    )
    model_config = ConfigDict(from_attributes=True)


class VPCSchema(VPCBaseSchema, VPCID):
    """Deployed VPC schema."""

    model_config = ConfigDict(from_attributes=True)
