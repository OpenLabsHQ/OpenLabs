from ipaddress import IPv4Address

from pydantic import BaseModel, ConfigDict, Field

from ..validators.names import OPENLABS_NAME_REGEX


class VPNClientBaseSchema(BaseModel):
    """Base pydantic class for all vpn client objects."""

    name: str = Field(..., min_length=1, description="Name of VPN client.")

    # Wireguard
    wg_public_key: str = Field(..., min_length=3, description="Wireguard public key.")
    wg_assigned_ip: IPv4Address = Field(..., description="Wireguard client IP address.")
    wg_config_file: str = Field(..., description="Wireguard config file.")

    range_id: int = Field(..., ge=0, description="ID of associated range.")


class VPNClientCreateSchema(VPNClientBaseSchema):
    """Schema to create a VPN client object."""

    model_config = ConfigDict(from_attributes=True)


class VPNClientSchema(VPNClientBaseSchema):
    """VPN client object."""

    id: int = Field(..., description="ID of VPN client.")

    model_config = ConfigDict(from_attributes=True)


class VPNClientCreateRequest(BaseModel):
    """Request model for creating a new VPN client."""

    name: str = Field(
        ...,
        pattern=OPENLABS_NAME_REGEX,
        description="A descriptive name for the VPN client (e.g., 'my-laptop').",
    )
