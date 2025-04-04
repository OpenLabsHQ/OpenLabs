from ipaddress import IPv4Network

from pydantic import BaseModel, Field


class VPCCommonSchema(BaseModel):
    """Common VPC attributes."""

    cidr: IPv4Network = Field(
        ..., description="CIDR range", examples=["192.168.0.0/16"]
    )
    name: str = Field(
        ..., description="VPC name", min_length=1, examples=["example-vpc-1"]
    )
