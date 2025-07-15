from abc import ABC, abstractmethod
from typing import Any, Tuple

from src.app.schemas.message_schema import MessageSchema
from src.app.schemas.secret_schema import SecretSchema


class AbstractBaseCreds(ABC):
    """Abstract class to enforce common credential verification functionality across range cloud providers."""

    @abstractmethod
    def __init__(self, credentials: dict[str, Any]) -> None:
        """Expected constructor for all credential subclasses."""  # noqa: D401
        pass

    @abstractmethod
    def convert_user_creds(self) -> dict[str, str]:
        """Convert user secrets to dictionary for encryption."""
        pass

    @abstractmethod
    def update_user_creds(
        self, secrets: SecretSchema, encrypted_data: dict[str, str]
    ) -> SecretSchema:
        """Update user secrets record with newly encrypted secrets."""
        pass

    @abstractmethod
    def verify_creds(self) -> Tuple[bool, MessageSchema]:
        """Verify that user provided credentials properly authenticate to a provider account."""
        pass

    @abstractmethod
    def get_message(self) -> MessageSchema:
        """Provide specific message for successful verification and updadting of credentials in the database."""
        pass
