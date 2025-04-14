import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from ..enums.permissions import PermissionEntityType
from ..models.template_permission_model import TemplatePermissionModel
from ..schemas.template_permission_schema import TemplatePermissionCreateSchema

logger = logging.getLogger(__name__)


async def create_template_permission(
    db: AsyncSession, permission: TemplatePermissionCreateSchema
) -> TemplatePermissionModel:
    """Create a new template permission.

    Args:
    ----
        db (AsyncSession): Database connection.
        permission (TemplatePermissionCreateSchema): Permission data.

    Returns:
    -------
        TemplatePermissionModel: The created permission.

    """
    permission_dict = permission.model_dump()
    permission_dict["id"] = uuid.uuid4()

    permission_obj = TemplatePermissionModel(**permission_dict)

    # Set datetime fields after instantiation
    permission_obj.created_at = datetime.now(UTC)
    permission_obj.updated_at = datetime.now(UTC)

    db.add(permission_obj)
    await db.commit()
    await db.refresh(permission_obj)

    return permission_obj


async def get_template_permission(
    db: AsyncSession, permission_id: UUID
) -> TemplatePermissionModel | None:
    """Get a template permission by ID.

    Args:
    ----
        db (AsyncSession): Database connection.
        permission_id (UUID): Permission ID.

    Returns:
    -------
        TemplatePermissionModel | None: The permission if found, None otherwise.

    """
    stmt = select(TemplatePermissionModel).where(
        TemplatePermissionModel.id == permission_id
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_template_permissions_by_template(
    db: AsyncSession, template_type: str, template_id: UUID
) -> list[TemplatePermissionModel]:
    """Get all permissions for a template.

    Args:
    ----
        db (AsyncSession): Database connection.
        template_type (str): Type of template.
        template_id (UUID): Template ID.

    Returns:
    -------
        list[TemplatePermissionModel]: List of permissions.

    """
    stmt = (
        select(TemplatePermissionModel)
        .where(TemplatePermissionModel.template_type == template_type)
        .where(TemplatePermissionModel.template_id == template_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@dataclass
class TemplateIdentifier:
    """Template identifier with type and ID."""

    template_type: str
    template_id: UUID


@dataclass
class EntityIdentifier:
    """Entity identifier with type and ID."""

    entity_type: PermissionEntityType
    entity_id: UUID


async def delete_template_permission(db: AsyncSession, permission_id: UUID) -> bool:
    """Delete a template permission.

    Args:
    ----
        db (AsyncSession): Database connection.
        permission_id (UUID): Permission ID.

    Returns:
    -------
        bool: True if deleted, False otherwise.

    """
    permission = await get_template_permission(db, permission_id)
    if not permission:
        return False

    await db.delete(permission)
    await db.commit()
    return True
