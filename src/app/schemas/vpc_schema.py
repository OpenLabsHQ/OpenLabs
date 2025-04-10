import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .subnet_schema import SubnetBaseSchema, SubnetSchema
from .vpc_common_schema import VPCCommonSchema


class VPCBaseSchema(VPCCommonSchema):
    """Deployed VPC base schema."""

    resource_id: str = Field(
        ...,
        min_length=1,
        description="VPC cloud resource ID.",
        examples=["	vpc-05c770240dd042b88"],
    )


class VPCID(BaseModel):
    """Identity class for the VPC object."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="Unique VPC identifier."
    )
    model_config = ConfigDict(from_attributes=True)


class VPCSchema(VPCBaseSchema, VPCID):
    """Deployed VPC schema."""

    subnets: list[SubnetSchema] = Field(..., description="Contained subnets")

    model_config = ConfigDict(from_attributes=True)
