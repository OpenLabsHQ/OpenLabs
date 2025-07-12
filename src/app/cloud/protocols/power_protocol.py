from typing import Protocol

from ...enums.providers import OpenLabsProvider
from ...enums.regions import OpenLabsRegion
from ...schemas.metadata_schemas import RangeMetadata
from ...schemas.resource_identity_schemas import HostIdentity
from ..clients.aws_client import AWSControlClient


class PowerControlProtocol(Protocol):
    """Contract for host power operations."""

    async def start_host(
        self,
        cloud_id: HostIdentity,
        region: OpenLabsRegion,
        range_metadata: RangeMetadata,
    ) -> bool:
        """Start/power on a host."""

    async def stop_host(
        self,
        cloud_id: HostIdentity,
        region: OpenLabsRegion,
        range_metadata: RangeMetadata,
    ) -> bool:
        """Stop/power off a host."""

    async def reboot_host(
        self,
        cloud_id: HostIdentity,
        region: OpenLabsRegion,
        range_metadata: RangeMetadata,
    ) -> bool:
        """Reboot/restart/power cycle a host."""


# NOTE: Only register a client here once it supports the protocol.
POWER_CONTROL_FACTORY: dict[OpenLabsProvider, type[PowerControlProtocol]] = {
    OpenLabsProvider.AWS: AWSControlClient
}


def get_power_controller(provider: OpenLabsProvider) -> PowerControlProtocol:
    """Get the cloud provider client that supports the power controller protocol."""
    controller_class = POWER_CONTROL_FACTORY.get(provider)
    if not controller_class:
        msg = f"No power controller found for provider: {provider.value}"
        raise NotImplementedError(msg)
    return controller_class()
