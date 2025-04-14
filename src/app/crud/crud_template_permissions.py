import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from ..enums.permissions import PermissionEntityType, PermissionType
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


async def get_template_permissions_by_entity(
    db: AsyncSession, entity_type: PermissionEntityType, entity_id: UUID
) -> list[TemplatePermissionModel]:
    """Get all permissions for an entity.

    Args:
    ----
        db (AsyncSession): Database connection.
        entity_type (PermissionEntityType): Type of entity.
        entity_id (UUID): Entity ID.

    Returns:
    -------
        list[TemplatePermissionModel]: List of permissions.

    """
    stmt = (
        select(TemplatePermissionModel)
        .where(TemplatePermissionModel.entity_type == entity_type)
        .where(TemplatePermissionModel.entity_id == entity_id)
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


async def get_specific_permission(
    db: AsyncSession,
    template: TemplateIdentifier,
    entity: EntityIdentifier,
    permission_type: PermissionType | None = None,
) -> TemplatePermissionModel | None:
    """Get a specific permission by template, entity, and optionally permission type.

    Args:
    ----
        db (AsyncSession): Database connection.
        template (TemplateIdentifier): Template identifier with type and ID.
        entity (EntityIdentifier): Entity identifier with type and ID.
        permission_type (PermissionType | None): Type of permission to filter by.

    Returns:
    -------
        TemplatePermissionModel | None: The permission if found, None otherwise.

    """
    stmt = (
        select(TemplatePermissionModel)
        .where(TemplatePermissionModel.template_type == template.template_type)
        .where(TemplatePermissionModel.template_id == template.template_id)
        .where(TemplatePermissionModel.entity_type == entity.entity_type)
        .where(TemplatePermissionModel.entity_id == entity.entity_id)
    )

    if permission_type is not None:
        stmt = stmt.where(TemplatePermissionModel.permission_type == permission_type)

    result = await db.execute(stmt)
    return result.scalars().first()


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


async def delete_all_template_permissions(
    db: AsyncSession, template_type: str, template_id: UUID
) -> bool:
    """Delete all permissions for a template.

    Args:
    ----
        db (AsyncSession): Database connection.
        template_type (str): Type of template.
        template_id (UUID): Template ID.

    Returns:
    -------
        bool: True if any permissions were deleted, False otherwise.

    """
    permissions = await get_template_permissions_by_template(
        db, template_type, template_id
    )
    if not permissions:
        return False

    for permission in permissions:
        await db.delete(permission)

    await db.commit()
    return True


async def check_permission(
    db: AsyncSession,
    template: TemplateIdentifier,
    entity: EntityIdentifier,
    permission_type: PermissionType,
) -> bool:
    """Check if an entity has a specific permission on a template.

    Args:
    ----
        db (AsyncSession): Database connection.
        template (TemplateIdentifier): Template identifier with type and ID.
        entity (EntityIdentifier): Entity identifier with type and ID.
        permission_type (PermissionType): Type of permission to check.

    Returns:
    -------
        bool: True if the entity has the permission, False otherwise.

    """
    # If checking for READ permission, WRITE permission also implies READ
    if permission_type == PermissionType.READ:
        stmt = (
            select(TemplatePermissionModel)
            .where(TemplatePermissionModel.template_type == template.template_type)
            .where(TemplatePermissionModel.template_id == template.template_id)
            .where(TemplatePermissionModel.entity_type == entity.entity_type)
            .where(TemplatePermissionModel.entity_id == entity.entity_id)
        )
        result = await db.execute(stmt)
        return result.scalars().first() is not None
    # For WRITE permission, specifically check for WRITE
    stmt = (
        select(TemplatePermissionModel)
        .where(TemplatePermissionModel.template_type == template.template_type)
        .where(TemplatePermissionModel.template_id == template.template_id)
        .where(TemplatePermissionModel.entity_type == entity.entity_type)
        .where(TemplatePermissionModel.entity_id == entity.entity_id)
        .where(TemplatePermissionModel.permission_type == permission_type)
    )
    result = await db.execute(stmt)
    return result.scalars().first() is not None
