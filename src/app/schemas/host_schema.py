import uuid
from ipaddress import IPv4Address

from pydantic import BaseModel, ConfigDict, Field

from .host_common_schema import HostCommonSchema


class HostBaseSchema(HostCommonSchema):
    """Deployed host base schema."""

    resource_id: str = Field(
        ...,
        min_length=1,
        description="Host cloud resource ID.",
        examples=["i-05c770240dd042b88"],
    )
    ip_address: IPv4Address = Field(
        ..., description="IP address of deployed host.", examples=["192.168.1.59/24"]
    )


class HostID(BaseModel):
    """Identity class for the host object."""

    id: uuid.UUID = Field(..., description="Unique host identifier.")
    model_config = ConfigDict(from_attributes=True)


class HostSchema(HostBaseSchema, HostID):
    """Deployed host schema."""

    model_config = ConfigDict(from_attributes=True)
