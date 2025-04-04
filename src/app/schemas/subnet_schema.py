import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .host_schema import HostBaseSchema
from .subnet_common_schema import SubnetCommonSchema


class SubnetBaseSchema(SubnetCommonSchema):
    """Deployed subnet base schema."""

    resource_id: str = Field(
        ...,
        min_length=1,
        description="Subnet cloud resource ID.",
        examples=["subnet-05c770240dd042b88"],
    )

    hosts: list[HostBaseSchema] = Field(..., description="Contained hosts")

    @field_validator("hosts")
    @classmethod
    def validate_unique_hostnames(
        cls, hosts: list[HostBaseSchema]
    ) -> list[HostBaseSchema]:
        """Check hostnames are unique.

        Args:
        ----
            cls: SubnetBaseSchema object.
            hosts (list[HostBaseSchema]): Host objects.

        Returns:
        -------
            list[HostBaseSchema]: Host objects.

        """
        hostnames = [host.hostname for host in hosts]
        if len(hostnames) != len(set(hostnames)):
            msg = "All hostnames must be unique."
            raise ValueError(msg)
        return hosts


class SubnetID(BaseModel):
    """Identity class for the subnet object."""

    id: uuid.UUID = Field(..., description="Unique subnet identifier.")
    model_config = ConfigDict(from_attributes=True)


class SubnetSchema(SubnetBaseSchema, SubnetID):
    """Deployed subnet schema."""

    model_config = ConfigDict(from_attributes=True)
