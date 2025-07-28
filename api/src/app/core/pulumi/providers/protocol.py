"""Protocol definitions for Pulumi providers."""

from typing import Callable, Protocol

import pulumi.automation as auto

from ....enums.regions import OpenLabsRegion
from ....schemas.range_schemas import BlueprintRangeSchema, DeployedRangeSchema
from ....schemas.secret_schema import SecretSchema


class PulumiProvider(Protocol):
    """Protocol defining the contract for Pulumi providers."""

    def get_pulumi_program(
        self,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        region: OpenLabsRegion,
        secrets: SecretSchema,
        stack_name: str,
    ) -> Callable[[], None]:
        """Return Pulumi program function for this provider.

        Args:
            range_obj: Blueprint or deployed range object
            region: Cloud region for deployment
            secrets: Cloud provider credentials
            stack_name: Name of the Pulumi stack

        Returns:
            Pulumi program function that defines infrastructure

        """
        ...

    def has_secrets(self, secrets: SecretSchema) -> bool:
        """Check if provider has correct cloud credentials.

        Args:
            secrets: Cloud provider credentials

        Returns:
            True if correct provider creds exist, False otherwise

        """
        ...

    def get_config_values(
        self,
        region: OpenLabsRegion,
        secrets: SecretSchema,
    ) -> dict[str, auto.ConfigValue]:
        """Return dictionary of Pulumi configuration values.

        Args:
            region: Cloud region for deployment
            secrets: Cloud provider credentials

        Returns:
            Dict of Pulumi configuration values

        """
        ...

    def get_cred_env_vars(self, secrets: SecretSchema) -> dict[str, str]:
        """Return dictionary of cloud provider credential environment variables.

        Args:
            secrets: Cloud provider credentials

        Returns:
            Dict of environment variables for cloud credentials

        """
        ...
