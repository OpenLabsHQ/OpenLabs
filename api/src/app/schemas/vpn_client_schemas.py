from ipaddress import IPv4Address
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from ..enums.vpns import OpenLabsVPNType
from ..validators.names import OPENLABS_NAME_REGEX


class VPNClientCommonSchema(BaseModel):
    """Base pydantic class for VPN clients."""

    name: str = Field(
        ...,
        pattern=OPENLABS_NAME_REGEX,
        min_length=3,  # This is for documentation clarity
        description="Name of VPN client.",
    )


# ==================== Blueprints =====================


class BlueprintVPNClientBaseSchema(VPNClientCommonSchema):
    """Base pydantic class for blueprint VPN clients."""

    pass


class BlueprintVPNClientCreateSchema(BlueprintVPNClientBaseSchema):
    """Schema to create blueprint VPN clients."""

    model_config = ConfigDict(from_attributes=True)


class BlueprintVPNClientSchema(BlueprintVPNClientBaseSchema):
    """Blueprint VPN client object."""

    id: int = Field(..., description="Blueprint VPN client unique identifier.")

    model_config = ConfigDict(from_attributes=True)


# ==================== Deployed =====================


class VPNClientBaseSchema(VPNClientCommonSchema):
    """Base pydantic class for VPN client objects."""

    type: OpenLabsVPNType = Field(
        ..., description="VPN client type.", examples=[OpenLabsVPNType.WIREGUARD]
    )
    assigned_ip: IPv4Address = Field(..., description="VPN client IP address.")
    owner_id: int = Field(..., ge=0, description="ID of user who owns the VPN client.")


class WireguardVPNClientCreateSchema(VPNClientBaseSchema):
    """Schema to create Wireguard VPN clients."""

    type: Literal[OpenLabsVPNType.WIREGUARD] = OpenLabsVPNType.WIREGUARD
    wg_public_key: str = Field(..., description="Wireguard public key.")
    wg_private_key: str = Field(..., description="Wireguard private key.")


AnyVPNClientCreateSchema = Annotated[
    Union[WireguardVPNClientCreateSchema], Field(discriminator="type")
]
any_vpn_client_create_adapter = TypeAdapter(AnyVPNClientCreateSchema)


class WireguardVPNClientSchema(WireguardVPNClientCreateSchema):
    """Wireguard VPN client object."""

    id: int = Field(..., description="ID of VPN client.")

    model_config = ConfigDict(from_attributes=True)


AnyVPNClient = Annotated[Union[WireguardVPNClientSchema], Field(discriminator="type")]
any_vpn_client_adapter = TypeAdapter(AnyVPNClient)


class DeployedVPNClientCreateRequest(BaseModel):
    """Create request model for creating a new VPN client."""

    name: str = Field(
        ...,
        pattern=OPENLABS_NAME_REGEX,
        min_length=3,  # This is for documentation clarity
        description="A descriptive name for the VPN client (e.g., 'my-laptop').",
    )
    vpn_gateway_id: int = Field(
        ..., ge=0, description="VPN gateway the VPN client is associated with."
    )


class DeployedVPNClientSchema(VPNClientBaseSchema):
    """Generic model for VPN clients.

    Does not contain VPN type specific attributes.
    """

    id: int = Field(..., description="ID of VPN client.")

    model_config = ConfigDict(from_attributes=True)
