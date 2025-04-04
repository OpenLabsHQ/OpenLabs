import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..enums.range_states import RangeState
from ..enums.regions import OpenLabsRegion
from .range_common_schema import RangeCommonSchema
from .vpc_schema import VPCBaseSchema


class RangeBaseSchema(RangeCommonSchema):
    """Deployed base range schema."""

    description: str = Field(
        ..., description="Description of range", examples=["This is my test range."]
    )
    date: datetime = Field(
        description="Time range was created",
        examples=[datetime(2025, 2, 5, tzinfo=timezone.utc)],
    )
    readme: str | None = Field(default=None, description="Markdown readme for range")
    state_file: dict[str, Any] = Field(..., description="Terraform state file")
    state: RangeState = Field(
        ...,
        description="State of deployed range",
        examples=[RangeState.ON, RangeState.OFF, RangeState.STARTING],
    )
    region: OpenLabsRegion = Field(
        ..., description="Cloud region to deploy template range"
    )

    vpcs: list[VPCBaseSchema] = Field(..., description="Contained VPCs,")

    @field_validator("vpcs")
    @classmethod
    def validate_unique_vpc_names(
        cls, vpcs: list[VPCBaseSchema]
    ) -> list[VPCBaseSchema]:
        """Check VPC names are unique.

        Args:
        ----
            cls: RangeBaseSchema object.
            vpcs (list[VPCBaseSchema]): VPC objects.

        Returns:
        -------
            list[VPCBaseSchema]: VPC objects.

        """
        vpc_names = [vpc.name for vpc in vpcs]
        if len(vpc_names) != len(set(vpc_names)):
            msg = "All VPC names must be unique."
            raise (ValueError(msg))
        return vpcs


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
    readme: str | None = Field(default=None, description="Markdown readme for range")


class RangeID(BaseModel):
    """Identity class for the range object."""

    id: uuid.UUID = Field(..., description="Unique range identifier.")
    model_config = ConfigDict(from_attributes=True)


class RangeSchema(RangeBaseSchema, RangeID):
    """Deployed range schema."""

    model_config = ConfigDict(from_attributes=True)
