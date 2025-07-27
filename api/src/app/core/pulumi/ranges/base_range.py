import asyncio
import json
import logging
import os
import shutil
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os as aio_os
import pulumi.automation as auto

from ....enums.range_states import RangeState
from ....enums.regions import OpenLabsRegion
from ....schemas.range_schemas import (
    BlueprintRangeSchema,
    DeployedRangeCreateSchema,
    DeployedRangeSchema,
)
from ....schemas.secret_schema import SecretSchema
from ....utils.name_utils import normalize_name
from ...config import settings

# Configure logging
logger = logging.getLogger(__name__)


class AbstractBasePulumiRange(ABC):
    """Abstract class to enforce common functionality across range cloud providers."""

    name: str
    range_obj: BlueprintRangeSchema | DeployedRangeSchema
    state_data: dict[str, Any] | None  # Pulumi state data
    region: OpenLabsRegion
    stack_name: str
    secrets: SecretSchema
    deployed_range_name: str
    description: str

    # State variables
    _is_deployed: bool
    _stack: auto.Stack | None

    def __init__(  # noqa: PLR0913
        self,
        name: str,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        region: OpenLabsRegion,
        secrets: SecretSchema,
        description: str,
        state_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Pulumi base range object."""
        self.name = name
        self.range_obj = range_obj
        self.region = region
        self.secrets = secrets
        self.description = description
        self.state_data = state_data
        if not self.state_data:
            self._is_deployed = False
        else:
            self._is_deployed = True

        # Initial values
        # For new deployments, use a UUID. For destroy operations, extract from state if available
        if self.state_data and isinstance(self.state_data, dict):
            # Extract stack name from existing state data
            self.stack_name = self._extract_stack_name_from_state()
            self.unique_str = self.stack_name.split('-')[-1] if '-' in self.stack_name else str(uuid.uuid4())
        else:
            # New deployment - generate new UUID
            self.unique_str = uuid.uuid4()
            self.stack_name = f"{normalize_name(self.range_obj.name)}-{self.unique_str}"
        
        self.deployed_range_name = f"{normalize_name(self.name)}-{self.unique_str}"
        self._stack = None

    def _extract_stack_name_from_state(self) -> str:
        """Extract the stack name from stored Pulumi state data.
        
        Returns
        -------
        str: The original stack name used for deployment.
        
        """
        if not self.state_data or not isinstance(self.state_data, dict):
            # Fallback to UUID-based name
            return f"{normalize_name(self.range_obj.name)}-{uuid.uuid4()}"
        
        # Look for stack name in deployment data
        deployment = self.state_data.get("deployment", {})
        if isinstance(deployment, dict):
            # Try to find a resource with the stack URN pattern
            resources = deployment.get("resources", [])
            if isinstance(resources, list):
                for resource in resources:
                    if isinstance(resource, dict) and "urn" in resource:
                        urn = resource["urn"]
                        if isinstance(urn, str) and "pulumi:pulumi:Stack::" in urn:
                            # URN format: urn:pulumi:STACK_NAME::PROJECT::TYPE::NAME
                            parts = urn.split("::")
                            if len(parts) >= 2:
                                return parts[0].split(":")[-1]  # Extract stack name from URN
        
        # Fallback to creating a deterministic name based on range name
        return f"{normalize_name(self.range_obj.name)}-{normalize_name(self.name)}"

    @abstractmethod
    def get_pulumi_program(self) -> callable:
        """Return Pulumi program function for this provider.

        Returns
        -------
        callable: Pulumi program function that defines infrastructure.

        """
        pass

    @abstractmethod
    def has_secrets(self) -> bool:
        """Return if range has correct provider cloud credentials.

        Returns
        -------
            bool: True if correct provider creds exist. False otherwise.

        """
        pass

    @abstractmethod
    def get_config_values(self) -> dict[str, auto.ConfigValue]:
        """Return dictionary of Pulumi configuration values.

        Returns
        -------
            dict[str, auto.ConfigValue]: Dict of Pulumi configuration values.

        """
        pass

    async def _create_stack(self) -> bool:
        """Create Pulumi stack if it doesn't exist.

        Returns:
            bool: True if successful creation. False otherwise.

        """
        try:
            logger.info("Creating Pulumi stack: %s", self.stack_name)

            # Create workspace in temp directory
            work_dir = self.get_work_dir()
            await aio_os.makedirs(work_dir, exist_ok=True)
            
            # Create state directory for local backend
            state_dir = work_dir / "state"
            await aio_os.makedirs(state_dir, exist_ok=True)

            # Create or select stack with local workspace and environment variable backend
            env_vars = {
                "PULUMI_BACKEND_URL": f"file://{state_dir}",
                "PULUMI_CONFIG_PASSPHRASE": "",  # Disable encryption for local state
            }
            
            self._stack = await asyncio.to_thread(
                auto.create_or_select_stack,
                stack_name=self.stack_name,
                project_name="openlabs-ranges",
                program=self.get_pulumi_program(),
                opts=auto.LocalWorkspaceOptions(
                    work_dir=str(work_dir),
                    env_vars=env_vars,
                ),
            )

            # Install required plugins - Pulumi will auto-install during deployment
            # await asyncio.to_thread(
            #     self._stack.workspace.install_plugin, "aws", "v6.61.0"
            # )

            # Set configuration
            config_values = self.get_config_values()
            for key, value in config_values.items():
                await asyncio.to_thread(self._stack.set_config, key, value)

            logger.info("Pulumi stack created successfully: %s", self.stack_name)
            return True
        except Exception as e:
            logger.error(
                "Error creating Pulumi stack: %s. Error: %s",
                self.stack_name,
                e,
            )
            return False

    async def deploy(self) -> DeployedRangeCreateSchema | None:
        """Deploy infrastructure using Pulumi.

        Returns
        -------
            DeployedRangeCreateSchema: The deployed range creation schema to add to the database.

        """
        try:
            # Create stack
            stack_created = await self._create_stack()
            if not stack_created or not self._stack:
                msg = "Failed to create Pulumi stack."
                raise RuntimeError(msg)

            # Deploy infrastructure
            logger.info("Deploying selected range: %s", self.name)

            # Set environment variables for credentials
            env_vars = os.environ.copy()
            if hasattr(self, 'get_cred_env_vars'):
                env_vars.update(self.get_cred_env_vars())

            # Deploy with environment variables
            up_result = await asyncio.to_thread(
                self._stack.up,
                on_output=lambda output: logger.info("Pulumi output: %s", output),
            )

            if up_result.summary.result != "succeeded":
                msg = f"Pulumi deployment failed: {up_result.summary.result}"
                raise RuntimeError(msg)

            # Store state data - properly serialize Deployment object
            exported_state = await asyncio.to_thread(self._stack.export_stack)
            if hasattr(exported_state, 'deployment') and hasattr(exported_state, 'version'):
                # Create proper Pulumi state structure
                self.state_data = {
                    "version": exported_state.version,
                    "deployment": exported_state.deployment
                }
            elif isinstance(exported_state, dict):
                self.state_data = exported_state
            else:
                # Fallback - try to serialize the object
                try:
                    self.state_data = json.loads(json.dumps(exported_state, default=str))
                except (TypeError, ValueError):
                    self.state_data = {"version": 3, "deployment": {}}
            self._is_deployed = True

            # Parse outputs
            deployed_range = await self._parse_pulumi_outputs(up_result.outputs)
            if not deployed_range:
                msg = "Failed to parse Pulumi outputs!"
                raise RuntimeError(msg)

        except Exception as e:
            logger.exception("Error during deployment: %s", e)
            if self.is_deployed():
                destroy_success = await self.destroy()
                if not destroy_success:
                    logger.critical(
                        "Failed to cleanup after deployment failure of range: %s",
                        self.name,
                    )
            return None
        finally:
            # Cleanup workspace
            await self.cleanup_workspace()

        logger.info("Successfully deployed range: %s", self.name)
        return deployed_range

    async def destroy(self) -> bool:
        """Destroy Pulumi infrastructure.

        Returns
        -------
            bool: True if destroy was successful. False otherwise.

        """
        if not self.is_deployed():
            logger.error("Can't destroy range that is not deployed!")
            return False

        try:
            # Recreate stack if needed
            if not self._stack:
                stack_created = await self._create_stack()
                if not stack_created:
                    msg = "Failed to recreate Pulumi stack for destruction."
                    raise RuntimeError(msg)

                # Import state if we have it
                if self.state_data:
                    # Recreate Deployment object from stored state
                    if isinstance(self.state_data, dict) and "version" in self.state_data and "deployment" in self.state_data:
                        deployment = auto.Deployment(
                            version=self.state_data["version"],
                            deployment=self.state_data["deployment"]
                        )
                    else:
                        # Fallback for legacy format
                        deployment = auto.Deployment(self.state_data)
                    
                    await asyncio.to_thread(self._stack.import_stack, deployment)

            # Destroy infrastructure
            logger.info("Tearing down selected range: %s", self.name)
            destroy_result = await asyncio.to_thread(self._stack.destroy)

            if destroy_result.summary.result != "succeeded":
                msg = f"Pulumi destroy failed: {destroy_result.summary.result}"
                raise RuntimeError(msg)

            self._is_deployed = False
            logger.info("Successfully destroyed range: %s", self.name)
            return True

        except Exception as e:
            logger.exception("Error during destroy: %s", e)
            return False
        finally:
            # Cleanup workspace
            await self.cleanup_workspace()

    async def _parse_pulumi_outputs(  # noqa: PLR0911
        self, outputs: dict[str, auto.OutputValue]
    ) -> DeployedRangeCreateSchema | None:
        """Parse Pulumi output values into a deployed range object.

        Args:
        ----
            outputs: Dictionary of Pulumi output values.

        Returns
        -------
            DeployedRangeCreateSchema: The deployed range creation schema.

        """
        try:
            dumped_schema = self.range_obj.model_dump()

            # Range attributes
            jumpbox_key = next(
                (key for key in outputs if key.endswith("-JumpboxInstanceId")),
                None,
            )
            jumpbox_ip_key = next(
                (key for key in outputs if key.endswith("-JumpboxPublicIp")),
                None,
            )
            private_key = next(
                (key for key in outputs if key.endswith("-private-key")),
                None,
            )

            if not all([jumpbox_key, jumpbox_ip_key, private_key]):
                logger.error(
                    "Could not find required keys in Pulumi output: %s",
                    outputs.keys(),
                )
                return None

            dumped_schema["jumpbox_resource_id"] = outputs[jumpbox_key].value
            dumped_schema["jumpbox_public_ip"] = outputs[jumpbox_ip_key].value
            dumped_schema["range_private_key"] = outputs[private_key].value

            for x, vpc in enumerate(self.range_obj.vpcs):
                normalized_vpc_name = normalize_name(vpc.name)
                current_vpc = dumped_schema["vpcs"][x]
                
                vpc_key = next(
                    (
                        key
                        for key in outputs
                        if key.endswith(f"-{normalized_vpc_name}-resource-id")
                    ),
                    None,
                )
                if not vpc_key:
                    logger.error(
                        "Could not find VPC resource ID key for %s in Pulumi output",
                        normalized_vpc_name,
                    )
                    return None
                current_vpc["resource_id"] = outputs[vpc_key].value

                for y, subnet in enumerate(vpc.subnets):  # type: ignore
                    normalized_subnet_name = normalize_name(subnet.name)
                    current_subnet = current_vpc["subnets"][y]
                    
                    subnet_key = next(
                        (
                            key
                            for key in outputs
                            if key.endswith(
                                f"-{normalized_vpc_name}-{normalized_subnet_name}-resource-id"
                            )
                        ),
                        None,
                    )
                    if not subnet_key:
                        logger.error(
                            "Could not find subnet resource ID key for %s in %s in Pulumi output",
                            normalized_subnet_name,
                            normalized_vpc_name,
                        )
                        return None
                    current_subnet["resource_id"] = outputs[subnet_key].value

                    for z, host in enumerate(subnet.hosts):
                        current_host = current_subnet["hosts"][z]
                        
                        host_id_key = next(
                            (
                                key
                                for key in outputs
                                if key.endswith(
                                    f"-{normalized_vpc_name}-{normalized_subnet_name}-{host.hostname}-resource-id"
                                )
                            ),
                            None,
                        )
                        host_ip_key = next(
                            (
                                key
                                for key in outputs
                                if key.endswith(
                                    f"-{normalized_vpc_name}-{normalized_subnet_name}-{host.hostname}-private-ip"
                                )
                            ),
                            None,
                        )

                        if not host_id_key or not host_ip_key:
                            logger.error(
                                "Could not find host keys for %s in %s/%s in Pulumi output",
                                host.hostname,
                                normalized_vpc_name,
                                normalized_subnet_name,
                            )
                            return None

                        current_host["resource_id"] = outputs[host_id_key].value
                        current_host["ip_address"] = outputs[host_ip_key].value

        except KeyError as e:
            logger.exception(
                "Failed to parse Pulumi outputs. Missing key in output. Exception: %s",
                e,
            )
            return None
        except Exception as e:
            logger.exception(
                "Unknown error parsing Pulumi outputs. Exception: %s", e
            )
            return None

        # Add missing attributes
        dumped_schema["name"] = self.name
        dumped_schema["description"] = self.description
        dumped_schema["date"] = datetime.now(tz=timezone.utc)
        dumped_schema["readme"] = None
        
        # Add state data (already converted to dict in deploy method)
        dumped_schema["state_file"] = self.get_state_data() or {}
            
        dumped_schema["state"] = RangeState.ON
        dumped_schema["region"] = self.region

        return DeployedRangeCreateSchema.model_validate(dumped_schema)

    def is_deployed(self) -> bool:
        """Return if range is currently deployed."""
        return self._is_deployed

    def get_work_dir(self) -> Path:
        """Get Pulumi working directory."""
        return Path(f"{settings.CDKTF_DIR}/pulumi_stacks/{self.stack_name}")

    def get_state_data(self) -> dict[str, Any] | None:
        """Return state data content.

        Range must have been deployed or have state data passed on object creation.
        """
        return self.state_data

    async def cleanup_workspace(self) -> bool:
        """Delete Pulumi workspace files."""
        try:
            work_dir = self.get_work_dir()
            if await aio_os.path.exists(work_dir):
                await asyncio.to_thread(shutil.rmtree, work_dir)
            return True
        except Exception as e:
            logger.error(
                "Failed to delete workspace files for stack: %s. Error: %s",
                self.stack_name,
                e,
            )
            return False