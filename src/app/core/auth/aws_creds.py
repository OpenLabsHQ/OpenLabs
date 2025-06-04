from datetime import UTC, datetime
from typing import Any

from src.app.models.secret_model import SecretModel
from src.app.schemas.message_schema import AWSUpdateSecretMessageSchema, MessageSchema
from src.app.schemas.secret_schema import AWSSecrets
from src.app.utils.crypto import encrypt_with_public_key

from .base_creds import AbstractBaseCreds


class AWSCreds(AbstractBaseCreds):
    """Credential verification for AWS."""

    credentials: AWSSecrets

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize AWS credentials verification object."""
        self.credentials = AWSSecrets.model_validate(credentials)

    def update_user_secrets(
        self, secrets: SecretModel, current_user_public_key: str
    ) -> MessageSchema:
        """Update user AWS secrets."""
        # Convert to dictionary for encryption
        aws_data = {
            "aws_access_key": self.credentials.aws_access_key,
            "aws_secret_key": self.credentials.aws_secret_key,
        }

        # Encrypt with the user's public key
        encrypted_data = encrypt_with_public_key(aws_data, current_user_public_key)

        # Update the secrets with encrypted values
        secrets.aws_access_key = encrypted_data["aws_access_key"]
        secrets.aws_secret_key = encrypted_data["aws_secret_key"]
        secrets.aws_created_at = datetime.now(UTC)

        return AWSUpdateSecretMessageSchema(
            message="AWS credentials updated successfully"
        )
