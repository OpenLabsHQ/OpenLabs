from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_template_permissions import (
    create_template_permission,
    delete_template_permission,
    get_templates_by_workspace,
    get_workspace_template_permission,
    sync_user_workspace_permissions,
    sync_workspace_template_permissions,
)
from ...crud.crud_workspace_users import (
    add_user_to_workspace,
    get_workspace_users_with_details,
    remove_user_from_workspace,
    update_workspace_user,
)
from ...crud.crud_workspaces import (
    create_workspace,
    delete_workspace,
    get_workspace,
    get_workspaces_by_owner,
    get_workspaces_by_user,
    is_workspace_admin,
    is_workspace_member,
    is_workspace_owner,
    update_workspace,
)
from ...enums.permissions import PermissionEntityType
from ...models.user_model import UserModel
from ...schemas.message_schema import MessageSchema
from ...schemas.template_permission_schema import (
    TemplatePermissionCreateSchema,
    TemplatePermissionSchema,
)
from ...schemas.workspace_schema import (
    WorkspaceCreateSchema,
    WorkspaceSchema,
    WorkspaceTemplateDeleteSchema,
    WorkspaceTemplateSchema,
)
from ...schemas.workspace_user_schema import (
    WorkspaceUserCreateSchema,
    WorkspaceUserDetailSchema,
    WorkspaceUserSchema,
    WorkspaceUserUpdateSchema,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceSchema, status_code=status.HTTP_201_CREATED)
