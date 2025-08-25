from enum import Enum


class OpenLabsVPNType(str, Enum):
    """OpenLabs supported VPN types."""

    WIREGUARD = "wireguard"
