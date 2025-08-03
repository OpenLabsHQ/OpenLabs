from datetime import datetime, timezone
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.app.enums.providers import OpenLabsProvider


class SecretBaseSchema(BaseModel):
    """Base secret object for OpenLabs."""

    aws_access_key: str | None = Field(
        default=None,
        description="Access key for AWS account",
    )
    aws_secret_key: str | None = Field(
        default=None,
        description="Secret key for AWS account",
    )

    aws_created_at: datetime | None = Field(
        default=None,
        description="Time AWS secrets were populated",
        examples=[datetime(2025, 2, 5, tzinfo=timezone.utc)],
    )

    azure_client_id: str | None = Field(
        default=None,
        description="Client ID for Azure",
    )

    azure_client_secret: str | None = Field(
        default=None,
        description="Client secret for Azure",
    )

    azure_tenant_id: str | None = Field(
        default=None,
        description="Tenant ID for Azure",
    )

    azure_subscription_id: str | None = Field(
        default=None,
        description="Subscription ID for Azure",
    )

    azure_created_at: datetime | None = Field(
        default=None,
        description="Time Azure secrets were populated",
        examples=[datetime(2025, 2, 5, tzinfo=timezone.utc)],
    )


class SecretSchema(SecretBaseSchema):
    """Secret object for OpenLabs."""

    model_config = ConfigDict(from_attributes=True)


class BaseSecrets(BaseModel):
    """Base secret object for setting secrets on OpenLabs."""

    provider: OpenLabsProvider


class AWSSecrets(BaseSecrets):
    """AWS secret object for setting secrets on OpenLabs."""

    provider: Literal[OpenLabsProvider.AWS] = OpenLabsProvider.AWS
    aws_access_key: str = Field(
        ...,
        description="Access key for AWS account",
    )
    aws_secret_key: str = Field(
        ...,
        description="Secret key for AWS account",
    )

    @field_validator("aws_access_key")
    @classmethod
    def validate_access_key(cls, aws_access_key: str) -> str:
        """Check AWS access key is correct length.

        Args:
        ----
            cls: AWSSecrets object.
            aws_access_key (str): AWS access key.

        Returns:
        -------
            str: AWS access key.

        """
        access_key_length = 20
        if len(aws_access_key.strip()) == 0:
            msg = "No AWS access key provided. Please ensure you are providing proper AWS credentials."
            raise ValueError(msg)
        if len(aws_access_key.strip()) != access_key_length:
            msg = "Invalid AWS access key format. Please ensure your AWS credentials are of proper length."
            raise ValueError(msg)
        return aws_access_key

    @field_validator("aws_secret_key")
    @classmethod
    def validate_secret_key(cls, aws_secret_key: str) -> str:
        """Check AWS secret key is correct length.

        Args:
        ----
            cls: AWSSecrets object.
            aws_secret_key (str): AWS secret key.

        Returns:
        -------
            str: AWS access key.

        """
        secret_key_length = 40
        if len(aws_secret_key.strip()) == 0:
            msg = "No AWS secret key provided. Please ensure you are providing proper AWS credentials."
            raise ValueError(msg)
        if len(aws_secret_key.strip()) != secret_key_length:
            msg = "Invalid AWS secret key format. Please ensure your AWS credentials are of proper length."
            raise ValueError(msg)
        return aws_secret_key


class AzureSecrets(BaseSecrets):
    """Azure secret object for setting secrets on OpenLabs."""

    provider: Literal[OpenLabsProvider.AZURE] = OpenLabsProvider.AZURE

    azure_client_id: str = Field(
        ...,
        description="Client ID for Azure",
    )
    azure_client_secret: str = Field(
        ...,
        description="Client secret for Azure",
    )
    azure_tenant_id: str = Field(
        ...,
        description="Tenant ID for Azure",
    )
    azure_subscription_id: str = Field(
        ...,
        description="Subscription ID for Azure",
    )


AnySecrets = Annotated[Union[AWSSecrets, AzureSecrets], Field(discriminator="provider")]


class CloudSecretStatusSchema(BaseModel):
    """General response schema for a single cloud provider."""

    has_credentials: bool = Field(
        ...,
        description="Indicates if the credentials are present",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Time the secrets were created",
        examples=[datetime(2025, 2, 5, tzinfo=timezone.utc)],
    )


class UserSecretResponseSchema(BaseModel):
    """Response schema for retrieving user secret status."""

    aws: CloudSecretStatusSchema = Field(
        ...,
        description="Status of AWS credentials",
    )
    azure: CloudSecretStatusSchema = Field(
        ...,
        description="Status of Azure credentials",
    )
