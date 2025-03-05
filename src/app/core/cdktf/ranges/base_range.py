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
from ....schemas.secret_schema import SecretSchema
from ....schemas.template_range_schema import TemplateRangeSchema
from ....schemas.user_schema import UserID
from ...config import settings
from ..stacks.base_stack import AbstractBaseStack

# Configure logging
logger = logging.getLogger(__name__)

# # Define a TypeVar bound to AbstractBaseStack
# TStack = TypeVar("TStack", bound=AbstractBaseStack)


class CdktfBaseRange(ABC):
    """Abstract class to enforce common functionality across range cloud providers."""

    id: uuid.UUID
    template: TemplateRangeSchema
    region: OpenLabsRegion
    stack_name: str | None
    state: str | None  # Terraform state
    owner_id: UserID
    secrets: SecretSchema

    # State varibles
    _is_synthesized: bool
    _is_deployed: bool

    def __init__(
        self,
        range_id: uuid.UUID,
        template: TemplateRangeSchema,
        region: OpenLabsRegion,
        owner_id: UserID,
        secrets: SecretSchema,
    ) -> None:
        """Initialize CDKTF base range object."""
        self.id = range_id
        self.template = template
        self.region = region
        self.owner_id = owner_id
        self.secrets = secrets

        # Initial values
        self.stack_name = None
        self.state = None
        self._is_synthesized = False
        self._is_deployed = False

    @abstractmethod
    def get_provider_stack_class(self) -> type[AbstractBaseStack]:
        """Return specific provider stack class to instantiate.

        Returns
        -------
        Type[TStack]: Provider stack class.

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

    def synthesize(self) -> None:
        """Abstract method to synthesize terraform configuration."""
        try:
            self.stack_name = f"{self.template.name}-{self.id}"
            logger.info("Syntehsizing stack: %s", self.stack_name)

            # Create CDKTF app
            app = App(outdir=settings.CDKTF_DIR)

            # Instantiate the correct provider stack
            stack_class = self.get_provider_stack_class()
            stack_class(
                scope=app,
                template_range=self.template,
                cdktf_id=self.stack_name,
                cdktf_dir=settings.CDKTF_DIR,
                region=self.region,
            )

            # Synthesize Terraform files
            app.synth()
            logger.info(
                "Range: %s synthesized successfully as: %s",
                self.template.name,
                self.stack_name,
            )

            self._is_synthesized = True
        except Exception as e:
            logger.error(
                "Error during synthesis of stack: %s. Error: %s", self.stack_name, e
            )

    def deploy(self) -> bool:
        """Run `terraform deploy --auto-approve` programmatically.

        Args:
        ----
            stack_dir (str): Output directory.
            stack_name (str): Name of stack used to deploy the range (format: <range name>-<range id>).

        Returns:
        -------
            bool: True if successfully deployed range. False otherwise.

        """
        if not self.is_synthesized():
            logger.warning(
                "Deployed range that was not synthesized. Synthesizing now..."
            )
            self.synthesize()

        try:
            initial_dir = os.getcwd()
            os.chdir(self.get_synth_dir())
            subprocess.run(["terraform", "init"], check=True)  # noqa: S603, S607

            # Terraform apply
            env = os.environ.copy()
            env.update(self.get_cred_env_vars())
            subprocess.run(  # noqa: S603
                ["terraform", "apply", "--auto-approve"],  # noqa: S607
                check=True,
                env=env,
            )

            # Load state
            state_path = self.get_synth_dir() / f"terraform.{self.stack_name}.tfstate"
            if state_path.exists():
                with open(state_path, "r", encoding="utf-8") as file:
                    self.state = file.read()

            self._is_deployed = True
            logger.info("Range deployment successful for %s", self.template.name)
            os.chdir(initial_dir)
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Terraform command failed: %s", e)
            return False
        except Exception as e:
            logger.error("Error during deployment: %s", e)
            return False

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
            logger.info("Range to destory is not synethized. Re-synthesizing now...")
            self.synthesize()

        try:
            # Change to directory with `cdk.tf.json` and terraform state file
            os.chdir(self.get_synth_dir())

            # Run Terraform commands
            print("Tearing down selected range: %s", self.template.name)
            subprocess.run(  # noqa: S603
                ["terraform", "destroy", "--auto-approve"], check=True  # noqa: S607
            )

            # Delete synth files
            self.cleanup_synth()
            self._is_deployed = False
            self._is_synthesized = False

            return True
        except subprocess.CalledProcessError as e:
            logger.error("Terraform command failed: %s", e)
            return False
        except Exception as e:
            logger.error("Error during destroy: %s", e)
            return False

    def is_synthesized(self) -> bool:
        """Return if range is currently synthesized."""
        return self._is_synthesized

    def is_deployed(self) -> bool:
        """Return if range is currently deployed."""
        return self._is_deployed

    def get_synth_dir(self) -> Path:
        """Get CDKTF synthesis directory."""
        return Path(f"{settings.CDKTF_DIR}/stacks/{self.stack_name}")

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
