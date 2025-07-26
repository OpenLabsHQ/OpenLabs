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
from ..validators.network import max_num_hosts_in_subnet
from .host_schemas import (
    BlueprintHostCreateSchema,
    BlueprintHostSchema,
    DeployedHostCreateSchema,
    DeployedHostSchema,
    HostCommonSchema,
)


class SubnetCommonSchema(BaseModel):
    """Common subnet attributes."""

    name: str = Field(
        ...,
        description="Subnet name.",
        pattern=OPENLABS_NAME_REGEX,
        examples=["example-subnet-1"],
    )

    cidr: IPv4Network = Field(
        ..., description="CIDR range.", examples=["192.168.1.0/24"]
    )


class SubnetCreateValidationMixin(BaseModel):
    """Mixin class with common validation for all subnet creation schemas."""

    # Forward references
    name: str
    cidr: IPv4Network
    hosts: Sequence[HostCommonSchema]

    @field_validator("cidr")
    @classmethod
    def validate_subnet_private_cidr_range(cls, cidr: IPv4Network) -> IPv4Network:
        """Check subnet CIDR ranges are private."""
        if not cidr.is_private:
            msg = "Subnets should only use private CIDR ranges."
            raise ValueError(msg)
        return cidr

    @model_validator(mode="after")
    def validate_unique_hostnames(self) -> Self:
        """Check hostnames are unique."""
        if not self.hosts:
            return self

        hostnames = [host.hostname for host in self.hosts]
        if len(hostnames) != len(set(hostnames)):
            msg = f"All hostnames in subnet: {self.name} must be unique."
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def validate_max_number_hosts(self) -> Self:
        """Check that the number of hosts does not exceed subnet CIDR."""
        max_num_hosts = max_num_hosts_in_subnet(self.cidr)

        if len(self.hosts) > max_num_hosts:
            msg = f"Too many hosts in subnet: {self.name}! Max: {max_num_hosts}, Requested: {len(self.hosts)}"
            raise ValueError(msg)

        return self


# ==================== Blueprints =====================


class BlueprintSubnetBaseSchema(SubnetCommonSchema):
    """Base pydantic class for all blueprint subnet objects."""

    pass


class BlueprintSubnetCreateSchema(
    BlueprintSubnetBaseSchema, SubnetCreateValidationMixin
):
    """Schema to create blueprint subnet objects."""

    hosts: list[BlueprintHostCreateSchema] = Field(
        ..., description="All blueprint hosts in the subnet."
    )


class BlueprintSubnetSchema(BlueprintSubnetBaseSchema):
    """Blueprint subnet object."""

    id: int = Field(..., description="Blueprint subnet unique identifier.")
    hosts: list[BlueprintHostSchema] = Field(
        ..., description="All blueprint hosts in the subnet."
    )

    model_config = ConfigDict(from_attributes=True)


class BlueprintSubnetHeaderSchema(BlueprintSubnetBaseSchema):
    """Header schema for blueprint subnet objects."""

    id: int = Field(..., description="Blueprint subnet unique identifier.")

    model_config = ConfigDict(from_attributes=True)


# ==================== Deployed (Instances) =====================


class DeployedSubnetBaseSchema(SubnetCommonSchema):
    """Base pydantic class for all deployed subnet objects."""

    resource_id: str = Field(
        ...,
        min_length=1,
        description="Deplyed subnet cloud resource ID.",
        examples=["subnet-05c770240dd042b88"],
    )


class DeployedSubnetCreateSchema(DeployedSubnetBaseSchema, SubnetCreateValidationMixin):
    """Schema to create deployed subnet objects."""

    hosts: list[DeployedHostCreateSchema] = Field(
        ..., description="Deployed hosts within subnet."
    )

    model_config = ConfigDict(from_attributes=True)


class DeployedSubnetSchema(DeployedSubnetBaseSchema):
    """Deployed subnet object."""

    id: int = Field(..., description="Deployed subnet unique identifier.")
    hosts: list[DeployedHostSchema] = Field(
        ..., description="Deployed hosts within subnet."
    )

    model_config = ConfigDict(from_attributes=True)


class DeployedSubnetHeaderSchema(DeployedSubnetBaseSchema):
    """Header schema for deployed subnet objects."""

    id: int = Field(..., description="Deployed subnet unique identifier.")

    model_config = ConfigDict(from_attributes=True)
