import uuid

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from .host_common_schema import HostCommonSchema


class TemplateHostBaseSchema(HostCommonSchema):
    """Base template host object for OpenLabs."""

    pass


class TemplateHostID(BaseModel):
    """Identity class for template host object."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="Unique object identifier."
    )

    model_config = ConfigDict(from_attributes=True)


class TemplateHostSchema(TemplateHostBaseSchema, TemplateHostID):
    """Template host object for OpenLabs."""

    model_config = ConfigDict(from_attributes=True)
