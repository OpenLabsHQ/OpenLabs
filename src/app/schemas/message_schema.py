from typing import Literal

from pydantic import BaseModel, Field


class MessageSchema(BaseModel):
    """Generic JSON response schema for OpenLabs."""

    message: str = Field(..., description="Response message")


class UpdatePasswordMessageSchema(MessageSchema):
    """Password update response schema for OpenLabs."""

    message: Literal[
        "Password updated successfully", "Current password is incorrect"
    ] = Field(..., description="Message indicating password reset status")


class AWSUpdateSecretMessageSchema(MessageSchema):
    """AWS update secret response schema for OpenLabs."""

    message: Literal["AWS credentials updated successfully"] = Field(...)


class AzureUpdateSecretMessageSchema(MessageSchema):
    """Azure update secret response schema for OpenLabs."""

    message: Literal["Azure credentials updated successfully"] = Field(...)


class UserLoginMessageSchema(BaseModel):
    """User login response schema for OpenLabs."""

    success: bool = Field(..., description="Whether or not login was successfull")


class UserLogoutMessageSchema(BaseModel):
    """User logout response schema for OpenLabs."""

    success: bool = Field(..., description="Whether or not logout was successfull")
