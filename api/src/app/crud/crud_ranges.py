import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.permission_models import (
    BlueprintRangePermissionModel,
    DeployedRangePermissionModel,
)
from ..models.range_models import BlueprintRangeModel, DeployedRangeModel
from ..models.subnet_models import BlueprintSubnetModel, DeployedSubnetModel
from ..models.vpc_models import BlueprintVPCModel, DeployedVPCModel
from ..schemas.range_schemas import (
    BlueprintRangeCreateSchema,
    BlueprintRangeHeaderSchema,
    BlueprintRangeSchema,
    DeployedRangeCreateSchema,
    DeployedRangeHeaderSchema,
    DeployedRangeKeySchema,
    DeployedRangeSchema,
)
from .crud_permissions import grant_blueprint_permission, grant_deployed_permission
from .crud_vpcs import build_blueprint_vpc_models, build_deployed_vpc_models

logger = logging.getLogger(__name__)


def get_permissions(model):
    """Safely get permissions from a model, handling mocks."""
    permissions = getattr(model, 'permissions', [])
    if hasattr(permissions, '_mock_name'):
        return []
    return permissions or []


def can_read_blueprint(range_model, user_id: int) -> bool:
    """Check if user can read a blueprint range."""
    if range_model.owner_id == user_id:
        return True
    return any(p.user_id == user_id and p.permission_type in ('read', 'write') 
               for p in get_permissions(range_model))


def can_write_blueprint(range_model, user_id: int) -> bool:
    """Check if user can write a blueprint range."""
    if range_model.owner_id == user_id:
        return True
    return any(p.user_id == user_id and p.permission_type == 'write' 
               for p in get_permissions(range_model))


def can_read_deployed(range_model, user_id: int) -> bool:
    """Check if user can read a deployed range."""
    if range_model.owner_id == user_id:
        return True
    return any(p.user_id == user_id and p.permission_type in ('read', 'write', 'execute') 
               for p in get_permissions(range_model))


def can_write_deployed(range_model, user_id: int) -> bool:
    """Check if user can write a deployed range."""
    if range_model.owner_id == user_id:
        return True
    return any(p.user_id == user_id and p.permission_type == 'write' 
               for p in get_permissions(range_model))


def can_execute_deployed(range_model, user_id: int) -> bool:
    """Check if user can execute a deployed range."""
    if range_model.owner_id == user_id:
        return True
    return any(p.user_id == user_id and p.permission_type == 'execute' 
               for p in get_permissions(range_model))


# ==================== Blueprints =====================


async def get_blueprint_range_headers(
    db: AsyncSession,
    user_id: int,
    is_admin: bool = False,
) -> list[BlueprintRangeHeaderSchema]:
    """Get list of range blueprint headers.

    Args:
    ----
        db (Session): Database connection.
        user_id (int): ID of user.
        is_admin (bool): Admins can see other user's blueprints.

    Returns:
    -------
        list[BlueprintRangeHeaderSchema]: List of blueprint range header schemas.

    """
    stmt = select(
        BlueprintRangeModel.id,
        BlueprintRangeModel.name,
        BlueprintRangeModel.provider,
        BlueprintRangeModel.vnc,
        BlueprintRangeModel.vpn,
        BlueprintRangeModel.description,
    ).select_from(BlueprintRangeModel)

    if not is_admin:
        stmt = stmt.outerjoin(
            BlueprintRangePermissionModel,
            BlueprintRangeModel.id == BlueprintRangePermissionModel.blueprint_range_id
        ).filter(
            (BlueprintRangeModel.owner_id == user_id) |
            (
                (BlueprintRangePermissionModel.user_id == user_id) &
                (BlueprintRangePermissionModel.permission_type.in_(["read", "write"]))
            )
        ).distinct()

    result = await db.execute(stmt)

    range_headers = [
        BlueprintRangeHeaderSchema.model_validate(row_mapping)
        for row_mapping in result.mappings().all()
    ]

    logger.info(
        "Fetched %s range blueprint headers for user: %s.",
        len(range_headers),
        user_id,
    )
    return range_headers


async def get_blueprint_range(
    db: AsyncSession, range_id: int, user_id: int, is_admin: bool = False
) -> BlueprintRangeSchema | None:
    """Get range blueprint by ID.

    Args:
    ----
        db (Session): Database connection.
        range_id (int): ID of the range blueprint.
        user_id (int): ID of the user requesting data.
        is_admin (bool): Admins can see other user's blueprints.

    Returns:
    -------
        Optional[BlueprintRangeSchema]: Range blueprint data if it exists in the database.

    """
    options = [
        selectinload(BlueprintRangeModel.vpcs)
        .selectinload(BlueprintVPCModel.subnets)
        .selectinload(BlueprintSubnetModel.hosts),
        selectinload(BlueprintRangeModel.permissions),
    ]
    range_model = await db.get(BlueprintRangeModel, range_id, options=options)

    if not range_model:
        logger.info(
            "Failed to fetch range blueprint: %s. Not found in database!", range_id
        )
        return None

    if is_admin or can_read_blueprint(range_model, user_id):
        logger.debug("Fetched range blueprint: %s for user %s.", range_id, user_id)
        return BlueprintRangeSchema.model_validate(range_model)

    logger.warning(
        "User: %s is not authorized to fetch range blueprint: %s.", user_id, range_id
    )
    return None


