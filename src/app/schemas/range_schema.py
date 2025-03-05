import uuid

from pydantic import BaseModel, ConfigDict, Field

from ..enums.regions import OpenLabsRegion


class DeployRangeBaseSchema(BaseModel):
    """Deploy range to cloud provider schema."""

    name: str = Field(..., description="Range name", min_length=1, examples=["range-1"])
    description: str = Field(
        ..., description="Description of range", examples=["This is my test range."]
    )
    template_id: uuid.UUID = Field(..., description="Template range ID")
    region: OpenLabsRegion = Field(
        ..., description="Cloud region to deploy template range"
    )


class RangeID(BaseModel):
    """Identity class for the template range object."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="Unique range identifier."
    )
    model_config = ConfigDict(from_attributes=True)
