from typing import Any

from ..stacks.azure_stack import AzureStack
from .base_range import AbstractBaseRange


class AzureRange(AbstractBaseRange):
    """Range deployed to Azure."""

    def get_provider_stack_class(self) -> type[AzureStack]:
        """Return AzureStack class."""
        return AzureStack

    def has_secrets(self) -> bool:
        """Return whether Azure range has proper credentials."""
        return bool(
            self.secrets.azure_client_id
            and self.secrets.azure_client_secret
            and self.secrets.azure_tenant_id
            and self.secrets.azure_subscription_id
        )

    def get_cred_env_vars(self) -> dict[str, Any]:
        """Return Azure credential environment variables."""
        return {
            "ARM_CLIENT_ID": self.secrets.azure_client_id,
            "ARM_CLIENT_SECRET": self.secrets.azure_client_secret,
            "ARM_TENANT_ID": self.secrets.azure_tenant_id,
            "ARM_SUBSCRIPTION_ID": self.secrets.azure_subscription_id,
        }
