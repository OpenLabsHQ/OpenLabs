from ipaddress import IPv4Network

from pydantic import BaseModel, ConfigDict, Field

from ..enums.vpns import OpenLabsVPNType
from ..schemas.vpn_client_schemas import (
    BlueprintVPNClientCreateSchema,
    BlueprintVPNClientSchema,
)
from ..validators.names import OPENLABS_NAME_REGEX
from ..validators.network import DNSEntry


class VPNGatewayCommonSchema(BaseModel):
    """Base pydantic class for VPN gateways."""

    name: str = Field(
        ...,
        min_length=3,  # For documentation clarity
        pattern=OPENLABS_NAME_REGEX,
        description="Name of VPN gateway.",
    )
    type: OpenLabsVPNType = Field(
        ..., description="VPN gateway type.", examples=[OpenLabsVPNType.WIREGUARD]
    )


# ==================== Blueprints =====================


class BlueprintVPNGatewayBaseSchema(VPNGatewayCommonSchema):
    """Base pydantic class for blueprint VPN gateway objects."""

    cidr: IPv4Network | None = Field(
        default=None,
        description="VPN gateway CIDR range.",
        examples=["10.254.254.0/24"],
    )
    dns_servers: list[DNSEntry] = Field(
        default_factory=list,
        description="List of DNS servers used by all VPN clients associated with this VPN gateway.",
    )


class BlueprintVPNGatewayCreateSchema(BlueprintVPNGatewayBaseSchema):
    """Schema to create blueprint VPN gateways."""

    clients: list[BlueprintVPNClientCreateSchema] = Field(
        default_factory=list, description="VPN clients to create on deployment."
    )

    model_config = ConfigDict(from_attributes=True)


class BlueprintVPNGatewaySchema(BlueprintVPNGatewayBaseSchema):
    """Blueprint VPN gateway object."""

    id: int = Field(..., description="Blueprint VPN gateway unique identifier.")
    clients: list[BlueprintVPNClientSchema] = Field(
        default_factory=list, description="VPN clients to create on deployment."
    )

    model_config = ConfigDict(from_attributes=True)


# ==================== Deployed =====================


class DeployedVPNGatewayBaseSchema(VPNGatewayCommonSchema):
    """Base pydantic class for all deployed VPN gateway objects."""

    cidr: IPv4Network = Field(
        ..., description="VPN gateway CIDR range.", examples=["10.254.254.0/24"]
    )
    dns_servers: list[DNSEntry] = Field(
        ...,
        description="List of DNS servers used by all VPN clients associated with this VPN gateway.",
    )


class DeployedVPNGatewayCreateSchema(DeployedVPNGatewayBaseSchema):
    """Schema to create blueprint VPN gateways."""

    model_config = ConfigDict(from_attributes=True)


class DeployedVPNGatewaySchema(DeployedVPNGatewayBaseSchema):
    """Deployed VPN gateway schemas."""

    id: int = Field(..., description="Deployed VPN gateway unique identifier.")

    model_config = ConfigDict(from_attributes=True)
