from ipaddress import IPv4Network

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from ..validators.network import max_num_hosts_in_subnet
from .host_schemas import (
    BlueprintHostCreateSchema,
    BlueprintHostSchema,
    DeployedHostCreateSchema,
    DeployedHostSchema,
)


class SubnetCommonSchema(BaseModel):
    """Common subnet attributes."""

    name: str = Field(
        ...,
        description="Subnet name.",
        min_length=1,
        max_length=63,  # GCP max
        examples=["example-subnet-1"],
    )

    cidr: IPv4Network = Field(
        ..., description="CIDR range.", examples=["192.168.1.0/24"]
    )


# ==================== Blueprints =====================


class BlueprintSubnetBaseSchema(SubnetCommonSchema):
    """Base pydantic class for all blueprint subnet objects."""

    pass


class BlueprintSubnetCreateSchema(BlueprintSubnetBaseSchema):
    """Schema to create blueprint subnet objects."""

    hosts: list[BlueprintHostCreateSchema] = Field(
        ..., description="All blueprint hosts in the subnet."
    )

    @field_validator("cidr")
    @classmethod
    def validate_subnet_private_cidr_range(cls, cidr: IPv4Network) -> IPv4Network:
        """Check subnet CIDR ranges are private."""
        if not cidr.is_private:
            msg = "Subnets should only use private CIDR ranges."
            raise ValueError(msg)
        return cidr

    @field_validator("hosts")
    @classmethod
    def validate_unique_hostnames(
        cls, hosts: list[BlueprintHostCreateSchema]
    ) -> list[BlueprintHostCreateSchema]:
        """Check hostnames are unique."""
        hostnames = [host.hostname for host in hosts]
        if len(hostnames) != len(set(hostnames)):
            msg = "All hostnames must be unique."
            raise ValueError(msg)
        return hosts

    @field_validator("hosts")
    @classmethod
    def validate_max_number_hosts(
        cls, hosts: list[BlueprintHostCreateSchema], info: ValidationInfo
    ) -> list[BlueprintHostCreateSchema]:
        """Check that the number of hosts does not exceed subnet CIDR."""
        subnet_cidr = info.data.get("cidr")

        if not subnet_cidr:
            msg = "Subnet missing CIDR."
            raise ValueError(msg)

        max_num_hosts = max_num_hosts_in_subnet(subnet_cidr)
        num_requested_hosts = len(hosts)

        if num_requested_hosts > max_num_hosts:
            msg = f"Too many hosts in subnet! Max: {max_num_hosts}, Requested: {num_requested_hosts}"
            raise ValueError(msg)

        return hosts


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


class DeployedSubnetCreateSchema(DeployedSubnetBaseSchema):
    """Schema to create deployed subnet objects."""

    hosts: list[DeployedHostCreateSchema] = Field(
        ..., description="Deployed hosts within subnet."
    )

    @field_validator("cidr")
    @classmethod
    def validate_subnet_private_cidr_range(cls, cidr: IPv4Network) -> IPv4Network:
        """Check subnet CIDR ranges are private."""
        if not cidr.is_private:
            msg = "Subnets should only use private CIDR ranges."
            raise ValueError(msg)
        return cidr

    @field_validator("hosts")
    @classmethod
    def validate_unique_hostnames(
        cls, hosts: list[DeployedHostCreateSchema]
    ) -> list[DeployedHostCreateSchema]:
        """Check hostnames are unique."""
        hostnames = [host.hostname for host in hosts]
        if len(hostnames) != len(set(hostnames)):
            msg = "All hostnames must be unique."
            raise ValueError(msg)
        return hosts

    @field_validator("hosts")
    @classmethod
    def validate_max_number_hosts(
        cls, hosts: list[DeployedHostCreateSchema], info: ValidationInfo
    ) -> list[DeployedHostCreateSchema]:
        """Check that the number of hosts does not exceed subnet CIDR."""
        subnet_cidr = info.data.get("cidr")

        if not subnet_cidr:
            msg = "Subnet missing CIDR."
            raise ValueError(msg)

        max_num_hosts = max_num_hosts_in_subnet(subnet_cidr)
        num_requested_hosts = len(hosts)

        if num_requested_hosts > max_num_hosts:
            msg = f"Too many hosts in subnet! Max: {max_num_hosts}, Requested: {num_requested_hosts}"
            raise ValueError(msg)

        return hosts

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
