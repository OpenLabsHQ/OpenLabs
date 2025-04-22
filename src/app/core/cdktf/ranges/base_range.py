from datetime import datetime, timezone
import json
import logging
import os
import shutil
import subprocess
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from cdktf import App

from ....enums.regions import OpenLabsRegion
from ....enums.providers import OpenLabsProvider
from ....enums.range_states import RangeState
from ....schemas.range_schemas import BlueprintRangeSchema, DeployedRangeCreateSchema, DeployedRangeSchema
from ....schemas.secret_schema import SecretSchema
from ...config import settings
from ..stacks.base_stack import AbstractBaseStack

# Configure logging
logger = logging.getLogger(__name__)


class AbstractBaseRange(ABC):
    """Abstract class to enforce common functionality across range cloud providers."""

    name: str
    range_obj: BlueprintRangeSchema | DeployedRangeSchema
    state_file: dict[str, Any] | None  # Terraform state
    region: OpenLabsRegion
    stack_name: str
    secrets: SecretSchema
    deployed_range_name: str
    description: str

    # State variables
    _is_synthesized: bool
    _is_deployed: bool

    def __init__(
        self,
        name: str,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        region: OpenLabsRegion,
        secrets: SecretSchema,
        description: str,
        state_file: dict[str, Any] | None = None,
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

        # Initial values
        self.unique_str = uuid.uuid4()
        # Remove spaces to avoid CDKTF errors
        self.stack_name = f"{self.range_obj.name.replace(' ', '')}-{self.unique_str}"
        self._is_synthesized = False
        self.deployed_range_name = f"{self.name.replace(' ', '')}-{self.unique_str}"

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

    def synthesize(self) -> bool:
        """Abstract method to synthesize terraform configuration.

        Returns:
            bool: True if successful synthesis. False otherwise.

        """
        try:
            logger.info(
                "Synthesizing selected range: %s from blueprint: %s",
                self.name,
                self.range_obj.name,
            )

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
            )

            # Synthesize Terraform files
            app.synth()
            logger.info(
                "Range: %s synthesized successfully as: %s",
                self.name,
                self.stack_name,
            )

            self._is_synthesized = True
            return True
        except Exception as e:
            logger.error(
                "Error during synthesis of stack: %s. Error: %s", self.stack_name, e
            )
            return False

    def deploy(self) -> DeployedRangeCreateSchema | None:
        """Run `terraform deploy --auto-approve` programmatically.

        Returns
        -------
            DeployedRangeCreateSchema: True if successfully deployed range. False otherwise.

        """
        if not self.is_synthesized():
            logger.error("Range to destroy is not synthesized!")
            return None

        try:
            initial_dir = os.getcwd()
            os.chdir(self.get_synth_dir())
            subprocess.run(["terraform", "init"], check=True)  # noqa: S603, S607

            # Terraform apply
            env = os.environ.copy()
            env.update(self.get_cred_env_vars())
            logger.info("Deploying selected range: %s", self.name)
            self._is_deployed = True # To allow for clean up if apply fails
            subprocess.run(  # noqa: S603
                ["terraform", "apply", "--auto-approve"],  # noqa: S607
                check=True,
                env=env,
            )

            # Load state
            state_file_path = self.get_state_file_path()
            if state_file_path.exists():
                with open(state_file_path, "r", encoding="utf-8") as file:
                    self.state_file = json.loads(file.read())
            else:
                msg = f"State file was not created during deployment. Expected path: {state_file_path}"
                logger.error(msg)
                return FileNotFoundError(msg)

            # Parse output variables
            deployed_range = self.parse_terraform_outputs()
            if not deployed_range:
                return None

            logger.info("Successfully deployed range: %s", self.name)
        except subprocess.CalledProcessError as e:
            logger.error("Terraform command failed: %s", e)
            if not self.destroy():
                logger.error("Failed to cleanup after deployment failure.")
            return None
        except Exception as e:
            logger.error("Error during deployment: %s", e)
            if not self.destroy():
                logger.error("Failed to cleanup after deployment failure.")
            return None

        # Delete files made during deployment
        os.chdir(initial_dir)
        self.cleanup_synth() 

        return deployed_range

    def destroy(self) -> bool:
        """Destroy terraform infrastructure.

        Args:
        ----
            stack_dir (str): Output directory.
            stack_name (str): Name of stack used to deploy the range (format: <range name>-<range id>) to tear down the range.

        Returns:
        -------
            None

        """
        if not self.is_deployed():
            logger.error("Can't destroy range that is not deployed!")
            return False

        if not self.is_synthesized():
            logger.error("Range to destory is not synthesized!")
            return False

        try:
            # Change to directory with `cdk.tf.json`
            initial_dir = os.getcwd()
            os.chdir(self.get_synth_dir())
            if not self.create_state_file():
                msg = f"Unable to destroy range: {self.name} missing state file!"
                raise ValueError(msg)

            # Run Terraform commands
            env = os.environ.copy()
            env.update(self.get_cred_env_vars())
            logger.info(
                "Tearing down selected range: %s",
                self.name,
            )
            subprocess.run(["terraform", "init"], check=True)  # noqa: S603, S607
            subprocess.run(  # noqa: S603
                ["terraform", "destroy", "--auto-approve"],  # noqa: S607
                check=True,
                env=env,
            )

            os.chdir(initial_dir)

            # Delete synth files
            self.cleanup_synth()
            self._is_deployed = False

            logger.info("Successfully destroyed range: %s", self.name)
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Terraform command failed: %s", e)
            return False
        except Exception as e:
            logger.error("Error during destroy: %s", e)
            return False

    def parse_terraform_outputs(self) -> dict[str, Any] | None:
        """Parse Terraform output variables into a deployed range object."""
        state_file_path = self.get_state_file_path()
        if not state_file_path.exists():
            logger.error("Failed to find state file at: %s when attempting to parse Terraform outputs.", state_file_path)
            return None
        
        # Change to directory with state file
        os.chdir(state_file_path.parent)

        try:
            result = subprocess.run(
                ["terraform", "output", "-json"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error("Failed to parse Terraform outputs: %s", e)
            return None
        
        # Parse Terraform Output variables
        raw_outputs = json.loads(result.stdout)
        dumped_schema = self.range_obj.model_dump()

        try:
            # Range attributes
            jumpbox_key = next((key for key in raw_outputs.keys() if key.endswith("-JumpboxInstanceId")), None)
            jumpbox_ip_key = next((key for key in raw_outputs.keys() if key.endswith("-JumpboxPublicIp")), None)
            private_key = next((key for key in raw_outputs.keys() if key.endswith("-private-key")), None)
            
            if not all([jumpbox_key, jumpbox_ip_key, private_key]):
                logger.error("Could not find required keys in Terraform output: %s", raw_outputs.keys())
                return None
                
            dumped_schema["jumpbox_resource_id"] = raw_outputs[jumpbox_key]["value"]
            dumped_schema["jumpbox_public_ip"] = raw_outputs[jumpbox_ip_key]["value"]
            dumped_schema["range_private_key"] = raw_outputs[private_key]["value"]

            
            for x, vpc in enumerate(self.range_obj.vpcs):
                current_vpc = dumped_schema["vpcs"][x]
                vpc_key = next((key for key in raw_outputs.keys() if key.endswith(f"-{vpc.name}-resource-id")), None)
                if not vpc_key:
                    logger.error("Could not find VPC resource ID key for %s in Terraform output", vpc.name)
                    return None
                current_vpc["resource_id"] = raw_outputs[vpc_key]["value"]
                
                for y, subnet in enumerate(vpc.subnets):
                    current_subnet = current_vpc["subnets"][y]
                    subnet_key = next((key for key in raw_outputs.keys() if key.endswith(f"-{vpc.name}-{subnet.name}-resource-id")), None)
                    if not subnet_key:
                        logger.error("Could not find subnet resource ID key for %s in %s in Terraform output", subnet.name, vpc.name)
                        return None
                    current_subnet["resource_id"] = raw_outputs[subnet_key]["value"]
                    
                    for z, host in enumerate(subnet.hosts):
                        current_host = current_subnet["hosts"][z]
                        host_id_key = next((key for key in raw_outputs.keys() if key.endswith(f"-{vpc.name}-{subnet.name}-{host.hostname}-resource-id")), None)
                        host_ip_key = next((key for key in raw_outputs.keys() if key.endswith(f"-{vpc.name}-{subnet.name}-{host.hostname}-private-ip")), None)
                        
                        if not host_id_key or not host_ip_key:
                            logger.error("Could not find host keys for %s in %s/%s in Terraform output", host.hostname, vpc.name, subnet.name)
                            return None
                            
                        current_host["resource_id"] = raw_outputs[host_id_key]["value"]
                        current_host["ip_address"] = raw_outputs[host_ip_key]["value"]
        except KeyError as e:
            logger.exception("Failed to parse Terraform outputs. Missing key in output. Exception: %s", e)
            return None
        except Exception as e:
            logger.exception("Unknown error parsing Terraform outputs. Exception: %s", e)
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

    def create_state_file(self) -> bool:
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

        with open(self.get_state_file_path(), mode="w") as file:
            json.dump(self.state_file, file, indent=4)

        msg = f"Successfully created state file: {self.get_state_file_path()} "
        logger.info(msg)
        return True

    def cleanup_synth(self) -> bool:
        """Delete Terraform files generated by CDKTF synthesis."""
        try:
            shutil.rmtree(self.get_synth_dir())
            self._is_synthesized = False
            return True
        except Exception as e:
            logger.error(
                "Failed to delete synthesis files for stack: %s. Error: %s",
                self.stack_name,
                e,
            )
            return False
