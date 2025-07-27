import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from ..models.permission_models import (
    BlueprintRangePermissionModel,
    DeployedRangePermissionModel,
)

logger = logging.getLogger(__name__)


async def grant_blueprint_permission(
    db: AsyncSession,
    blueprint_range_id: int,
    user_id: int, 
    permission_type: Literal["read", "write"],
) -> BlueprintRangePermissionModel:
    """Grant permission to a blueprint range.
    
    Args:
    ----
        db: Database session
        blueprint_range_id: ID of blueprint range to grant permission for
        user_id: ID of user to grant permission to
        permission_type: Type of permission to grant
        
    Returns:
    -------
        BlueprintRangePermissionModel: The created permission
        
    Raises:
    ------
        SQLAlchemyError: If database operation fails
    """
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
    permission_type: Literal["read", "write", "execute"],
) -> DeployedRangePermissionModel:
    """Grant permission to a deployed range.
    
    Args:
    ----
        db: Database session
        deployed_range_id: ID of deployed range to grant permission for
        user_id: ID of user to grant permission to
        permission_type: Type of permission to grant
        
    Returns:
    -------
        DeployedRangePermissionModel: The created permission
        
    Raises:
    ------
        SQLAlchemyError: If database operation fails
    """
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
    permission_type: Literal["read", "write"],
) -> bool:
    """Revoke permission from a blueprint range.
    
    Args:
    ----
        db: Database session
        blueprint_range_id: ID of blueprint range to revoke permission from
        user_id: ID of user to revoke permission from
        permission_type: Type of permission to revoke
        
    Returns:
    -------
        bool: True if permission was revoked, False if not found
        
    Raises:
    ------
        SQLAlchemyError: If database operation fails
    """
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
    permission_type: Literal["read", "write", "execute"],
) -> bool:
    """Revoke permission from a deployed range.
    
    Args:
    ----
        db: Database session
        deployed_range_id: ID of deployed range to revoke permission from
        user_id: ID of user to revoke permission from
        permission_type: Type of permission to revoke
        
    Returns:
    -------
        bool: True if permission was revoked, False if not found
        
    Raises:
    ------
        SQLAlchemyError: If database operation fails
    """
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
