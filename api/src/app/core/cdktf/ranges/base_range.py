import asyncio
import json
import logging
import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os as aio_os
from cdktf import App

from ....enums.range_states import RangeState
from ....enums.regions import OpenLabsRegion
from ....schemas.range_schemas import (
    BlueprintRangeSchema,
    DeployedRangeCreateSchema,
    DeployedRangeSchema,
)
from ....schemas.secret_schema import SecretSchema
from ....utils.cdktf_utils import gen_resource_logical_ids
from ....utils.hash_utils import generate_short_hash
from ....utils.name_utils import normalize_name
from ...config import settings
from ..stacks.base_stack import AbstractBaseStack

# Configure logging
logger = logging.getLogger(__name__)


class AbstractBaseRange(ABC):
    """Abstract class to enforce common functionality across range cloud providers."""

    # Mutex for terraform init calls
    _init_lock = asyncio.Lock()

    # State variables
    _is_synthesized: bool
    _is_deployed: bool

    def __init__(  # noqa: PLR0913
        self,
        name: str,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        region: OpenLabsRegion,
        secrets: SecretSchema,
        description: str,
        state_file: dict[str, Any] | None = None,
        deployment_id: str | None = None,
    ) -> None:
        """Initialize CDKTF base range object."""
        self.name = name
        self.range_obj = range_obj
        self.region = region
        self.secrets = secrets
        self.description = description
        self.state_file = state_file
        if not self.state_file:
            self._is_deployed = False
        else:
            self._is_deployed = True

        # A small hash to improve readability while
        # maintaining uniqueness of the deployment
        self.deployment_id = (
            deployment_id if deployment_id else generate_short_hash()[:10]
        )

        # Format names to prevent CDKTF errors
        self.stack_name = normalize_name(f"{self.range_obj.name}-{self.deployment_id}")
        self._is_synthesized = False
        self.deployed_range_name = normalize_name(f"{self.name}-{self.deployment_id}")

    @abstractmethod
    def get_provider_stack_class(self) -> type[AbstractBaseStack]:
        """Return specific provider stack class to instantiate.

        Returns
        -------
        type[AbstractBaseStack]: Provider stack class.

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
    def get_cred_env_vars(self) -> dict[str, Any]:
        """Return dictionary of BASH Terraform cloud credential environment variables.

        Returns
        -------
            dict[str, Any]: Dict of BASH environment variables.

        """
        pass

    async def synthesize(self) -> bool:
        """Abstract method to synthesize terraform configuration.

        Returns:
            bool: True if successful synthesis. False otherwise.

        """
        try:
            logger.info("Synthesizing selected range: %s", self.name)

            # Create CDKTF app
            app = App(outdir=settings.CDKTF_DIR)

            # Instantiate the correct provider stack
            stack_class = self.get_provider_stack_class()
            stack_class(
                scope=app,
                range_obj=self.range_obj,
                cdktf_id=self.stack_name,
                cdktf_dir=settings.CDKTF_DIR,
                region=self.region,
                range_name=self.deployed_range_name,
                deployment_id=self.deployment_id,
            )

            # Synthesize Terraform files
            await asyncio.to_thread(app.synth)
            logger.info(
                "Range: %s synthesized successfully as stack: %s",
                self.name,
                self.stack_name,
            )

            self._is_synthesized = True
            return True
        except Exception as e:
            logger.error(
                "Error during synthesis of range: %s with stack: %s. Error: %s",
                self.name,
                self.stack_name,
                e,
            )
            return False

    async def _async_run_command(
        self, command: list[str], with_creds: bool = False
    ) -> tuple[str, str, int | None]:
        """Run a command asynchronously in the synth directory.

        Args:
        ----
            command (list[str]): Command to run in a list format.
            with_creds (bool): Include cloud credentials in execution environment.

        Returns:
        -------
            str: Standard output.
            str: Standard error.
            int | None: Return code of command if available.

        """
        synth_dir = self.get_synth_dir()
        if not await aio_os.path.exists(synth_dir):
            msg = f"Synthesis directory does not exist: {synth_dir}"
            raise FileNotFoundError(msg)

        env = os.environ.copy()
        if with_creds:
            env.update(self.get_cred_env_vars())

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=synth_dir,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await process.communicate()
        stdout, stderr = stdout_bytes.decode().strip(), stderr_bytes.decode().strip()

        if stdout:
            logger.info(
                "Command `cd %s && %s` stdout:\n%s",
                synth_dir,
                " ".join(command),
                stdout,
            )
        if stderr:
            logger.warning(
                "Command `cd %s && %s` stderr:\n%s",
                synth_dir,
                " ".join(command),
                stderr,
            )

        return stdout, stderr, process.returncode

    async def _init(self) -> bool:
        """Run `terraform init` programatically.

        Returns
        -------
            bool: True if successfully initialized. False otherwise.

        """
        async with AbstractBaseRange._init_lock:
            logger.info("Acquired lock for terraform init.")
            init_command = ["terraform", "init"]
            _, _, return_code = await self._async_run_command(
                init_command, with_creds=False
            )

            if return_code != 0:
                logger.error("Terraform init failed.")
                return False

            logger.info("Terraform init completed successfully.")

            return True

    async def deploy(self) -> DeployedRangeCreateSchema | None:
        """Run `terraform deploy --auto-approve` programmatically.

        Returns
        -------
            DeployedRangeCreateSchema: The deployed range creation schema to add to the database.

        """
        if not self.is_synthesized():
            logger.error("Range to destroy is not synthesized!")
            return None

        try:
            # Terraform init
            init_success = await self._init()
            if not init_success:
                msg = "Terraform init failed."
                raise RuntimeError(msg)

            # Terraform apply
            logger.info("Deploying selected range: %s", self.name)

            # Resources are deployed continously during apply command
            self._is_deployed = True

            apply_command = ["terraform", "apply", "--auto-approve"]
            _, _, return_code = await self._async_run_command(
                apply_command, with_creds=True
            )

            if return_code != 0:
                msg = "Terraform apply failed."
                raise RuntimeError(msg)

            # Load state
            if await aio_os.path.exists(self.get_state_file_path()):
                async with aiofiles.open(
                    self.get_state_file_path(), "r", encoding="utf-8"
                ) as f:
                    content = await f.read()
                    self.state_file = json.loads(content)
            else:
                msg = f"State file was not created during deployment. Expected path: {self.get_state_file_path()}"
                raise FileNotFoundError(msg)

            # Parse output variables
            deployed_range = await self._parse_terraform_outputs()
            if not deployed_range:
                msg = "Failed to parse terraform outputs!"
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
            # Delete files made during deployment
            await self.cleanup_synth()

        logger.info("Successfully deployed range: %s", self.name)

        return deployed_range

    async def destroy(self) -> bool:
        """Destroy terraform infrastructure.

        Returns
        -------
            bool: True if destroy was successful. False otherwise.

        """
        if not self.is_deployed():
            logger.error("Can't destroy range that is not deployed!")
            return False

        if not self.is_synthesized():
            logger.error("Range to destory is not synthesized!")
            return False

        try:
            # Try to create the state file
            created_state_file = await self.create_state_file()
            if not created_state_file:
                logger.info(
                    "State file not saved! Unable to create a new one in the filesystem."
                )

            # Check for an existing state file to be used for destroying
            if not await aio_os.path.exists(self.get_state_file_path()):
                msg = f"Unable to destroy range: {self.name} missing state file!"
                raise FileNotFoundError(msg)

            # Terraform init
            init_success = await self._init()
            if not init_success:
                msg = "Terraform init failed."
                raise RuntimeError(msg)

            # Terraform destroy
            logger.info(
                "Tearing down selected range: %s",
                self.name,
            )
            destroy_command = ["terraform", "destroy", "--auto-approve"]
            _, _, return_code = await self._async_run_command(
                destroy_command, with_creds=True
            )

            if return_code != 0:
                msg = "Terraform destroy failed"
                raise RuntimeError(msg)

            self._is_deployed = False

            logger.info("Successfully destroyed range: %s", self.name)
            return True
        except Exception as e:
            logger.exception("Error during destroy: %s", e)
            return False
        finally:
            # Delete synth files
            await self.cleanup_synth()

    async def _parse_terraform_outputs(  # noqa: PLR0911
        self,
    ) -> DeployedRangeCreateSchema | None:
        """Parse Terraform output variables into a deployed range object.

        Internal class function should not be called externally.

        Returns
        -------
            DeployedRangeCreateSchema: The terraform deploy output rendered as a desployed range pydantic schema.

        """
        if not await aio_os.path.exists(self.get_state_file_path()):
            logger.error(
                "Failed to find state file at: %s when attempting to parse terraform outputs.",
                self.get_state_file_path(),
            )
            return None

        try:
            output_command = ["terraform", "output", "-json"]
            stdout, _, return_code = await self._async_run_command(
                output_command, with_creds=False
            )

            if return_code != 0 or not stdout:
                msg = "Terraform output failed"
                raise RuntimeError(msg)

            logger.info("Terraform output completed successfully.")

        except Exception as e:
            logger.exception("Failed to parse Terraform outputs: %s", e)
            return None

        # Parse Terraform Output variables
        raw_outputs = json.loads(stdout)
        dumped_schema = self.range_obj.model_dump()

        try:
            # Range attributes
            jumpbox_key = next(
                (key for key in raw_outputs if key.endswith("-JumpboxInstanceId")),
                None,
            )
            jumpbox_ip_key = next(
                (key for key in raw_outputs if key.endswith("-JumpboxPublicIp")),
                None,
            )
            private_key = next(
                (key for key in raw_outputs if key.endswith("-private-key")),
                None,
            )

            if not all([jumpbox_key, jumpbox_ip_key, private_key]):
                logger.error(
                    "Could not find required keys in Terraform output: %s",
                    raw_outputs.keys(),
                )
                return None

            dumped_schema["jumpbox_resource_id"] = raw_outputs[jumpbox_key]["value"]
            dumped_schema["jumpbox_public_ip"] = raw_outputs[jumpbox_ip_key]["value"]
            dumped_schema["range_private_key"] = raw_outputs[private_key]["value"]

            vpc_logical_ids = gen_resource_logical_ids(
                [vpc.name for vpc in self.range_obj.vpcs]
            )
            for x, vpc in enumerate(self.range_obj.vpcs):
                vpc_logical_id = vpc_logical_ids[vpc.name]
                current_vpc = dumped_schema["vpcs"][x]

                vpc_key = next(
                    (
                        key
                        for key in raw_outputs
                        if key.endswith(f"-{vpc_logical_id}-resource-id")
                    ),
                    None,
                )
                if not vpc_key:
                    logger.error(
                        "Could not find VPC resource ID key for %s in Terraform output",
                        vpc_logical_id,
                    )
                    return None
                current_vpc["resource_id"] = raw_outputs[vpc_key]["value"]

                subnet_logical_ids = gen_resource_logical_ids(
                    [subnet.name for subnet in vpc.subnets]  # type: ignore
                )
                for y, subnet in enumerate(vpc.subnets):  # type: ignore
                    subnet_logical_id = subnet_logical_ids[subnet.name]
                    current_subnet = current_vpc["subnets"][y]

                    subnet_key = next(
                        (
                            key
                            for key in raw_outputs
                            if key.endswith(
                                f"-{vpc_logical_id}-{subnet_logical_id}-resource-id"
                            )
                        ),
                        None,
                    )
                    if not subnet_key:
                        logger.error(
                            "Could not find subnet resource ID key for %s in %s in Terraform output",
                            subnet_logical_id,
                            vpc_logical_id,
                        )
                        return None
                    current_subnet["resource_id"] = raw_outputs[subnet_key]["value"]

                    for z, host in enumerate(subnet.hosts):
                        current_host = current_subnet["hosts"][z]
                        host_id_key = next(
                            (
                                key
                                for key in raw_outputs
                                if key.endswith(
                                    f"-{vpc_logical_id}-{subnet_logical_id}-{host.hostname}-resource-id"
                                )
                            ),
                            None,
                        )
                        host_ip_key = next(
                            (
                                key
                                for key in raw_outputs
                                if key.endswith(
                                    f"-{vpc_logical_id}-{subnet_logical_id}-{host.hostname}-private-ip"
                                )
                            ),
                            None,
                        )

                        if not host_id_key or not host_ip_key:
                            logger.error(
                                "Could not find host keys for %s in %s/%s in Terraform output",
                                host.hostname,
                                vpc_logical_id,
                                subnet_logical_id,
                            )
                            return None

                        current_host["resource_id"] = raw_outputs[host_id_key]["value"]
                        current_host["ip_address"] = raw_outputs[host_ip_key]["value"]
        except KeyError as e:
            logger.exception(
                "Failed to parse Terraform outputs. Missing key in output. Exception: %s",
                e,
            )
            return None
        except Exception as e:
            logger.exception(
                "Unknown error parsing Terraform outputs. Exception: %s", e
            )
            return None

        # Add missing attributes
        dumped_schema["name"] = self.name
        dumped_schema["description"] = self.description
        dumped_schema["date"] = datetime.now(tz=timezone.utc)
        dumped_schema["readme"] = None
        dumped_schema["state_file"] = self.get_state_file()
        dumped_schema["state"] = RangeState.ON
        dumped_schema["region"] = self.region

        return DeployedRangeCreateSchema.model_validate(dumped_schema)

    def is_synthesized(self) -> bool:
        """Return if range is currently synthesized."""
        return self._is_synthesized

    def is_deployed(self) -> bool:
        """Return if range is currently deployed."""
        return self._is_deployed

    def get_synth_dir(self) -> Path:
        """Get CDKTF synthesis directory."""
        return Path(f"{settings.CDKTF_DIR}/stacks/{self.stack_name}")

    def get_synth_file_path(self) -> Path:
        """Get path to terraform HCL from CDKTF synthesis."""
        return Path(f"{self.get_synth_dir()}/cdk.tf.json")

    def get_state_file(self) -> dict[str, Any] | None:
        """Return state file content.

        Range must have been deployed or have a state file passed on object creation.
        """
        return self.state_file

    def get_state_file_path(self) -> Path:
        """Get CDKTF state file path."""
        return self.get_synth_dir() / f"terraform.{self.stack_name}.tfstate"

    async def create_state_file(self) -> bool:
        """Create state file with contents.

        Range must have been deployed or have a state file passed on object creation.

        Returns
        -------
            bool: True if state file successfully written. False otherwise.

        """
        if not self.state_file:
            msg = f"Can't write state file none exists! Attempted on range: {self.name}"
            logger.warning(msg)
            return False

        json_string = json.dumps(self.state_file, indent=4)

        async with aiofiles.open(self.get_state_file_path(), mode="w") as file:
            await file.write(json_string)

        msg = f"Successfully created state file: {self.get_state_file_path()} "
        logger.info(msg)
        return True

    async def cleanup_synth(self) -> bool:
        """Delete Terraform files generated by CDKTF synthesis."""
        try:
            await asyncio.to_thread(shutil.rmtree, self.get_synth_dir())
            self._is_synthesized = False
            return True
        except Exception as e:
            logger.error(
                "Failed to delete synthesis files for stack: %s. Error: %s",
                self.stack_name,
                e,
            )
            return False
