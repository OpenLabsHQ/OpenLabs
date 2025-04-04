import uuid
from ipaddress import IPv4Network

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from ..validators.network import max_num_hosts_in_subnet
from .subnet_common_schema import SubnetCommonSchema
from .template_host_schema import TemplateHostBaseSchema


class TemplateSubnetBaseSchema(SubnetCommonSchema):
    """Template subnet object for OpenLabs."""

    hosts: list[TemplateHostBaseSchema] = Field(..., description="All hosts in subnet")

    @field_validator("hosts")
    @classmethod
    def validate_unique_hostnames(
        cls, hosts: list[TemplateHostBaseSchema]
    ) -> list[TemplateHostBaseSchema]:
        """Check hostnames are unique.

        Args:
        ----
            cls: TemplateSubnetBaseSchema object.
            hosts (list[TemplateHostBaseSchema]): Host objects.

        Returns:
        -------
            list[TemplateHostBaseSchema]: Host objects.

        """
        hostnames = [host.hostname for host in hosts]
        if len(hostnames) != len(set(hostnames)):
            msg = "All hostnames must be unique."
            raise ValueError(msg)
        return hosts

    @field_validator("hosts")
    @classmethod
    def validate_max_number_hosts(
        cls, hosts: list[TemplateHostBaseSchema], info: ValidationInfo
    ) -> list[TemplateHostBaseSchema]:
        """Check that the number of hosts does not exceed subnet CIDR.

        Args:
        ----
            cls: TemplateSubnetBaseSchema object.
            hosts (list[TemplateHostBaseSchema]): List of host objects.
            info (ValidationInfo): Info of object currently being validated.

        Returns:
        -------
            list[TemplateHostBaseSchema]: List of host objects.

        """
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


class TemplateSubnetID(BaseModel):
    """Identiy class for tempalte subnet object."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="Unique subnet identifier."
    )

    model_config = ConfigDict(from_attributes=True)


class TemplateSubnetSchema(TemplateSubnetBaseSchema, TemplateSubnetID):
    """Template subnet object for OpenLabs."""

    model_config = ConfigDict(from_attributes=True)


class TemplateSubnetHeaderSchema(TemplateSubnetID):
    """Header (non-nested object) information for the TemplateSubnetSchema."""

    cidr: IPv4Network = Field(
        ..., description="CIDR range", examples=["192.168.1.0/24"]
    )
    name: str = Field(
        ..., description="Subnet name", min_length=1, examples=["example-subnet-1"]
    )