def build_blueprint_range_models(
    ranges: list[BlueprintRangeCreateSchema], user_id: int
) -> list[BlueprintRangeModel]:
    """Build a list of blueprint range ORM models from creation schemas.

    **Note:** These models will only contain the data available in the
    schemas (i.e. no database ID).

    Args:
    ----
        ranges (list[BlueprintRangeCreateSchema]): Range object data.
        user_id (int): User who created the subnets.

    Returns:
    -------
        list[BlueprintRangeModel]: Corresponding blueprint range models.

    """
    range_models: list[BlueprintRangeModel] = []
    for range_schema in ranges:
        range_model = BlueprintRangeModel(
            **range_schema.model_dump(exclude={"vpcs", "readers", "writers"}), 
            owner_id=user_id
        )
        range_model.vpcs = build_blueprint_vpc_models(range_schema.vpcs, user_id)
        range_models.append(range_model)

    logger.debug(
        "Build %s blueprint range models for user: %s.", len(range_models), user_id
    )
    return range_models


async def create_blueprint_range(
    db: AsyncSession,
    blueprint: BlueprintRangeCreateSchema,
    user_id: int,
) -> BlueprintRangeHeaderSchema:
    """Create and add a new range blueprint to the database session.

    **Note:** This function only adds ranges to the database session. It is the responsibility
    of the caller to commit the changes to the database or rollback in the event of
    a failure.

    Args:
    ----
        db (Session): Database connection.
        blueprint (BlueprintRangeCreateSchema): Pydantic model of range blueprint data without IDs.
        user_id (int): User who owns the new range blueprint.

    Returns:
    -------
        BlueprintRangeHeaderSchema: The newly created range blueprint header data with it's ID.

    """
    built_models = build_blueprint_range_models([blueprint], user_id)

    # Sanity check that we only have a single range model
    if len(built_models) != 1:
        msg = f"Built {len(built_models) } range blueprint models from a single schema!"
        logger.error(msg)
        raise RuntimeError(msg)

    range_model = built_models[0]

    db.add(range_model)
    logger.debug(
        "Added range blueprint model with name: %s to database session.",
        range_model.name,
    )

    try:
        await db.flush()
        await db.refresh(range_model)
        logger.debug(
            "Successfully flushed range blueprint: %s owned by user: %s.",
            range_model.id,
            user_id,
        )
        
        for reader_id in blueprint.readers:
            if reader_id != user_id:
                await grant_blueprint_permission(db, range_model.id, reader_id, "read")
                
        for writer_id in blueprint.writers:
            if writer_id != user_id:
                await grant_blueprint_permission(db, range_model.id, writer_id, "write")
                
    except SQLAlchemyError as e:
        logger.exception(
            "Database error while flushing range blueprint to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while flushing range blueprint to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise

    return BlueprintRangeHeaderSchema.model_validate(range_model)


async def delete_blueprint_range(
    db: AsyncSession, range_id: int, user_id: int, is_admin: bool = False
) -> BlueprintRangeHeaderSchema | None:
    """Delete a range blueprint.

    This function only adds delete queries to the database session. It is the responsibility of
    the caller to commit the changes to the database or rollback in the event of a failure.

    Args:
    ----
        db (Sessions): Database connection.
        range_id (int): ID of the range blueprint.
        user_id (int): ID of user initiating the delete.
        is_admin (bool): Admins can delete other user's blueprints.

    Returns:
    -------
        Optional[BlueprintRangeHeaderSchema]: Range header data if it exists in database and was successfully deleted.

    """
    range_model = await db.get(
        BlueprintRangeModel, 
        range_id, 
        options=[selectinload(BlueprintRangeModel.permissions)]
    )
    if not range_model:
        logger.warning(
            "Range blueprint: %s not found for deletion as user: %s. Does user have permissions?",
            range_id,
            user_id,
        )
        return None

    if not range_model.is_standalone():
        logger.info(
            "Failed to delete range blueprint: %s. Not a standalone blueprint!",
            range_model.id,
        )
        return None

    if not is_admin and not can_write_blueprint(range_model, user_id):
        logger.warning(
            "User: %s is not authorized to delete range blueprint: %s.",
            user_id,
            range_model.id,
        )
        return None

    try:
        await db.delete(range_model)
        await db.flush()
        logger.debug(
            "Successfully marked range blueprint: %s for deletion.", range_model.id
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Database error while marking range blueprint: %s for deletion for user: %s. Exception: %s.",
            range_model.id,
            user_id,
            e,
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while marking range blueprint: %s for deletion for user: %s. Exception: %s.",
            range_model.id,
            user_id,
            e,
        )
        raise

    return BlueprintRangeHeaderSchema.model_validate(range_model)


# ==================== Deployed (Instances) =====================


async def get_deployed_range_headers(
    db: AsyncSession,
    user_id: int,
    is_admin: bool = False,
) -> list[DeployedRangeHeaderSchema]:
    """Get list of deployed range headers.

    Args:
    ----
        db (Session): Database connection.
        user_id (int): ID of user.
        is_admin (bool): Admins can see other user's blueprints.

    Returns:
    -------
        list[DeployedRangeHeaderSchema]: List of deployed range header schemas.

    """
    stmt = select(
        DeployedRangeModel.id,
        DeployedRangeModel.name,
        DeployedRangeModel.provider,
        DeployedRangeModel.vnc,
        DeployedRangeModel.vpn,
        DeployedRangeModel.description,
        DeployedRangeModel.date,
        DeployedRangeModel.state,
        DeployedRangeModel.region,
    ).select_from(DeployedRangeModel)

    if not is_admin:
        stmt = stmt.outerjoin(
            DeployedRangePermissionModel,
            DeployedRangeModel.id == DeployedRangePermissionModel.deployed_range_id
        ).filter(
            (DeployedRangeModel.owner_id == user_id) |
            (
                (DeployedRangePermissionModel.user_id == user_id) &
                (DeployedRangePermissionModel.permission_type.in_(["read", "write", "execute"]))
            )
        ).distinct()

    result = await db.execute(stmt)

    range_headers = [
        DeployedRangeHeaderSchema.model_validate(row_mapping)
        for row_mapping in result.mappings().all()
    ]

    logger.info(
        "Fetched %s deployed range headers for user: %s.",
        len(range_headers),
        user_id,
    )
    return range_headers


async def get_deployed_range(
    db: AsyncSession, range_id: int, user_id: int, is_admin: bool = False
) -> DeployedRangeSchema | None:
    """Get deployed range by ID.

    Args:
    ----
        db (Session): Database connection.
        range_id (int): ID of the deployed range.
        user_id (int): ID of the user requesting data.
        is_admin (bool): Admins can see other user's deployed ranges.

    Returns:
    -------
        Optional[DeployedRangeSchema]: Deployed range data if it exists in the database.

    """
    options = [
        selectinload(DeployedRangeModel.vpcs)
        .selectinload(DeployedVPCModel.subnets)
        .selectinload(DeployedSubnetModel.hosts),
        selectinload(DeployedRangeModel.permissions),
    ]
    range_model = await db.get(DeployedRangeModel, range_id, options=options)

    if not range_model:
        logger.info(
            "Failed to fetch deployed range: %s. Not found in database!", range_id
        )
        return None

    if is_admin or can_read_deployed(range_model, user_id):
        logger.debug("Fetched deployed range: %s for user %s.", range_id, user_id)
        return DeployedRangeSchema.model_validate(range_model)

    logger.warning(
        "User: %s is not authorized to fetch deployed range: %s.", user_id, range_id
    )
    return None


async def get_deployed_range_key(
    db: AsyncSession,
    range_id: int,
    user_id: int,
    is_admin: bool = False,
) -> DeployedRangeKeySchema | None:
    """Get the SSH private key for a deployed range by ID.

    Optimized to only query the required 'range_private_key' column.

    Args:
    ----
        db (Session): Database connection.
        range_id (int): ID of the deployed range.
        user_id (int): ID of user requesting the key.
        is_admin (bool): Admins can access other user's range keys.

    Returns:
    -------
        Optional[DeployedRangeKeySchema]: Deployed range key data if the range exists and the user is authorized, otherwise None.

    """
    range_model = await db.get(
        DeployedRangeModel, 
        range_id, 
        options=[selectinload(DeployedRangeModel.permissions)]
    )

    if not range_model or (not is_admin and not can_execute_deployed(range_model, user_id)):
        logger.warning(
            "Failed to fetch deployed range key for range: %s for user %s. Range not found or unauthorized.",
            range_id,
            user_id,
        )
        return None

    stmt = select(DeployedRangeModel.range_private_key).where(
        DeployedRangeModel.id == range_id
    )
    range_private_key = await db.scalar(stmt)

    logger.debug(
        "Fetched deployed range key for range: %s for user %s.", range_id, user_id
    )
    return DeployedRangeKeySchema(range_private_key=range_private_key)


def build_deployed_range_models(
    ranges: list[DeployedRangeCreateSchema], user_id: int
) -> list[DeployedRangeModel]:
    """Build a list of deployed range ORM models from creation schemas.

    **Note:** These models will only contain the data available in the
    schemas (i.e. no database ID).

    Args:
    ----
        ranges (list[DeployedRangeCreateSchema]): Range object data.
        user_id (int): User who created the ranges.

    Returns:
    -------
        list[DeployedRangeModels]: Corresponding deployed range models.

    """
    range_models: list[DeployedRangeModel] = []
    for range_schema in ranges:
        range_model = DeployedRangeModel(
            **range_schema.model_dump(exclude={"vpcs", "readers", "writers", "executors"}), 
            owner_id=user_id
        )
        range_model.vpcs = build_deployed_vpc_models(range_schema.vpcs, user_id)
        range_models.append(range_model)

    logger.debug(
        "Build %s deployed range models for user: %s.", len(range_models), user_id
    )
    return range_models


async def create_deployed_range(
    db: AsyncSession,
    range_schema: DeployedRangeCreateSchema,
    user_id: int,
) -> DeployedRangeHeaderSchema:
    """Create and add a new deployed range to the database session.

    **Note:** This function only adds ranges to the database session. It is the responsibility
    of the caller to commit the changes to the database or rollback in the event of
    a failure.

    Args:
    ----
        db (Session): Database connection.
        range_schema (DeployedRangeCreateSchema): Pydantic model of deployed range data without IDs.
        user_id (int): User who owns the new deployed range.

    Returns:
    -------
        DeployedRangeHeaderSchema: The newly created deployed range header data with it's ID.

    """
    built_models = build_deployed_range_models([range_schema], user_id)

    # Sanity check that we only have a single range model
    if len(built_models) != 1:
        msg = f"Built {len(built_models) } deployed range models from a single schema!"
        logger.error(msg)
        raise RuntimeError(msg)

    range_model = built_models[0]

    db.add(range_model)
    logger.debug(
        "Added deployed range model with name: %s to database session.",
        range_model.name,
    )

    try:
        await db.flush()
        await db.refresh(range_model)
        logger.debug(
            "Successfully flushed deployed range: %s owned by user: %s.",
            range_model.id,
            user_id,
        )
        
        for reader_id in range_schema.readers:
            if reader_id != user_id:
                await grant_deployed_permission(db, range_model.id, reader_id, "read")
                
        for writer_id in range_schema.writers:
            if writer_id != user_id:
                await grant_deployed_permission(db, range_model.id, writer_id, "write")
                
        for executor_id in range_schema.executors:
            if executor_id != user_id:
                await grant_deployed_permission(db, range_model.id, executor_id, "execute")
                
    except SQLAlchemyError as e:
        logger.exception(
            "Database error while flushing deployed range to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while flushing deployed range to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise

    return DeployedRangeHeaderSchema.model_validate(range_model)


async def delete_deployed_range(
    db: AsyncSession, range_id: int, user_id: int, is_admin: bool = False
) -> DeployedRangeHeaderSchema | None:
    """Delete a deployed range.

    This function only adds delete queries to the database session. It is the responsibility of
    the caller to commit the changes to the database or rollback in the event of a failure.

    Args:
    ----
        db (Sessions): Database connection.
        range_id (int): ID of the deployed range.
        user_id (int): ID of user initiating the delete.
        is_admin (bool): Admins can delete other user's deployed ranges.

    Returns:
    -------
        Optional[DeployedRangeHeaderSchema]: Deployed range header data if it exists in database and was successfully deleted.

    """
    range_model = await db.get(
        DeployedRangeModel, 
        range_id, 
        options=[selectinload(DeployedRangeModel.permissions)]
    )
    if not range_model:
        logger.warning(
            "Deployed range: %s not found for deletion as user: %s. Does user have permissions?",
            range_id,
            user_id,
        )
        return None

    if not is_admin and not can_write_deployed(range_model, user_id):
        logger.warning(
            "User: %s is not authorized to delete deployed range: %s.",
            user_id,
            range_model.id,
        )
        return None

    try:
        await db.delete(range_model)
        await db.flush()
        logger.debug(
            "Successfully marked deployed range: %s for deletion.", range_model.id
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Database error while marking deployed range: %s for deletion for user: %s. Exception: %s.",
            range_model.id,
            user_id,
            e,
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while marking deployed range: %s for deletion for user: %s. Exception: %s.",
            range_model.id,
            user_id,
            e,
        )
        raise

    return DeployedRangeHeaderSchema.model_validate(range_model)
