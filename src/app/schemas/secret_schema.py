from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


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


class AWSSecrets(BaseModel):
    """AWS secret object for setting secrets on OpenLabs."""

    aws_access_key: str
    aws_secret_key: str


class AzureSecrets(BaseModel):
    """Azure secret object for setting secrets on OpenLabs."""

    azure_client_id: str
    azure_client_secret: str
    azure_tenant_id: str
    azure_subscription_id: str
