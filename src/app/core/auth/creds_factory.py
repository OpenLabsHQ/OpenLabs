import logging
from typing import Any, ClassVar, Type

from src.app.core.auth.aws_creds import AWSCreds
from src.app.core.auth.base_creds import AbstractBaseCreds
from src.app.enums.providers import OpenLabsProvider

# Configure logging
logger = logging.getLogger(__name__)


class CredsFactory:
    """Create creds objects."""

    _registry: ClassVar[dict[OpenLabsProvider, Type[AbstractBaseCreds]]] = {
        OpenLabsProvider.AWS: AWSCreds,
    }

    @classmethod
    def create_creds_verification(
        cls, provider: OpenLabsProvider, credentials: dict[str, Any]
    ) -> AbstractBaseCreds:
        """Create creds object.

        **Note:** This function accepts a creation schema as the OpenLabs resource ID is not required
        for terraform.

        Args:
        ----
            cls (CredsFactory): The CredsFactory class.
            provider (OpenLabsProvider): Cloud provider the credentials to verify are for
            credentials (dict[str, Any]): User cloud credentials to verify

        Returns:
        -------
            AbstractBaseCreds: Creds object that will be used to verify the user cloud credentials provided

        """
        creds_class = cls._registry.get(provider)

        if creds_class is None:
            msg = (
                f"Failed to build creds object. Non-existent provider given: {provider}"
            )
            logger.error(msg)
            raise ValueError(msg)

        return creds_class(credentials=credentials)
