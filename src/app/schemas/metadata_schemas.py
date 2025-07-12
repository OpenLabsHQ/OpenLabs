from typing import Literal, Union

from pydantic import BaseModel

from ..enums.providers import OpenLabsProvider


class BaseMetadata(BaseModel):
    """Base for provider-specific range metadata."""

    pass


class AWSMetadata(BaseMetadata):
    """AWS specific range metadata."""

    provider: Literal[OpenLabsProvider.AWS] = OpenLabsProvider.AWS


class AzureMetadata(BaseMetadata):
    """Azure specific range metadata."""

    provider: Literal[OpenLabsProvider.AZURE] = OpenLabsProvider.AZURE
    resource_group: str


# Using 'Union' here for clarity
RangeMetadata = Union[AWSMetadata, AzureMetadata]
