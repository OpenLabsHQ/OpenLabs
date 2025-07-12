from typing import Literal, Union

from pydantic import BaseModel, Field

from ..enums.providers import OpenLabsProvider


class BaseIdentity(BaseModel):
    """Common resource identity attributes across cloud providers."""

    primary_id: str = Field(description="The main ID of the resource.", min_length=1)


# ==================== Hosts =====================


class AWSHostIdentity(BaseIdentity):
    """Host identity attributes for AWS cloud."""

    provider: Literal[OpenLabsProvider.AWS] = OpenLabsProvider.AWS


# Using 'Union' here for clarity
HostIdentity = Union[AWSHostIdentity]
