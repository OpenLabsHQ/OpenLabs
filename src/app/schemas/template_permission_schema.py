import uuid

from pydantic import BaseModel, ConfigDict, Field

from ..enums.permissions import PermissionEntityType, PermissionType


class TemplatePermissionBaseSchema(BaseModel):
    """Base schema for template permission."""

    template_type: str = Field(
        ...,
        description="Type of template (range, vpc, subnet, host)",
        examples=[
            "range_templates",
            "vpc_templates",
            "subnet_templates",
            "host_templates",
        ],
    )
    template_id: uuid.UUID = Field(
        ...,
        description="ID of the template",
    )
    entity_type: PermissionEntityType = Field(
        ...,
        description="Type of entity (user or workspace)",
    )
    entity_id: uuid.UUID = Field(
        ...,
        description="ID of the entity",
    )
    permission_type: PermissionType = Field(
        ...,
        description="Type of permission (read or write)",
    )


class TemplatePermissionID(BaseModel):
    """Identity class for TemplatePermission."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="Unique template permission identifier."
    )

    model_config = ConfigDict(from_attributes=True)


class TemplatePermissionSchema(TemplatePermissionBaseSchema, TemplatePermissionID):
    """Schema for complete template permission data including ID."""

    created_at: str = Field(
        ..., description="Timestamp when the permission was created"
    )
    updated_at: str = Field(
        ..., description="Timestamp when the permission was last updated"
    )

    model_config = ConfigDict(from_attributes=True)


class TemplatePermissionCreateSchema(TemplatePermissionBaseSchema):
    """Schema for creating a new template permission."""

    model_config = ConfigDict(from_attributes=True)
