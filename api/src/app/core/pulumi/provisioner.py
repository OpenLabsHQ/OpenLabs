"""Central Pulumi provisioner using asynchronous context manager."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Self

import aiofiles.os as aio_os
import pulumi.automation as auto

from ...enums.providers import OpenLabsProvider
from ...enums.range_states import RangeState
from ...enums.regions import OpenLabsRegion
from ...schemas.range_schemas import (
    BlueprintRangeSchema,
    DeployedRangeCreateSchema,
    DeployedRangeSchema,
)
from ...schemas.secret_schema import SecretSchema
from ...utils.name_utils import normalize_name
from ..config import settings
from .providers.aws_provider import aws_provider
from .providers.protocol import PulumiProvider

# Configure logging
logger = logging.getLogger(__name__)

# Provider registry mapping OpenLabsProvider to provider instances
PULUMI_PROVIDER_REGISTRY: dict[OpenLabsProvider, PulumiProvider] = {
    OpenLabsProvider.AWS: aws_provider,
}


class PulumiOperation:
    """A self-contained context manager for a single Pulumi operation."""

    def __init__(  # noqa: PLR0913
        self,
        deployment_id: str,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        region: OpenLabsRegion,
        provider: OpenLabsProvider,
        secrets: SecretSchema,
        name: str,  # Display name for the range
        description: str,
    ) -> None:
        """Initialize the Pulumi operation context manager."""
        self.deployment_id = deployment_id
        self.range_obj = range_obj
        self.region = region
        self.secrets = secrets
        self.name = name
        self.description = description

        # Use the robust, consistent stack name we discussed previously
        self.stack_name = f"ol-{deployment_id}"
        self.work_dir = Path(f"{settings.PULUMI_DIR}/pulumi_stacks/{self.stack_name}")
        self.stack: auto.Stack | None = None

        # Get the Pulumi provider for the given OpenLabs provider
        pulumi_provider = PULUMI_PROVIDER_REGISTRY.get(provider)
        if not pulumi_provider:
            msg = f"Provider {provider.value} not found"
            raise ValueError(msg)
        self.pulumi_provider = pulumi_provider

    async def __aenter__(self) -> Self:
        """Create the workspace and initialize the Pulumi Stack object."""
        await aio_os.makedirs(self.work_dir, exist_ok=True)

        self.stack = await asyncio.to_thread(
            auto.create_or_select_stack,
            stack_name=self.stack_name,
            project_name="openlabs-ranges",
            program=self.pulumi_provider.get_pulumi_program(
                range_obj=self.range_obj,
                region=self.region,
                secrets=self.secrets,
                stack_name=self.stack_name,
            ),
            opts=auto.LocalWorkspaceOptions(
                work_dir=str(self.work_dir),
                env_vars={
                    "PULUMI_BACKEND_URL": str(settings.PULUMI_BACKEND_URL),
                    "PULUMI_CONFIG_PASSPHRASE": settings.PULUMI_CONFIG_PASSPHRASE,
                },
            ),
        )

        # Set the Pulumi configuration values
        config_values = self.pulumi_provider.get_config_values(
            self.region, self.secrets
        )
        self.stack.set_all_config(config_values)

        logger.info("Pulumi stack '%s' initialized.", self.stack_name)
        return self

    async def __aexit__(
        self, exc_type: Any, exc_val: Any, exc_tb: Any  # noqa: ANN401
    ) -> None:
        """Clean up Pulumi operation context.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        """
        if exc_type is not None:
            logger.error(
                "Pulumi operation %s completed with exception: %s - %s",
                self.stack_name,
                exc_type.__name__ if exc_type else "Unknown",
                str(exc_val) if exc_val else "No details",
            )
        else:
            logger.info("Pulumi operation %s completed successfully", self.stack_name)

        logger.info("Cleaning up Pulumi operation: %s", self.stack_name)
        # Note: We don't delete the workspace files as they may be needed for debugging
        # The stack object will be garbage collected automatically

    def _check_keys(self, keys: list[str], outputs: dict) -> None:
        """Private helper to check for required keys in the output."""
        if missing := set(keys) - set(outputs.keys()):
            msg = (
                f"Missing required keys in Pulumi outputs: {', '.join(sorted(missing))}"
            )
            raise RuntimeError(msg)

    def _parse_outputs(
        self,
        outputs: dict[str, auto.OutputValue],
    ) -> DeployedRangeCreateSchema:
        """Parse Pulumi output values into a deployed range object.

        Args:
            outputs: Dictionary of Pulumi output values
            range_obj: Original range object
            stack_name: Name of the Pulumi stack
            name: Name of the range
            description: Description of the range
            region: Cloud region
            deployment_id: Deployment ID

        Returns:
            The deployed range creation schema

        Raises:
            RuntimeError: If parsing fails

        """
        try:
            # Ensure all fields are present and empty ones are None
            dumped_schema = self.range_obj.model_dump(
                exclude_unset=False, exclude_none=False
            )

            # Range keys
            range_key_prefix = self.stack_name
            range_key_name = f"{range_key_prefix}-range-private-key"
            jumpbox_resource_id_key = f"{range_key_prefix}-jumpbox-resource-id"
            jumpbox_public_ip_key = f"{range_key_prefix}-jumpbox-public-ip"

            # Check that all required keys are present
            range_keys = [
                range_key_name,
                jumpbox_resource_id_key,
                jumpbox_public_ip_key,
            ]
            self._check_keys(range_keys, outputs)

            # Populate range keys
            dumped_schema["range_private_key"] = outputs[range_key_name].value
            dumped_schema["jumpbox_resource_id"] = outputs[
                jumpbox_resource_id_key
            ].value
            dumped_schema["jumpbox_public_ip"] = outputs[jumpbox_public_ip_key].value

            # Populate VPCs
            for i, vpc in enumerate(self.range_obj.vpcs):
                vpc_name = normalize_name(vpc.name)
                vpc_prefix = f"{self.stack_name}-{vpc_name}"

                # Check all required keys are present
                vpc_resource_id_key = f"{vpc_prefix}-resource-id"
                self._check_keys([vpc_resource_id_key], outputs)

                # Populate VPC keys
                dumped_schema["vpcs"][i]["resource_id"] = outputs[
                    vpc_resource_id_key
                ].value

                # Populate subnets
                for j, subnet in enumerate(vpc.subnets):  # type: ignore
                    subnet_prefix = f"{vpc_prefix}-{normalize_name(subnet.name)}"
                    subnet_resource_id_key = f"{subnet_prefix}-resource-id"

                    # Check all required keys are present
                    self._check_keys([subnet_resource_id_key], outputs)

                    # Populate subnet keys
                    dumped_schema["vpcs"][i]["subnets"][j]["resource_id"] = outputs[
                        subnet_resource_id_key
                    ].value

                    # Populate hosts
                    for k, host in enumerate(subnet.hosts):
                        host_prefix = f"{subnet_prefix}-{normalize_name(host.hostname)}"
                        host_resource_id_key = f"{host_prefix}-resource-id"
                        host_ip_address_key = f"{host_prefix}-ip-address"

                        # Check all required keys are present
                        self._check_keys(
                            [host_resource_id_key, host_ip_address_key], outputs
                        )

                        # Populate host keys
                        dumped_schema["vpcs"][i]["subnets"][j]["hosts"][k][
                            "resource_id"
                        ] = outputs[host_resource_id_key].value
                        dumped_schema["vpcs"][i]["subnets"][j]["hosts"][k][
                            "ip_address"
                        ] = outputs[host_ip_address_key].value

            # Add/overwrite static attributes
            dumped_schema["name"] = self.name
            dumped_schema["description"] = self.description
            dumped_schema["date"] = datetime.now(tz=timezone.utc)
            dumped_schema["readme"] = None
            dumped_schema["state"] = RangeState.ON
            dumped_schema["region"] = self.region
            dumped_schema["deployment_id"] = self.deployment_id
            return DeployedRangeCreateSchema.model_validate(dumped_schema)
        except Exception as e:
            logger.exception("Error parsing Pulumi outputs: %s", e)
            error_msg = f"Failed to parse Pulumi outputs: {e}"
            raise RuntimeError(error_msg) from e

    async def up(self) -> DeployedRangeCreateSchema:
        """High-level method to run 'up' and parse the results."""
        if not self.stack:
            msg = "Stack not initialized."
            raise RuntimeError(msg)

        logger.info("Applying infrastructure for stack '%s'.", self.stack_name)
        up_result = await asyncio.to_thread(self.stack.up, on_output=logger.info)

        if up_result.summary.result.lower() != "succeeded":
            msg = f"Pulumi up failed: {up_result.summary.result}"
            raise RuntimeError(msg)

        return self._parse_outputs(dict(up_result.outputs))

    async def destroy(self) -> None:
        """Run the Pulumi 'destroy' command."""
        if not self.stack:
            msg = "Stack not initialized."
            raise RuntimeError(msg)

        logger.info("Destroying infrastructure for stack '%s'.", self.stack_name)
        destroy_result = await asyncio.to_thread(
            self.stack.destroy, on_output=logger.info
        )

        if destroy_result.summary.result != "succeeded":
            msg = f"Pulumi destroy failed: {destroy_result.summary.result}"
            raise RuntimeError(msg)
