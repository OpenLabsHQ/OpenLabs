from ipaddress import IPv4Network

from pydantic import BaseModel, Field


class SubnetCommonSchema(BaseModel):
    """Common subnet attributes."""

    cidr: IPv4Network = Field(
        ..., description="CIDR range", examples=["192.168.1.0/24"]
    )
    name: str = Field(
        ..., description="Subnet name", min_length=1, examples=["example-subnet-1"]
    )
