import logging
from datetime import UTC, datetime
from typing import Any, Tuple

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

from src.app.models.secret_model import SecretModel
from src.app.schemas.message_schema import AWSUpdateSecretMessageSchema, MessageSchema
from src.app.schemas.secret_schema import AWSSecrets
from src.app.utils.crypto import encrypt_with_public_key

from .base_creds import AbstractBaseCreds

# Configure logging
logger = logging.getLogger(__name__)


class AWSCreds(AbstractBaseCreds):
    """Credential verification for AWS."""

    credentials: AWSSecrets

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize AWS credentials verification object."""
        self.credentials = AWSSecrets.model_validate(credentials)

    def update_user_secrets(
        self, secrets: SecretModel, current_user_public_key: str
    ) -> MessageSchema:
        """Update user AWS secrets in user record."""
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

    def authenticate(self) -> Tuple[bool, MessageSchema]:
        """Verify credentials authenticate to an AWS account."""
        try:
            client = boto3.client(
                "sts",
                aws_access_key_id=self.credentials.aws_access_key,
                aws_secret_access_key=self.credentials.aws_secret_key,
            )
            client.get_caller_identity()  # will raise an error if not valid
            return (
                True,
                MessageSchema(message="AWS credentials successfully authenticated"),
            )
        except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
            message = e.response["Error"]["Message"]
            logger.error("AWS authentication failed: %s", message)
            return (
                False,
                MessageSchema(
                    message="AWS credentials could not be verified. Please ensure you are providing credentials that are linked to a valid AWS account."
                ),
            )
