import asyncio
import logging
import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

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
        deployment_id: str,
    ) -> None:
        """Initialize Pulumi base range object.

        Args:
            name: Name of the range to deploy
            range_obj: Blueprint or deployed range object
            region: Cloud region for deployment
            secrets: Cloud provider credentials
            description: Range description
            deployment_id: ID unique to deployment.

        Returns:
            None

        """
        self.name = name
        self.range_obj = range_obj
        self.region = region
        self.secrets = secrets
        self.description = description
        self.deployment_id = deployment_id

        # Generate stack name
        self.stack_name = (
            f"ol-{self.deployment_id}-{normalize_name(self.range_obj.name)}"
        )

        # Initial state
        self._is_deployed = False
        self._stack = None

    @abstractmethod
    def get_pulumi_program(self) -> Callable[[], None]:
        """Return Pulumi program function for this provider.

        Returns
        -------
        Callable[[], None]: Pulumi program function that defines infrastructure.

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

    @abstractmethod
    def get_cred_env_vars(self) -> dict[str, str]:
        """Return dictionary of cloud provider credential environment variables.

        Returns
        -------
            dict[str, str]: Dict of environment variables for cloud credentials.

        """
        pass

    def get_work_dir(self) -> Path:
        """Get Pulumi working directory."""
        return Path(f"{settings.PULUMI_DIR}/pulumi_stacks/{self.stack_name}")

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

            # Create or select stack with postgres backend
            env_vars: dict[str, str] = {
                "PULUMI_BACKEND_URL": settings.POSTGRES_URI,  # type: ignore
                "PULUMI_CONFIG_PASSPHRASE": settings.PULUMI_CONFIG_PASSPHRASE,
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
            env_vars.update(self.get_cred_env_vars())

            # Deploy with environment variables
            up_result = await asyncio.to_thread(
                self._stack.up,
                on_output=lambda output: logger.info("Pulumi output: %s", output),
            )

            if up_result.summary.result != "succeeded":
                msg = f"Pulumi deployment failed: {up_result.summary.result}"
                raise RuntimeError(msg)

            self._is_deployed = True

            # Parse outputs
            deployed_range = await self._parse_pulumi_outputs(dict(up_result.outputs))
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
                if not stack_created or not self._stack:
                    msg = "Failed to recreate Pulumi stack for destruction."
                    raise RuntimeError(msg)

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

    def _fill_missing_fields(
        self,
        schema: Any,  # noqa: ANN401
        outputs: dict[str, auto.OutputValue],
        prefix: str,
    ) -> dict[str, Any]:
        if not isinstance(schema, dict):
            return schema

        for key, value in schema.items():
            if value is None:
                kebab_key = f"{prefix}-{key.replace('_', '-')}"
                if kebab_key in outputs:
                    schema[key] = outputs[kebab_key].value
                continue  # Done with this key

            if isinstance(value, list):
                for item in value:
                    name_key = item.get("name") or item.get("hostname")
                    new_prefix = (
                        f"{prefix}-{normalize_name(name_key)}" if name_key else prefix
                    )
                    self._fill_missing_fields(item, outputs, new_prefix)
                continue  # Done with this key

            # If value is not None and not a list, do nothing (skip)
        return schema

    async def _parse_pulumi_outputs(
        self, outputs: dict[str, auto.OutputValue]
    ) -> DeployedRangeCreateSchema | None:
        """Parse Pulumi output values into a deployed range object.

        Args:
        ----
            outputs: Dictionary of Pulumi output values.

        Returns:
        -------
            DeployedRangeCreateSchema: The deployed range creation schema.

        """
        try:
            # Ensure all fields are present and empty ones are None
            dumped_schema = self.range_obj.model_dump(
                exclude_unset=False, exclude_none=False
            )

            # Recursively fill only None fields from outputs
            self._fill_missing_fields(dumped_schema, outputs, self.stack_name)

            # Add/overwrite static attributes
            dumped_schema["name"] = self.name
            dumped_schema["description"] = self.description
            dumped_schema["date"] = datetime.now(tz=timezone.utc)
            dumped_schema["readme"] = None
            dumped_schema["state_file"] = {}
            dumped_schema["state"] = RangeState.ON
            dumped_schema["region"] = self.region
            return DeployedRangeCreateSchema.model_validate(dumped_schema)
        except Exception as e:
            logger.exception("Error parsing Pulumi outputs: %s", e)
            return None

    def is_deployed(self) -> bool:
        """Return if range is currently deployed."""
        return self._is_deployed

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
