import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.host_models import BlueprintHostModel, DeployedHostModel
from ..schemas.host_schemas import (
    BlueprintHostCreateSchema,
    BlueprintHostHeaderSchema,
    BlueprintHostSchema,
    DeployedHostCreateSchema,
)

logger = logging.getLogger(__name__)

# ==================== Blueprints =====================


async def get_blueprint_host_headers(
    db: AsyncSession, user_id: int, is_admin: bool = False, standalone_only: bool = True
) -> list[BlueprintHostHeaderSchema]:
    """Get list of host blueprint headers.

    Args:
    ----
        db (Session): Database connection.
        user_id (int): ID of user requesting data.
        is_admin (bool): Admins can see other user's blueprints. Defaults to False.
        standalone_only (bool): Include only hosts that are standalone blueprints (i.e. those with a null subnet_id). Defaults to True.

    Returns:
    -------
        list[BlueprintHostHeaderSchema]: List of host blueprint header schemas.

    """
    stmt = select(
        BlueprintHostModel.id,
        BlueprintHostModel.hostname,
        BlueprintHostModel.os,
        BlueprintHostModel.spec,
        BlueprintHostModel.size,
        BlueprintHostModel.tags,
    ).select_from(BlueprintHostModel)

    if not is_admin:
        stmt = stmt.filter(BlueprintHostModel.owner_id == user_id)

    if standalone_only:
        stmt = stmt.where(BlueprintHostModel.subnet_id.is_(None))

    result = await db.execute(stmt)

    host_headers = [
        BlueprintHostHeaderSchema.model_validate(row_mapping)
        for row_mapping in result.mappings().all()
    ]

    logger.info(
        "Fetched %s host blueprint headers for user: %s.", len(host_headers), user_id
    )
    return host_headers


async def get_blueprint_host(
    db: AsyncSession, host_id: int, user_id: int, is_admin: bool = False
) -> BlueprintHostSchema | None:
    """Get host blueprint by ID.

    Args:
    ----
        db (Sessions): Database connection.
        host_id (int): ID of the host blueprint.
        user_id (int): ID of user requesting data.
        is_admin (bool): Admins can see other user's blueprints.

    Returns:
    -------
        Optional[BlueprintHostSchema]: Host blueprint schema if it exists.

    """
    host_model = await db.get(BlueprintHostModel, host_id)

    if not host_model:
        logger.info(
            "Failed to fetch host blueprint: %s. Not found in database!", host_id
        )
        return None

    if is_admin or host_model.owner_id == user_id:
        logger.debug("Fetched host blueprint: %s for user: %s.", host_id, user_id)
        return BlueprintHostSchema.model_validate(host_model)

    logger.warning(
        "User: %s is not authorized to fetch host blueprint: %s.",
        host_id,
        user_id,
    )
    return None


def build_blueprint_host_models(
    hosts: list[BlueprintHostCreateSchema], user_id: int
) -> list[BlueprintHostModel]:
    """Build a list of host blueprint ORM models from creation schemas.

    **Note:** These models will only contain the data available in the
    schemas (i.e. no database ID).

    Args:
    ----
        hosts (list[BlueprintHostCreateSchema]): Host object data.
        user_id (int): User who created the hosts.

    Returns:
    -------
        list[BlueprintHostModel]: Corresponding host blueprint models.

    """
    host_models: list[BlueprintHostModel] = []
    for host in hosts:
        host_model = BlueprintHostModel(**host.model_dump(), owner_id=user_id)
        host_models.append(host_model)

    logger.debug(
        "Built %s host blueprint models for user: %s.", len(host_models), user_id
    )
    return host_models