async def create_new_workspace(
    workspace: WorkspaceCreateSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceSchema:
    """Create a new workspace.

    Args:
    ----
        workspace (WorkspaceCreateSchema): The workspace data.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceModel: The created workspace.

    """
    workspace_model = await create_workspace(db, workspace, current_user.id)
    # Convert to schema for proper response serialization
    return WorkspaceSchema(
        id=workspace_model.id,
        name=workspace_model.name,
        description=workspace_model.description,
        default_time_limit=workspace_model.default_time_limit,
        owner_id=workspace_model.owner_id,
        created_at=workspace_model.created_at.isoformat(),
        updated_at=workspace_model.updated_at.isoformat(),
    )


@router.get("", response_model=list[WorkspaceSchema])
async def get_workspaces(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> list[WorkspaceSchema]:
    """Get all workspaces the user has access to.

    Args:
    ----
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        list[WorkspaceModel]: The workspaces the user has access to.

    """
    # Admins can see all workspaces they own
    if current_user.is_admin:
        workspace_models = await get_workspaces_by_owner(db, current_user.id)
    else:
        # Regular users see workspaces they are members of
        workspace_models = await get_workspaces_by_user(db, current_user.id)

    # Convert models to schemas for response serialization
    return [
        WorkspaceSchema(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            default_time_limit=workspace.default_time_limit,
            owner_id=workspace.owner_id,
            created_at=workspace.created_at.isoformat(),
            updated_at=workspace.updated_at.isoformat(),
        )
        for workspace in workspace_models
    ]


@router.get("/{workspace_id}", response_model=WorkspaceSchema)
async def get_workspace_by_id(
    workspace_id: UUID = Path(..., description="The ID of the workspace to get"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceSchema:
    """Get a workspace by ID.

    Args:
    ----
        workspace_id (UUID): The ID of the workspace to get.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceModel: The workspace.

    """
    workspace_model = await get_workspace(db, workspace_id)
    if not workspace_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user has access to the workspace
    if not current_user.is_admin and not await is_workspace_member(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace",
        )

    # Convert model to schema for response serialization
    return WorkspaceSchema(
        id=workspace_model.id,
        name=workspace_model.name,
        description=workspace_model.description,
        default_time_limit=workspace_model.default_time_limit,
        owner_id=workspace_model.owner_id,
        created_at=workspace_model.created_at.isoformat(),
        updated_at=workspace_model.updated_at.isoformat(),
    )


@router.put("/{workspace_id}", response_model=WorkspaceSchema)
async def update_workspace_by_id(
    workspace_data: WorkspaceCreateSchema,
    workspace_id: UUID = Path(..., description="The ID of the workspace to update"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceSchema:
    """Update a workspace.

    Args:
    ----
        workspace_data (WorkspaceCreateSchema): The new workspace data.
        workspace_id (UUID): The ID of the workspace to update.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceModel: The updated workspace.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to update workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this workspace",
        )

    # Update workspace
    updated_workspace = await update_workspace(
        db, workspace_id, workspace_data.model_dump()
    )
    if not updated_workspace:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workspace",
        )

    # Convert model to schema for response serialization
    return WorkspaceSchema(
        id=updated_workspace.id,
        name=updated_workspace.name,
        description=updated_workspace.description,
        default_time_limit=updated_workspace.default_time_limit,
        owner_id=updated_workspace.owner_id,
        created_at=updated_workspace.created_at.isoformat(),
        updated_at=updated_workspace.updated_at.isoformat(),
    )


@router.delete("/{workspace_id}", response_model=MessageSchema)
async def delete_workspace_by_id(
    workspace_id: UUID = Path(..., description="The ID of the workspace to delete"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> MessageSchema:
    """Delete a workspace.

    Args:
    ----
        workspace_id (UUID): The ID of the workspace to delete.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        MessageSchema: Success message.

    """
    # Check if user is authorized to delete workspace
    if not current_user.is_admin and not await is_workspace_owner(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this workspace",
        )

    # First, clean up all template permissions related to this workspace
    from sqlalchemy import delete

    from ...models.template_permission_model import TemplatePermissionModel

    # 1. Find all templates shared with the workspace
    workspace_templates = await get_templates_by_workspace(db, workspace_id)

    # 2. Delete all template permissions for the workspace itself
    workspace_perms_stmt = (
        delete(TemplatePermissionModel)
        .where(TemplatePermissionModel.entity_type == PermissionEntityType.WORKSPACE)
        .where(TemplatePermissionModel.entity_id == workspace_id)
    )
    await db.execute(workspace_perms_stmt)

    # 3. Get all users in the workspace to clean up their permissions
    from ...crud.crud_workspace_users import get_workspace_users

    workspace_users = await get_workspace_users(db, workspace_id)
    user_ids = [user.user_id for user in workspace_users]

    # 4. For each template that was shared with the workspace, delete permissions
    # for users who were part of this workspace
    for template_perm in workspace_templates:
        for user_id in user_ids:
            # Find and delete user permissions for these templates
            user_perm_stmt = (
                delete(TemplatePermissionModel)
                .where(
                    TemplatePermissionModel.template_type == template_perm.template_type
                )
                .where(TemplatePermissionModel.template_id == template_perm.template_id)
                .where(TemplatePermissionModel.entity_type == PermissionEntityType.USER)
                .where(TemplatePermissionModel.entity_id == user_id)
            )
            await db.execute(user_perm_stmt)

    # Commit all permission deletions
    await db.commit()

    # Finally, delete the workspace
    success = await delete_workspace(db, workspace_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return MessageSchema(message="Workspace deleted successfully")


@router.get("/{workspace_id}/users", response_model=list[WorkspaceUserDetailSchema])
async def get_workspace_users_by_workspace_id(
    workspace_id: UUID = Path(..., description="The ID of the workspace"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> list[WorkspaceUserDetailSchema]:
    """Get all users in a workspace with their details.

    Args:
    ----
        workspace_id (UUID): The ID of the workspace.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        list[WorkspaceUserDetailSchema]: The users in the workspace with their details.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to view workspace users
    if not current_user.is_admin and not await is_workspace_member(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace",
        )

    # Get workspace users with their user details
    workspace_users_with_details = await get_workspace_users_with_details(
        db, workspace_id
    )

    # Convert models to schemas with properly formatted dates and user details
    return [
        WorkspaceUserDetailSchema(
            workspace_id=workspace_user.workspace_id,
            user_id=workspace_user.user_id,
            role=workspace_user.role,
            time_limit=workspace_user.time_limit,
            created_at=workspace_user.created_at.isoformat(),
            updated_at=workspace_user.updated_at.isoformat(),
            name=user_details.name,
            email=user_details.email,
        )
        for workspace_user, user_details in workspace_users_with_details
    ]


@router.post("/{workspace_id}/users", response_model=WorkspaceUserSchema)
async def add_user_to_workspace_by_id(
    user_data: WorkspaceUserCreateSchema,
    workspace_id: UUID = Path(..., description="The ID of the workspace"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceUserSchema:
    """Add a user to a workspace.

    Args:
    ----
        user_data (WorkspaceUserCreateSchema): The user data.
        workspace_id (UUID): The ID of the workspace.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceUserSchema: The created workspace user association.

    """
    # Check if user is authorized to add users to workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add users to this workspace",
        )

    # Add user to workspace
    workspace_user = await add_user_to_workspace(db, workspace_id, user_data)
    if not workspace_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace or user not found",
        )

    # Sync template permissions for the new user
    await sync_user_workspace_permissions(db, user_data.user_id, workspace_id)

    # Convert model to schema with properly formatted dates
    return WorkspaceUserSchema(
        workspace_id=workspace_user.workspace_id,
        user_id=workspace_user.user_id,
        role=workspace_user.role,
        time_limit=workspace_user.time_limit,
        created_at=workspace_user.created_at.isoformat(),
        updated_at=workspace_user.updated_at.isoformat(),
    )


@router.delete("/{workspace_id}/users/{user_id}", response_model=MessageSchema)
async def remove_user_from_workspace_by_id(
    workspace_id: UUID = Path(..., description="The ID of the workspace"),
    user_id: UUID = Path(..., description="The ID of the user to remove"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> MessageSchema:
    """Remove a user from a workspace.

    Args:
    ----
        workspace_id (UUID): The ID of the workspace.
        user_id (UUID): The ID of the user to remove.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        MessageSchema: Success message.

    """
    # Check if user is authorized to remove users from workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to remove users from this workspace",
        )

    # Check if user is trying to remove themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself from the workspace",
        )

    # Check if user is trying to remove the workspace owner
    workspace = await get_workspace(db, workspace_id)
    if workspace and workspace.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove the workspace owner",
        )

    # First check if the user is in the workspace to avoid unnecessary operations
    user_in_workspace = await remove_user_from_workspace(db, workspace_id, user_id)
    if not user_in_workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in workspace",
        )

    # After removing the user from workspace, also clean up their template permissions
    # that were granted through this workspace membership

    # 1. Get all templates shared with the workspace
    workspace_templates = await get_templates_by_workspace(db, workspace_id)

    if workspace_templates:
        # 2. For each template, check if the user has a direct permission that was
        # granted through workspace membership and remove it
        from sqlalchemy import and_, delete

        from ...models.template_permission_model import TemplatePermissionModel

        for template_perm in workspace_templates:
            # Delete any user permission for this template
            stmt = delete(TemplatePermissionModel).where(
                and_(
                    TemplatePermissionModel.template_type
                    == template_perm.template_type,
                    TemplatePermissionModel.template_id == template_perm.template_id,
                    TemplatePermissionModel.entity_type == PermissionEntityType.USER,
                    TemplatePermissionModel.entity_id == user_id,
                )
            )
            await db.execute(stmt)

        # Commit all the deletions
        await db.commit()

    return MessageSchema(message="User removed from workspace successfully")


@router.put("/{workspace_id}/users/{user_id}", response_model=WorkspaceUserSchema)
async def update_workspace_user_role(
    user_data: WorkspaceUserUpdateSchema,
    workspace_id: UUID = Path(..., description="The ID of the workspace"),
    user_id: UUID = Path(..., description="The ID of the user to update"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceUserSchema:
    """Update a user's role or time limit in a workspace.

    Args:
    ----
        user_data (WorkspaceUserUpdateSchema): The updated user data.
        workspace_id (UUID): The ID of the workspace.
        user_id (UUID): The ID of the user to update.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceUserSchema: The updated workspace user association.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to update users in this workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update users in this workspace",
        )

    # Check if trying to update the workspace owner's role (not allowed)
    if workspace.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change the workspace owner's role",
        )

    # Update the user's role and/or time limit
    update_data = user_data.model_dump(exclude_unset=True)
    updated_user = await update_workspace_user(db, workspace_id, user_id, update_data)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in workspace",
        )

    return WorkspaceUserSchema(
        workspace_id=updated_user.workspace_id,
        user_id=updated_user.user_id,
        role=updated_user.role,
        time_limit=updated_user.time_limit,
        created_at=updated_user.created_at.isoformat(),
        updated_at=updated_user.updated_at.isoformat(),
    )


@router.get("/{workspace_id}/templates", response_model=list[TemplatePermissionSchema])
async def get_workspace_templates(
    workspace_id: UUID = Path(..., description="The ID of the workspace"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> list[TemplatePermissionSchema]:
    """Get all templates shared with a workspace.

    Args:
    ----
        workspace_id (UUID): The ID of the workspace.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        list[TemplatePermissionSchema]: The templates shared with the workspace.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to view workspace templates
    if not current_user.is_admin and not await is_workspace_member(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace",
        )

    # Get all templates shared with the workspace
    template_permissions = await get_templates_by_workspace(db, workspace_id)

    # Convert to response schema
    return [
        TemplatePermissionSchema(
            id=permission.id,
            template_type=permission.template_type,
            template_id=permission.template_id,
            entity_type=permission.entity_type,
            entity_id=permission.entity_id,
            permission_type=permission.permission_type,
            created_at=permission.created_at.isoformat(),
            updated_at=permission.updated_at.isoformat(),
        )
        for permission in template_permissions
    ]


@router.post(
    "/{workspace_id}/templates",
    response_model=TemplatePermissionSchema,
    status_code=status.HTTP_201_CREATED,
)
async def share_template_with_workspace(
    template_data: WorkspaceTemplateSchema,
    workspace_id: UUID = Path(..., description="The ID of the workspace"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> TemplatePermissionSchema:
    """Share a template with a workspace.

    Args:
    ----
        template_data (WorkspaceTemplateSchema): The template data.
        workspace_id (UUID): The ID of the workspace.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        TemplatePermissionSchema: The created template permission.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to share templates with the workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to share templates with this workspace",
        )

    # Build the template permission
    permission_data = TemplatePermissionCreateSchema(
        template_type=template_data.template_type,
        template_id=template_data.template_id,
        entity_type=PermissionEntityType.WORKSPACE,
        entity_id=workspace_id,
        permission_type=template_data.permission_type,
    )

    # Create the permission for the workspace
    created_permission = await create_template_permission(db, permission_data)

    # Sync permissions for all users in the workspace
    await sync_workspace_template_permissions(db, workspace_id)

    # Return the created permission
    return TemplatePermissionSchema(
        id=created_permission.id,
        template_type=created_permission.template_type,
        template_id=created_permission.template_id,
        entity_type=created_permission.entity_type,
        entity_id=created_permission.entity_id,
        permission_type=created_permission.permission_type,
        created_at=created_permission.created_at.isoformat(),
        updated_at=created_permission.updated_at.isoformat(),
    )


@router.delete(
    "/{workspace_id}/templates/{template_id}",
    response_model=WorkspaceTemplateDeleteSchema,
)
async def remove_template_from_workspace(
    workspace_id: UUID = Path(..., description="The ID of the workspace"),
    template_id: UUID = Path(..., description="The ID of the template"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceTemplateDeleteSchema:
    """Remove a template from a workspace.

    Args:
    ----
        workspace_id (UUID): The ID of the workspace.
        template_id (UUID): The ID of the template.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceTemplateDeleteSchema: Success message.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to remove templates from the workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to remove templates from this workspace",
        )

    # Find any template permission for this workspace and template
    # Try all template types until we find a match
    template_types = [
        "range_templates",
        "vpc_templates",
        "subnet_templates",
        "host_templates",
    ]
    permission = None

    for template_type in template_types:
        permission = await get_workspace_template_permission(
            db, workspace_id, template_type, template_id
        )
        if permission:
            break

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template is not shared with this workspace",
        )

    # Capture the template details before deletion
    template_type = permission.template_type
    template_id = permission.template_id

    # Delete the workspace permission
    success = await delete_template_permission(db, permission.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove template from workspace",
        )

    # Also delete any derived user permissions for this template
    # that were created automatically through workspace membership
    from sqlalchemy import select

    from ...models.template_permission_model import TemplatePermissionModel
    from ...models.workspace_user_model import WorkspaceUserModel

    # Get all users in the workspace
    users_stmt = select(WorkspaceUserModel.user_id).where(
        WorkspaceUserModel.workspace_id == workspace_id
    )
    users_result = await db.execute(users_stmt)
    user_ids = users_result.scalars().all()

    # For each user, delete corresponding template permissions
    for user_id in user_ids:
        # Find the user's permission for this template
        stmt = (
            select(TemplatePermissionModel)
            .where(TemplatePermissionModel.template_type == template_type)
            .where(TemplatePermissionModel.template_id == template_id)
            .where(TemplatePermissionModel.entity_type == PermissionEntityType.USER)
            .where(TemplatePermissionModel.entity_id == user_id)
        )
        result = await db.execute(stmt)
        user_permission = result.scalars().first()

        # Delete the user permission if found
        if user_permission:
            await db.delete(user_permission)

    # Commit all the deletions
    await db.commit()

    # Return success message
    return WorkspaceTemplateDeleteSchema(success=True)
