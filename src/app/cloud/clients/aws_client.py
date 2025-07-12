import logging
from typing import Any

import boto3

from ...enums.regions import AWS_REGION_MAP, OpenLabsRegion
from ...schemas.metadata_schemas import RangeMetadata
from ...schemas.resource_identity_schemas import AWSHostIdentity
from ..protocols.power_protocol import PowerControlProtocol

logger = logging.getLogger(__name__)


class AWSControlClient(PowerControlProtocol):
    """AWS cloud runtime control client."""

    def __init__(self, aws_access_key: str, aws_secret_key: str) -> None:
        """Instatiate AWS cloud runtime control client."""
        self._aws_access_key = aws_access_key
        self._aws_secret_key = aws_secret_key

        logger.debug("Successfully instantiated AWS control client.")

    def _create_boto_client(
        self, service_name: str, region_name: str
    ) -> Any:  # noqa: ANN401
        """Create a serivce and region specific boto3 client."""
        return boto3.client(
            service_name,
            aws_access_key_id=self._aws_access_key,
            aws_secret_access_key=self._aws_secret_key,
            region_name=region_name,
        )

    async def start_host(
        self,
        cloud_ids: list[AWSHostIdentity],
        region: OpenLabsRegion,
        range_metadata: AWS,
    ) -> bool:
        """Start/power on a host."""
        if not cloud_ids:
            logger.info("No AWS host IDs provided. Nothing to start!")
            return True

        instance_ids = [cloud_id.primary_id for cloud_id in cloud_ids]
        aws_region = AWS_REGION_MAP[region]

        ec2_client = self._create_boto_client("ec2", aws_region)

        for i in range(0, len(instance_ids), 100):
            chunk = instance_ids[i : i + 100]
            logger.debug("Processing start request for instances: %s", chunk)
            ec2_client.start_instances(InstanceIds=chunk)

        return True

    async def stop_host(self, identity: AWSHostIdentity) -> bool:
        """Stop/power off a host."""
        return True

    async def reboot_host(self, identity: AWSHostIdentity) -> bool:
        """Reboot/restart/power cycle a host."""
        return True
