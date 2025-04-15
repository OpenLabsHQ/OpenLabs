import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.subnet_models import BlueprintSubnetModel, DeployedSubnetModel
from ..schemas.subnet_schemas import (
    BlueprintSubnetCreateSchema,
    BlueprintSubnetHeaderSchema,
    BlueprintSubnetSchema,
    DeployedSubnetCreateSchema,
)
from .crud_hosts import build_blueprint_host_models, build_deployed_host_models

logger = logging.getLogger(__name__)

# ==================== Blueprints =====================


async def get_blueprint_subnet_headers(
    db: AsyncSession,
    user_id: int,
    is_admin: bool = False,
    standalone_only: bool = True,
) -> list[BlueprintSubnetHeaderSchema]:
    """Get list of subnet blueprint headers.

    Args:
    ----
        db (Session): Database connection.
        user_id (int): ID of user.
        is_admin (bool): Admins can see other user's blueprints.
        standalone_only (bool): Include only subnets that are standalone blueprints (i.e. those with a null vpc_id). Defaults to True.

    Returns:
    -------
        list[BlueprintSubnetHeaderSchema]: List of blueprint subnet header schemas.

    """
    stmt = select(
        BlueprintSubnetModel.id, BlueprintSubnetModel.name, BlueprintSubnetModel.cidr
    ).select_from(BlueprintSubnetModel)

    if not is_admin:
        stmt = stmt.filter(BlueprintSubnetModel.owner_id == user_id)

    if standalone_only:
        stmt = stmt.where(BlueprintSubnetModel.vpc_id.is_(None))

    result = await db.execute(stmt)

    subnet_headers = [
        BlueprintSubnetHeaderSchema.model_validate(row_mapping)
        for row_mapping in result.mappings().all()
    ]

    logger.info(
        "Fetched %s subnet blueprint headers for user: %s.",
        len(subnet_headers),
        user_id,
    )
    return subnet_headers


async def get_blueprint_subnet(
    db: AsyncSession, subnet_id: int, user_id: int, is_admin: bool = False
) -> BlueprintSubnetSchema | None:
    """Get subnet blueprint by ID.

    Args:
    ----
        db (Session): Database connection.
        subnet_id (int): ID of the subnet blueprint.
        user_id (int): ID of the user requesting data.
        is_admin (bool): Admins can see other user's blueprints.

    Returns:
    -------
        Optional[BlueprintSubnetSchema]: Subnet blueprint data if it exists in the database.

    """
    options = [selectinload(BlueprintSubnetModel.hosts)]
    subnet_model = await db.get(BlueprintSubnetModel, subnet_id, options=options)

    if not subnet_model:
        logger.info(
            "Failed to fetch subnet blueprint: %s. Not found in database!", subnet_id
        )
        return None

    if is_admin or subnet_model.owner_id == user_id:
        logger.debug("Fetched subnet blueprint: %s for user %s.", subnet_id, user_id)
        return BlueprintSubnetSchema.model_validate(subnet_model)

    logger.warning(
        "User: %s is not authorized to fetch subnet blueprint: %s.", user_id, subnet_id
    )
    return None


def build_blueprint_subnet_models(
    subnets: list[BlueprintSubnetCreateSchema], user_id: int
) -> list[BlueprintSubnetModel]:
    """Build a list of blueprint subnet ORM models from creation schemas.

    **Note:** These models will only contain the data available in the
    schemas (i.e. no database ID).

    Args:
    ----
        subnets (list[BlueprintSubnetCreateSchema]): Subnet object data.
        user_id (int): User who created the subnets.

    Returns:
    -------
        list[BlueprintSubnetModel]: Corresponding blueprint subnet models.

    """
    subnet_models: list[BlueprintSubnetModel] = []
    for subnet in subnets:
        subnet_model = BlueprintSubnetModel(**subnet.model_dump(), owner_id=user_id)
        subnet_model.hosts = build_blueprint_host_models(subnet.hosts, user_id)
        subnet_models.append(subnet_model)

    logger.debug(
        "Build %s blueprint subnet models for user: %s.", len(subnet_models), user_id
    )
    return subnet_models


