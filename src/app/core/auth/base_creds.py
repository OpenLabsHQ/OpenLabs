from abc import ABC, abstractmethod
from typing import Tuple

from src.app.models.secret_model import SecretModel
from src.app.schemas.message_schema import MessageSchema


class AbstractBaseCreds(ABC):
    """Abstract class to enforce common credential verification functionality across range cloud providers."""

    @abstractmethod
    def update_user_secrets(
        self, secrets: SecretModel, current_user_public_key: str
    ) -> MessageSchema:
        """Add encrypted user credentials to secrets record in database.

        Args:
        ----
            secrets (SecretModel): SQLAlchemy ORM object loaded from the database to update with verified provider credentials.
            current_user_public_key (str): Public key of the current user to encrypt the credentials with before uploading to the database.

        Returns:
        -------
            MessageSchema.

        """
        pass

    @abstractmethod
    def verify_creds(self) -> Tuple[bool, MessageSchema]:
        """Verify that user provided credentials properly authenticate to a provider account."""
        pass
