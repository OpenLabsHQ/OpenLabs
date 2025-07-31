import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..enums.permissions import BlueprintPermissionType, DeployedRangePermissionType
from ..models.permission_models import (
    BlueprintRangePermissionModel,
    DeployedRangePermissionModel,
)
from ..models.range_models import BlueprintRangeModel, DeployedRangeModel

logger = logging.getLogger(__name__)


async def grant_blueprint_permission(
    db: AsyncSession,
    blueprint_range_id: int,
    user_id: int,
    permission_type: BlueprintPermissionType,
    requesting_user_id: int,
) -> BlueprintRangePermissionModel:
    """Grant permission to a blueprint range.

    Args:
    ----
        db: Database session
        blueprint_range_id: ID of blueprint range to grant permission for
        user_id: ID of user to grant permission to
        permission_type: Type of permission to grant
        requesting_user_id: ID of user requesting to grant permission (must be owner)

    Returns:
    -------
        BlueprintRangePermissionModel: The created permission

    Raises:
    ------
        SQLAlchemyError: If database operation fails
        ValueError: If requesting user is not the owner

    """
    # Check ownership - only owners can grant permissions
    stmt = select(BlueprintRangeModel).where(BlueprintRangeModel.id == blueprint_range_id)
    result = await db.execute(stmt)
    blueprint_range = result.scalar_one_or_none()
    
    if not blueprint_range:
        raise ValueError(f"Blueprint range {blueprint_range_id} not found")
    
    if blueprint_range.owner_id != requesting_user_id:
        raise ValueError(f"Only the owner can grant permissions on blueprint range {blueprint_range_id}")

    permission = BlueprintRangePermissionModel(
        blueprint_range_id=blueprint_range_id,
        user_id=user_id,
        permission_type=permission_type,
    )

    db.add(permission)

    try:
        await db.flush()
        await db.refresh(permission)
        logger.debug(
            "Granted %s permission on blueprint range %s to user %s",
            permission_type,
            blueprint_range_id,
            user_id,
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Failed to grant %s permission on blueprint range %s to user %s: %s",
            permission_type,
            blueprint_range_id,
            user_id,
            e,
        )
        raise

    return permission


async def grant_deployed_permission(
    db: AsyncSession,
    deployed_range_id: int,
    user_id: int,
    permission_type: DeployedRangePermissionType,
    requesting_user_id: int,
) -> DeployedRangePermissionModel:
    """Grant permission to a deployed range.

    Args:
    ----
        db: Database session
        deployed_range_id: ID of deployed range to grant permission for
        user_id: ID of user to grant permission to
        permission_type: Type of permission to grant
        requesting_user_id: ID of user requesting to grant permission (must be owner)

    Returns:
    -------
        DeployedRangePermissionModel: The created permission

    Raises:
    ------
        SQLAlchemyError: If database operation fails
        ValueError: If requesting user is not the owner

    """
    # Check ownership
    stmt = select(DeployedRangeModel).where(DeployedRangeModel.id == deployed_range_id)
    result = await db.execute(stmt)
    deployed_range = result.scalar_one_or_none()
    
    if not deployed_range:
        raise ValueError(f"Deployed range {deployed_range_id} not found")
    
    if deployed_range.owner_id != requesting_user_id:
        raise ValueError(f"User {requesting_user_id} is not the owner of deployed range {deployed_range_id}")

    permission = DeployedRangePermissionModel(
        deployed_range_id=deployed_range_id,
        user_id=user_id,
        permission_type=permission_type,
    )

    db.add(permission)

    try:
        await db.flush()
        await db.refresh(permission)
        logger.debug(
            "Granted %s permission on deployed range %s to user %s",
            permission_type,
            deployed_range_id,
            user_id,
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Failed to grant %s permission on deployed range %s to user %s: %s",
            permission_type,
            deployed_range_id,
            user_id,
            e,
        )
        raise

    return permission


