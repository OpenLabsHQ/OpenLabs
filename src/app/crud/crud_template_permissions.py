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


async def get_templates_by_workspace(
    db: AsyncSession, workspace_id: UUID
) -> list[TemplatePermissionModel]:
    """Get all templates shared with a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (UUID): The workspace ID.

    Returns:
    -------
        list[TemplatePermissionModel]: List of template permissions for the workspace.

    """
    stmt = (
        select(TemplatePermissionModel)
        .where(TemplatePermissionModel.entity_type == PermissionEntityType.WORKSPACE)
        .where(TemplatePermissionModel.entity_id == workspace_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_workspace_template_permission(
    db: AsyncSession, workspace_id: UUID, template_type: str, template_id: UUID
) -> TemplatePermissionModel | None:
    """Get a specific template permission for a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (UUID): Workspace ID.
        template_type (str): Type of template.
        template_id (UUID): Template ID.

    Returns:
    -------
        TemplatePermissionModel | None: The permission if found, None otherwise.

    """
    stmt = (
        select(TemplatePermissionModel)
        .where(TemplatePermissionModel.template_type == template_type)
        .where(TemplatePermissionModel.template_id == template_id)
        .where(TemplatePermissionModel.entity_type == PermissionEntityType.WORKSPACE)
        .where(TemplatePermissionModel.entity_id == workspace_id)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


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


async def get_user_workspaces_with_template_access(
    db: AsyncSession, user_id: UUID, template_type: str, template_id: UUID
) -> list[UUID]:
    """Get all workspace IDs that the user is a member of and have access to a specific template.

    Args:
    ----
        db (AsyncSession): Database connection.
        user_id (UUID): User ID.
        template_type (str): Type of template.
        template_id (UUID): Template ID.

    Returns:
    -------
        list[UUID]: List of workspace IDs.

    """
    # This query finds all workspaces where:
    # 1. The user is a member of the workspace
    # 2. The workspace has permission for the specified template

    from sqlalchemy import and_

    from ..models.workspace_user_model import WorkspaceUserModel

    stmt = (
        select(WorkspaceUserModel.workspace_id)
        .join(
            TemplatePermissionModel,
            and_(
                TemplatePermissionModel.entity_type == PermissionEntityType.WORKSPACE,
                TemplatePermissionModel.entity_id == WorkspaceUserModel.workspace_id,
                TemplatePermissionModel.template_type == template_type,
                TemplatePermissionModel.template_id == template_id,
            ),
            isouter=True,
        )
        .where(WorkspaceUserModel.user_id == user_id)
        .where(TemplatePermissionModel.id.is_not(None))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def check_user_template_access(
    db: AsyncSession,
    user_id: UUID,
    template_type: str,
    template_id: UUID,
    permission_type: PermissionType,
) -> bool:
    """Check if a user has access to a template either directly or through a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        user_id (UUID): User ID.
        template_type (str): Type of template.
        template_id (UUID): Template ID.
        permission_type (PermissionType): Type of permission required.

    Returns:
    -------
        bool: True if the user has access, False otherwise.

    """
    # Check direct user permission first
    user_permission_stmt = (
        select(TemplatePermissionModel)
        .where(TemplatePermissionModel.template_type == template_type)
        .where(TemplatePermissionModel.template_id == template_id)
        .where(TemplatePermissionModel.entity_type == PermissionEntityType.USER)
        .where(TemplatePermissionModel.entity_id == user_id)
    )

    # For READ permission, we can accept either READ or WRITE
    # For WRITE permission, we must have WRITE specifically
    if permission_type == PermissionType.READ:
        user_permission_stmt = user_permission_stmt.where(
            TemplatePermissionModel.permission_type.in_(
                [PermissionType.READ, PermissionType.WRITE]
            )
        )
    else:
        user_permission_stmt = user_permission_stmt.where(
            TemplatePermissionModel.permission_type == PermissionType.WRITE
        )

    result = await db.execute(user_permission_stmt)
    user_permission = result.scalars().first()

    if user_permission:
        return True

    # If no direct permission, check workspace permissions
    workspace_ids = await get_user_workspaces_with_template_access(
        db, user_id, template_type, template_id
    )
    return len(workspace_ids) > 0


async def sync_workspace_template_permissions(
    db: AsyncSession, workspace_id: UUID
) -> None:
    """Sync template permissions for all users in a workspace.

    When a template is shared with a workspace, ensure all users in the workspace
    have access to all templates shared with the workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (UUID): Workspace ID.

    """
    # Import here to avoid circular imports
    from ..models.workspace_user_model import WorkspaceUserModel

    # Get all users in the workspace
    users_stmt = select(WorkspaceUserModel.user_id).where(
        WorkspaceUserModel.workspace_id == workspace_id
    )
    users_result = await db.execute(users_stmt)
    user_ids = users_result.scalars().all()

    # Get all templates shared with the workspace
    templates_stmt = select(TemplatePermissionModel).where(
        TemplatePermissionModel.entity_type == PermissionEntityType.WORKSPACE,
        TemplatePermissionModel.entity_id == workspace_id,
    )
    templates_result = await db.execute(templates_stmt)
    template_permissions = templates_result.scalars().all()

    # For each user and template, ensure the user has access
    for user_id in user_ids:
        for template_permission in template_permissions:
            # Check if user already has direct permission to this template
            existing_stmt = (
                select(TemplatePermissionModel)
                .where(
                    TemplatePermissionModel.template_type
                    == template_permission.template_type
                )
                .where(
                    TemplatePermissionModel.template_id
                    == template_permission.template_id
                )
                .where(TemplatePermissionModel.entity_type == PermissionEntityType.USER)
                .where(TemplatePermissionModel.entity_id == user_id)
            )
            existing_result = await db.execute(existing_stmt)
            existing_permission = existing_result.scalars().first()

            # Skip if user already has direct permission
            if existing_permission:
                continue

            # Create permission for the user
            new_permission = TemplatePermissionModel(
                id=uuid.uuid4(),
                template_type=template_permission.template_type,
                template_id=template_permission.template_id,
                entity_type=PermissionEntityType.USER,
                entity_id=user_id,
                permission_type=template_permission.permission_type,
            )

            # Set datetime fields after instantiation
            new_permission.created_at = datetime.now(UTC)
            new_permission.updated_at = datetime.now(UTC)

            db.add(new_permission)

    # Commit all changes at once
    await db.commit()


async def sync_user_workspace_permissions(
    db: AsyncSession, user_id: UUID, workspace_id: UUID
) -> None:
    """Sync template permissions for a user added to a workspace.

    When a user is added to a workspace, ensure they have access to all templates
    shared with the workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        user_id (UUID): User ID.
        workspace_id (UUID): Workspace ID.

    """
    # Get all templates shared with the workspace
    templates_stmt = select(TemplatePermissionModel).where(
        TemplatePermissionModel.entity_type == PermissionEntityType.WORKSPACE,
        TemplatePermissionModel.entity_id == workspace_id,
    )
    templates_result = await db.execute(templates_stmt)
    template_permissions = templates_result.scalars().all()

    # For each template, ensure the user has access
    for template_permission in template_permissions:
        # Check if user already has direct permission to this template
        existing_stmt = (
            select(TemplatePermissionModel)
            .where(
                TemplatePermissionModel.template_type
                == template_permission.template_type
            )
            .where(
                TemplatePermissionModel.template_id == template_permission.template_id
            )
            .where(TemplatePermissionModel.entity_type == PermissionEntityType.USER)
            .where(TemplatePermissionModel.entity_id == user_id)
        )
        existing_result = await db.execute(existing_stmt)
        existing_permission = existing_result.scalars().first()

        # Skip if user already has direct permission
        if existing_permission:
            continue

        # Create permission for the user
        new_permission = TemplatePermissionModel(
            id=uuid.uuid4(),
            template_type=template_permission.template_type,
            template_id=template_permission.template_id,
            entity_type=PermissionEntityType.USER,
            entity_id=user_id,
            permission_type=template_permission.permission_type,
        )

        # Set datetime fields after instantiation
        new_permission.created_at = datetime.now(UTC)
        new_permission.updated_at = datetime.now(UTC)

        db.add(new_permission)

    # Commit all changes at once
    await db.commit()


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
