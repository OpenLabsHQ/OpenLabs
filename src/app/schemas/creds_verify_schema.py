from typing import Any

from pydantic import BaseModel, Field

from src.app.enums.providers import OpenLabsProvider


class CredsVerifySchema(BaseModel):
    """Base creds object for OpenLabs credential verification."""

    provider: OpenLabsProvider = Field(
        ...,
        description="Cloud provider",
        examples=[OpenLabsProvider.AWS, OpenLabsProvider.AZURE],
    )

    credentials: dict[str, Any] = Field(
        ..., description="Cloud provider credentials to verify"
    )