async def create_blueprint_host(
    db: AsyncSession,
    blueprint: BlueprintHostCreateSchema,
    user_id: int,
    subnet_id: int | None = None,
) -> BlueprintHostSchema:
    """Create and add a new host blueprint to the database session.

    **Note:** This function only adds hosts to the database session. It is the responsibility
    of the caller to commit the changes to the database or rollback in the event of
    a failure.

    Args:
    ----
        db (Session): Database connection.
        blueprint (BlueprintHostCreateSchema): Pydantic model of host blueprint data without IDs.
        user_id (int): User who owns the host blueprint.
        subnet_id (Optional[int]): Optional subnet ID to link host back to.

    Returns:
    -------
        BlueprintHostSchema: The newly created host blueprint data schema with it's ID.

    """
    built_models = build_blueprint_host_models([blueprint], user_id)

    # Sanity check that we only have a single host model
    if len(built_models) != 1:
        msg = f"Built {len(built_models) } host blueprint models from a single schema!"
        logger.error(msg)
        raise RuntimeError(msg)

    host_model = built_models[0]

    if subnet_id:
        host_model.subnet_id = subnet_id

    db.add(host_model)
    logger.debug(
        "Added host blueprint model with hostname: %s to database session.",
        host_model.hostname,
    )

    try:
        await db.flush()
        await db.refresh(host_model)
        logger.debug(
            "Successfully flushed host blueprint: %s owned by user: %s",
            host_model.id,
            user_id,
        )
    except Exception as e:
        logger.exception(
            "Failed to flush host blueprint to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise

    return BlueprintHostSchema.model_validate(host_model)


async def delete_blueprint_host(
    db: AsyncSession, host_id: int, user_id: int, is_admin: bool = False
) -> BlueprintHostSchema | None:
    """Delete a standalone host blueprint.

    Only allows deletion if the host blueprint is standalone (i.e. subnet_id is None). This
    function only adds delete queries to the database session. It is the responsibility of
    the caller to commit the changes to the database or rollback in the event of a failure.

    Args:
    ----
        db (Sessions): Database connection.
        host_id (int): ID of the host blueprint.
        user_id (int): ID of user initiating the delete.
        is_admin (bool): Admins can delete other user's blueprints.

    Returns:
    -------
        Optional[BlueprintHostSchema]: Host schema data if it exists in database and was successfully deleted.

    """
    host = await get_blueprint_host(db, host_id, user_id, is_admin)
    if not host:
        logger.warning(
            "Host blueprint: %s not found for deletion as user: %s. Does user have permissions?",
            host_id,
            user_id,
        )
        return None

    host_model = BlueprintHostModel(**host.model_dump())

    if not host_model.is_standalone():
        logger.info(
            "Failed to delete host blueprint: %s. Not a standalone blueprint!",
            host_model.id,
        )
        return None

    if not is_admin and host_model.owner_id != user_id:
        logger.warning(
            "User: %s is not authorized to delete host blueprint: %s.",
            user_id,
            host_model.id,
        )
        return None

    try:
        await db.delete(host_model)
        await db.flush()
        logger.debug(
            "Successfully marked host blueprint: %s for deletion.", host_model.id
        )
    except Exception as e:
        logger.exception(
            "Failed to mark host blueprint: %s for deletion in database session for user: %s, Exception: %s.",
            host_model.id,
            user_id,
            e,
        )
        raise

    return BlueprintHostSchema.model_validate(host_model)


# ==================== Deployed (Instances) =====================


def build_deployed_host_models(
    hosts: list[DeployedHostCreateSchema], user_id: int
) -> list[DeployedHostModel]:
    """Build a list of deployed host ORM models from creation schemas.

    Args:
    ----
        hosts (list[DeployedHostCreateSchema]): Host object data.
        user_id (int): User who created the hosts.

    Returns:
    -------
        list[DeployedHostModel]: Corresponding deployed host models.

    """
    host_models: list[DeployedHostModel] = []
    for host in hosts:
        host_model = DeployedHostModel(**host.model_dump(), owner_id=user_id)
        host_models.append(host_model)

    logger.debug(
        "Built %s deployed host models for user: %s.", len(host_models), user_id
    )
    return host_models


# TODO: Determine if this needs to be kept or removed before PR
# async def create_deployed_host(
#     db: AsyncSession,
#     host: DeployedHostCreateSchema,
#     user_id: int,
#     subnet_id: int | None = None,
# ) -> DeployedHostSchema:
#     """Create and add a new deployed host to the database session.

#     This function only adds hosts to the database session. It is the responsibility
#     of the caller to commit the changes to the database or rollback in the event of
#     a failure.

#     Args:
#     ----
#         db (Session): Database connection.
#         host (DeployedHostCreateSchema): Pydantic model of deployed host data without IDs.
#         user_id (int): User who owns the deployed host.
#         subnet_id (Optional[int]): Optional subnet ID to link host back to.

#     Returns:
#     -------
#         DeployedHostSchema: The newly created deployed host data model with it's ID.

#     """
#     built_models = build_deployed_host_models([host], user_id)

#     # Sanity check that we only have a single host model
#     if len(built_models) != 1:
#         msg = f"Built {len(built_models) } deployed host models from a single schema!"
#         logger.error(msg)
#         raise RuntimeError(msg)

#     host_model = built_models[0]

#     if subnet_id:
#         host_model.subnet_id = subnet_id

#     db.add(host_model)
#     logger.debug(
#         "Added deployed host model for hostname %s to database session.",
#         host_model.hostname,
#     )

#     try:
#         await db.flush()
#         await db.refresh(host_model)
#         logger.debug(
#             "Successfully flushed deployed host: %s owned by user: %s",
#             host_model.id,
#             user_id,
#         )
#     except Exception as e:
#         logger.exception(
#             "Failed to flush deployed host to database session for user: %s. Exception: %s",
#             user_id,
#             e,
#         )
#         raise

#     return DeployedHostSchema.model_validate(host_model)
