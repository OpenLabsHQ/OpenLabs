from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_workspace_users import (
    add_user_to_workspace,
    get_workspace_users,
    remove_user_from_workspace,
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
from ...models.user_model import UserModel
from ...schemas.message_schema import MessageSchema
from ...schemas.workspace_schema import (
    WorkspaceCreateSchema,
    WorkspaceSchema,
)
from ...schemas.workspace_user_schema import (
    WorkspaceUserCreateSchema,
    WorkspaceUserSchema,
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
    # Only allow admins to create workspaces
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create workspaces",
        )

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

    # Delete workspace
    success = await delete_workspace(db, workspace_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return MessageSchema(message="Workspace deleted successfully")


@router.get("/{workspace_id}/users", response_model=list[WorkspaceUserSchema])
async def get_workspace_users_by_workspace_id(
    workspace_id: UUID = Path(..., description="The ID of the workspace"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> list[WorkspaceUserSchema]:
    """Get all users in a workspace.

    Args:
    ----
        workspace_id (UUID): The ID of the workspace.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        list[WorkspaceUserSchema]: The users in the workspace.

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

    workspace_users = await get_workspace_users(db, workspace_id)

    # Convert models to schemas with properly formatted dates
    return [
        WorkspaceUserSchema(
            workspace_id=user.workspace_id,
            user_id=user.user_id,
            role=user.role,
            time_limit=user.time_limit,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )
        for user in workspace_users
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

    # Remove user from workspace
    success = await remove_user_from_workspace(db, workspace_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in workspace",
        )

    return MessageSchema(message="User removed from workspace successfully")
