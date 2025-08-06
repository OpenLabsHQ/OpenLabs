import logging
from typing import ClassVar, Type

from src.app.cloud.aws_creds import AWSCreds
from src.app.cloud.base_creds import AbstractBaseCreds
from src.app.enums.providers import OpenLabsProvider
from src.app.schemas.secret_schema import AnySecrets

# Configure logging
logger = logging.getLogger(__name__)


class CredsFactory:
    """Create creds objects."""

    _registry: ClassVar[dict[OpenLabsProvider, Type[AbstractBaseCreds]]] = {
        OpenLabsProvider.AWS: AWSCreds,
    }

    @classmethod
    def create_creds_verification(cls, credentials: AnySecrets) -> AbstractBaseCreds:
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
        creds_class = cls._registry.get(credentials.provider)

        if creds_class is None:
            msg = f"Failed to build creds object. Non-existent provider given: {credentials.provider}"
            logger.error(msg)
            raise ValueError(msg)

        return creds_class(credentials=credentials)