async def create_blueprint_subnet(
    db: AsyncSession,
    blueprint: BlueprintSubnetCreateSchema,
    user_id: int,
    vpc_id: int | None = None,
) -> BlueprintSubnetSchema:
    """Create and add a new subnet blueprint to the database session.

    **Note:** This function only adds subnets to the database session. It is the responsibility
    of the caller to commit the changes to the database or rollback in the event of
    a failure.

    Args:
    ----
        db (Session): Database connection.
        blueprint (BlueprintSubnetCreateSchema): Pydantic model of subnet blueprint data without IDs.
        user_id (int): User who owns the new subnet blueprint.
        vpc_id (int | None): Optional VPC ID to link subnet back to.

    Returns:
    -------
        BlueprintSubnetSchema: The newly created subnet blueprint data schema with it's ID.

    """
    built_models = build_blueprint_subnet_models([blueprint], user_id)

    # Sanity check that we only have a single subnet model
    if len(built_models) != 1:
        msg = (
            f"Built {len(built_models) } subnet blueprint models from a single schema!"
        )
        logger.error(msg)
        raise RuntimeError(msg)

    subnet_model = built_models[0]

    if vpc_id:
        subnet_model.vpc_id = vpc_id

    db.add(subnet_model)
    logger.debug(
        "Added subnet blueprint model with name: %s to database session.",
        subnet_model.name,
    )

    try:
        await db.flush()
        await db.refresh(subnet_model)
        logger.debug(
            "Successfully flushed subnet blueprint: %s owned by user: %s.",
            subnet_model.id,
            user_id,
        )
    except Exception as e:
        logger.exception(
            "Failed to flush subnet blueprint to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise

    return BlueprintSubnetSchema.model_validate(subnet_model)


async def delete_blueprint_subnet(
    db: AsyncSession, subnet_id: int, user_id: int, is_admin: bool = False
) -> BlueprintSubnetSchema | None:
    """Delete a standalone subnet blueprint.

    Only allows deletion if the subnet blueprint is standalone (i.e. subnet_id is None). This
    function only adds delete queries to the database session. It is the responsibility of
    the caller to commit the changes to the database or rollback in the event of a failure.

    Args:
    ----
        db (Sessions): Database connection.
        subnet_id (int): ID of the subnet blueprint.
        user_id (int): ID of user initiating the delete.
        is_admin (bool): Admins can delete other user's blueprints.

    Returns:
    -------
        Optional[BlueprintSubnetSchema]: Subnet schema data if it exists in database and was successfully deleted.

    """
    subnet = await get_blueprint_subnet(db, subnet_id, user_id, is_admin)
    if not subnet:
        logger.warning(
            "Subnet blueprint: %s not found for deletion as user: %s. Does user have permissions?",
            subnet_id,
            user_id,
        )
        return None

    subnet_model = BlueprintSubnetModel(**subnet.model_dump())

    if not subnet_model.is_standalone():
        logger.info(
            "Failed to delete subnet blueprint: %s. Not a standalone blueprint!",
            subnet_model.id,
        )
        return None

    if not is_admin and subnet_model.owner_id != user_id:
        logger.warning(
            "User: %s is not authorized to delete subnet blueprint: %s.",
            user_id,
            subnet_model.id,
        )
        return None

    try:
        await db.delete(subnet_model)
        await db.flush()
        logger.debug(
            "Successfully marked subnet blueprint: %s for deletion.", subnet_model.id
        )
    except Exception as e:
        logger.exception(
            "Failed to mark subnet blueprint: %s for deletion in database session for user: %s, Exception: %s.",
            subnet_model.id,
            user_id,
            e,
        )
        raise

    return BlueprintSubnetSchema.model_validate(subnet_model)


# ==================== Deployed (Instances) =====================


def build_deployed_subnet_models(
    subnets: list[DeployedSubnetCreateSchema], user_id: int
) -> list[DeployedSubnetModel]:
    """Build a list of deployed subnet ORM models from creation schemas.

    Args:
    ----
        subnets (list[DeployedSubnetCreateSchema]): Subnet object data.
        user_id (int): User who created the subnets.

    Returns:
    -------
        list[DeployedSubnetModel]: Corresponding deployed subnet models.

    """
    subnet_models: list[DeployedSubnetModel] = []
    for subnet in subnets:
        subnet_model = DeployedSubnetModel(**subnet.model_dump(), owner_id=user_id)
        subnet_model.hosts = build_deployed_host_models(subnet.hosts, user_id)
        subnet_models.append(subnet_model)

    logger.debug(
        "Build %s deployed subnet models for user: %s.", len(subnet_models), user_id
    )
    return subnet_models
