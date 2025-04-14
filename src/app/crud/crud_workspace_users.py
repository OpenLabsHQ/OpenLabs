import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from ..enums.workspace_roles import WorkspaceRole
from ..models.user_model import UserModel
from ..models.workspace_user_model import WorkspaceUserModel
from ..schemas.workspace_user_schema import WorkspaceUserCreateSchema
from .crud_workspaces import get_workspace

logger = logging.getLogger(__name__)


async def add_user_to_workspace(
    db: AsyncSession,
    workspace_id: UUID,
    user_data: WorkspaceUserCreateSchema,
) -> WorkspaceUserModel | None:
    """Add a user to a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (UUID): Workspace ID.
        user_data (WorkspaceUserCreateSchema): User data including role and optional time limit.

    Returns:
    -------
        WorkspaceUserModel | None: The created workspace user association, or None if the
        workspace or user doesn't exist.

    """
    # Get the workspace to check it exists and get default time limit
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        return None

    # Check if user exists
    stmt = select(UserModel).where(UserModel.id == user_data.user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        return None

    # Check if user is already in workspace
    workspace_user_stmt = (
        select(WorkspaceUserModel)
        .where(WorkspaceUserModel.workspace_id == workspace_id)
        .where(WorkspaceUserModel.user_id == user_data.user_id)
    )
    workspace_user_result = await db.execute(workspace_user_stmt)
    existing_user = workspace_user_result.scalars().first()
    if existing_user:
        # Update the existing user instead of creating a new one
        if user_data.role is not None:
            existing_user.role = user_data.role
        if user_data.time_limit is not None:
            existing_user.time_limit = user_data.time_limit
        existing_user.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(existing_user)
        return existing_user

    # Use the workspace's default time limit if not specified
    time_limit = (
        user_data.time_limit
        if user_data.time_limit is not None
        else workspace.default_time_limit
    )

    # Create the workspace user association
    workspace_user = WorkspaceUserModel(
        workspace_id=workspace_id,
        user_id=user_data.user_id,
        role=user_data.role,
        time_limit=time_limit,
    )

    # Set datetime fields after instantiation
    workspace_user.created_at = datetime.now(UTC)
    workspace_user.updated_at = datetime.now(UTC)

    db.add(workspace_user)
    await db.commit()

    return workspace_user


async def get_workspace_user(
    db: AsyncSession, workspace_id: UUID, user_id: UUID
) -> WorkspaceUserModel | None:
    """Get a user's association with a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (UUID): Workspace ID.
        user_id (UUID): User ID.

    Returns:
    -------
        WorkspaceUserModel | None: The workspace user association if found, None otherwise.

    """
    stmt = (
        select(WorkspaceUserModel)
        .where(WorkspaceUserModel.workspace_id == workspace_id)
        .where(WorkspaceUserModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_workspace_users(
    db: AsyncSession, workspace_id: UUID
) -> list[WorkspaceUserModel]:
    """Get all users in a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (UUID): Workspace ID.

    Returns:
    -------
        list[WorkspaceUserModel]: List of workspace user associations.

    """
    stmt = select(WorkspaceUserModel).where(
        WorkspaceUserModel.workspace_id == workspace_id
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_users_not_in_workspace(
    db: AsyncSession, workspace_id: UUID
) -> list[UserModel]:
    """Get all users not in a specific workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (UUID): Workspace ID to exclude users from.

    Returns:
    -------
        list[UserModel]: List of users not in the workspace.

    """
    # First, get all user IDs that are already in the workspace
    subquery = (
        select(WorkspaceUserModel.user_id)
        .where(WorkspaceUserModel.workspace_id == workspace_id)
        .scalar_subquery()
    )

    # Then query all users where their ID is not in the list of workspace users
    stmt = select(UserModel).where(UserModel.id.not_in(subquery))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_workspace_admins(
    db: AsyncSession, workspace_id: UUID
) -> list[WorkspaceUserModel]:
    """Get all admin users in a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (UUID): Workspace ID.

    Returns:
    -------
        list[WorkspaceUserModel]: List of workspace admin user associations.

    """
    stmt = (
        select(WorkspaceUserModel)
        .where(WorkspaceUserModel.workspace_id == workspace_id)
        .where(WorkspaceUserModel.role == WorkspaceRole.ADMIN)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_workspace_user(
    db: AsyncSession,
    workspace_id: UUID,
    user_id: UUID,
    role: WorkspaceRole | None = None,
    time_limit: int | None = None,
) -> WorkspaceUserModel | None:
    """Update a user's role or time limit in a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (UUID): Workspace ID.
        user_id (UUID): User ID.
        role (WorkspaceRole | None): New role, or None to keep current role.
        time_limit (int | None): New time limit, or None to keep current limit.

    Returns:
    -------
        WorkspaceUserModel | None: The updated workspace user if found, None otherwise.

    """
    workspace_user = await get_workspace_user(db, workspace_id, user_id)
    if not workspace_user:
        return None

    if role is not None:
        workspace_user.role = role
    if time_limit is not None:
        workspace_user.time_limit = time_limit

    workspace_user.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(workspace_user)
    return workspace_user


async def remove_user_from_workspace(
    db: AsyncSession, workspace_id: UUID, user_id: UUID
) -> bool:
    """Remove a user from a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (UUID): Workspace ID.
        user_id (UUID): User ID.

    Returns:
    -------
        bool: True if removed, False otherwise.

    """
    workspace_user = await get_workspace_user(db, workspace_id, user_id)
    if not workspace_user:
        return False

    await db.delete(workspace_user)
    await db.commit()
    return True