async def revoke_blueprint_permission(
    db: AsyncSession,
    blueprint_range_id: int,
    user_id: int,
    permission_type: BlueprintPermissionType,
    requesting_user_id: int,
) -> bool:
    """Revoke permission from a blueprint range.

    Args:
    ----
        db: Database session
        blueprint_range_id: ID of blueprint range to revoke permission from
        user_id: ID of user to revoke permission from
        permission_type: Type of permission to revoke
        requesting_user_id: ID of user requesting to revoke permission (must be owner)

    Returns:
    -------
        bool: True if permission was revoked, False if not found

    Raises:
    ------
        SQLAlchemyError: If database operation fails
        ValueError: If requesting user is not the owner

    """
    # Check ownership
    stmt = select(BlueprintRangeModel).where(BlueprintRangeModel.id == blueprint_range_id)
    result = await db.execute(stmt)
    blueprint_range = result.scalar_one_or_none()
    
    if not blueprint_range:
        raise ValueError(f"Blueprint range {blueprint_range_id} not found")
    
    if blueprint_range.owner_id != requesting_user_id:
        raise ValueError(f"User {requesting_user_id} is not the owner of blueprint range {blueprint_range_id}")

    stmt = select(BlueprintRangePermissionModel).where(
        BlueprintRangePermissionModel.blueprint_range_id == blueprint_range_id,
        BlueprintRangePermissionModel.user_id == user_id,
        BlueprintRangePermissionModel.permission_type == permission_type,
    )
    result = await db.execute(stmt)
    permission = result.scalar_one_or_none()

    if not permission:
        logger.warning(
            "Permission %s on blueprint range %s for user %s not found",
            permission_type,
            blueprint_range_id,
            user_id,
        )
        return False

    try:
        await db.delete(permission)
        await db.flush()
        logger.debug(
            "Revoked %s permission on blueprint range %s from user %s",
            permission_type,
            blueprint_range_id,
            user_id,
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Failed to revoke %s permission on blueprint range %s from user %s: %s",
            permission_type,
            blueprint_range_id,
            user_id,
            e,
        )
        raise

    return True


async def revoke_deployed_permission(
    db: AsyncSession,
    deployed_range_id: int,
    user_id: int,
    permission_type: DeployedRangePermissionType,
    requesting_user_id: int,
) -> bool:
    """Revoke permission from a deployed range.

    Args:
    ----
        db: Database session
        deployed_range_id: ID of deployed range to revoke permission from
        user_id: ID of user to revoke permission from
        permission_type: Type of permission to revoke
        requesting_user_id: ID of user requesting to revoke permission (must be owner)

    Returns:
    -------
        bool: True if permission was revoked, False if not found

    Raises:
    ------
        SQLAlchemyError: If database operation fails
        ValueError: If requesting user is not the owner

    """
    # Check ownership
    stmt = select(DeployedRangeModel).where(DeployedRangeModel.id == deployed_range_id)
    result = await db.execute(stmt)
    deployed_range = result.scalar_one_or_none()
    
    if not deployed_range:
        raise ValueError(f"Deployed range {deployed_range_id} not found")
    
    if deployed_range.owner_id != requesting_user_id:
        raise ValueError(f"User {requesting_user_id} is not the owner of deployed range {deployed_range_id}")

    stmt = select(DeployedRangePermissionModel).where(
        DeployedRangePermissionModel.deployed_range_id == deployed_range_id,
        DeployedRangePermissionModel.user_id == user_id,
        DeployedRangePermissionModel.permission_type == permission_type,
    )
    result = await db.execute(stmt)
    permission = result.scalar_one_or_none()

    if not permission:
        logger.warning(
            "Permission %s on deployed range %s for user %s not found",
            permission_type,
            deployed_range_id,
            user_id,
        )
        return False

    try:
        await db.delete(permission)
        await db.flush()
        logger.debug(
            "Revoked %s permission on deployed range %s from user %s",
            permission_type,
            deployed_range_id,
            user_id,
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Failed to revoke %s permission on deployed range %s from user %s: %s",
            permission_type,
            deployed_range_id,
            user_id,
            e,
        )
        raise

    return True
