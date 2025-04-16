import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.subnet_models import BlueprintSubnetModel
from ..models.vpc_models import BlueprintVPCModel, DeployedVPCModel
from ..schemas.vpc_schemas import (
    BlueprintVPCCreateSchema,
    BlueprintVPCHeaderSchema,
    BlueprintVPCSchema,
    DeployedVPCCreateSchema,
)
from .crud_subnets import build_blueprint_subnet_models, build_deployed_subnet_models

logger = logging.getLogger(__name__)

# ==================== Blueprints =====================


async def get_blueprint_vpc_headers(
    db: AsyncSession,
    user_id: int,
    is_admin: bool = False,
    standalone_only: bool = True,
) -> list[BlueprintVPCHeaderSchema]:
    """Get list of VPC blueprint headers.

    Args:
    ----
        db (Session): Database connection.
        user_id (int): ID of user.
        is_admin (bool): Admins can see other user's blueprints.
        standalone_only (bool): Include only VPCs that are standalone blueprints (i.e. those with a null range_id). Defaults to True.

    Returns:
    -------
        list[BlueprintVPCHeaderSchema]: List of blueprint VPC header schemas.

    """
    stmt = select(
        BlueprintVPCModel.id, BlueprintVPCModel.name, BlueprintVPCModel.cidr
    ).select_from(BlueprintVPCModel)

    if not is_admin:
        stmt = stmt.filter(BlueprintVPCModel.owner_id == user_id)

    if standalone_only:
        stmt = stmt.where(BlueprintVPCModel.range_id.is_(None))

    result = await db.execute(stmt)

    vpc_headers = [
        BlueprintVPCHeaderSchema.model_validate(row_mapping)
        for row_mapping in result.mappings().all()
    ]

    logger.info(
        "Fetched %s VPC blueprint headers for user: %s.",
        len(vpc_headers),
        user_id,
    )
    return vpc_headers


async def get_blueprint_vpc(
    db: AsyncSession, vpc_id: int, user_id: int, is_admin: bool = False
) -> BlueprintVPCSchema | None:
    """Get VPC blueprint by ID.

    Args:
    ----
        db (Session): Database connection.
        vpc_id (int): ID of the VPC blueprint.
        user_id (int): ID of the user requesting data.
        is_admin (bool): Admins can see other user's blueprints.

    Returns:
    -------
        Optional[BlueprintVPCSchema]: VPC blueprint data if it exists in the database.

    """
    options = [
        selectinload(BlueprintVPCModel.subnets).selectinload(
            BlueprintSubnetModel.hosts
        ),
    ]
    vpc_model = await db.get(BlueprintVPCModel, vpc_id, options=options)

    if not vpc_model:
        logger.info("Failed to fetch VPC blueprint: %s. Not found in database!", vpc_id)
        return None

    if is_admin or vpc_model.owner_id == user_id:
        logger.debug("Fetched VPC blueprint: %s for user %s.", vpc_id, user_id)
        return BlueprintVPCSchema.model_validate(vpc_model)

    logger.warning(
        "User: %s is not authorized to fetch VPC blueprint: %s.", user_id, vpc_id
    )
    return None


def build_blueprint_vpc_models(
    vpcs: list[BlueprintVPCCreateSchema], user_id: int
) -> list[BlueprintVPCModel]:
    """Build a list of blueprint VPC ORM models from creation schemas.

    **Note:** These models will only contain the data available in the
    schemas (i.e. no database ID).

    Args:
    ----
        vpcs (list[BlueprintVPCCreateSchema]): VPC object data.
        user_id (int): User who created the subnets.

    Returns:
    -------
        list[BlueprintVPCModel]: Corresponding blueprint VPC models.

    """
    vpc_models: list[BlueprintVPCModel] = []
    for vpc in vpcs:
        vpc_model = BlueprintVPCModel(**vpc.model_dump(), owner_id=user_id)
        vpc_model.subnets = build_blueprint_subnet_models(vpc.subnets, user_id)
        vpc_models.append(vpc_model)

    logger.debug(
        "Build %s blueprint VPC models for user: %s.", len(vpc_models), user_id
    )
    return vpc_models


async def create_blueprint_vpc(
    db: AsyncSession,
    blueprint: BlueprintVPCCreateSchema,
    user_id: int,
    range_id: int | None = None,
) -> BlueprintVPCSchema:
    """Create and add a new VPC blueprint to the database session.

    **Note:** This function only adds VPCs to the database session. It is the responsibility
    of the caller to commit the changes to the database or rollback in the event of
    a failure.

    Args:
    ----
        db (Session): Database connection.
        blueprint (BlueprintVPCCreateSchema): Pydantic model of VPC blueprint data without IDs.
        user_id (int): User who owns the new VPC blueprint.
        range_id (int | None): Optional range ID to link VPC back to.

    Returns:
    -------
        BlueprintVPCSchema: The newly created VPC blueprint data schema with it's ID.

    """
    built_models = build_blueprint_vpc_models([blueprint], user_id)

    # Sanity check that we only have a single VPC model
    if len(built_models) != 1:
        msg = f"Built {len(built_models) } VPC blueprint models from a single schema!"
        logger.error(msg)
        raise RuntimeError(msg)

    vpc_model = built_models[0]

    if range_id:
        vpc_model.range_id = range_id

    db.add(vpc_model)
    logger.debug(
        "Added VPC blueprint model with name: %s to database session.",
        vpc_model.name,
    )

    try:
        await db.flush()
        await db.refresh(vpc_model)
        logger.debug(
            "Successfully flushed VPC blueprint: %s owned by user: %s.",
            vpc_model.id,
            user_id,
        )
    except Exception as e:
        logger.exception(
            "Failed to flush VPC blueprint to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise

    return BlueprintVPCSchema.model_validate(vpc_model)


async def delete_blueprint_vpc(
    db: AsyncSession, vpc_id: int, user_id: int, is_admin: bool = False
) -> BlueprintVPCSchema | None:
    """Delete a standalone VPC blueprint.

    Only allows deletion if the VPC blueprint is standalone (i.e. range_id is None). This
    function only adds delete queries to the database session. It is the responsibility of
    the caller to commit the changes to the database or rollback in the event of a failure.

    Args:
    ----
        db (Sessions): Database connection.
        vpc_id (int): ID of the VPC blueprint.
        user_id (int): ID of user initiating the delete.
        is_admin (bool): Admins can delete other user's blueprints.

    Returns:
    -------
        Optional[BlueprintVPCSchema]: VPC schema data if it exists in database and was successfully deleted.

    """
    vpc = await get_blueprint_vpc(db, vpc_id, user_id, is_admin)
    if not vpc:
        logger.warning(
            "Subnet blueprint: %s not found for deletion as user: %s. Does user have permissions?",
            vpc_id,
            user_id,
        )
        return None

    vpc_model = BlueprintVPCModel(**vpc.model_dump())

    if not vpc_model.is_standalone():
        logger.info(
            "Failed to delete VPC blueprint: %s. Not a standalone blueprint!",
            vpc_model.id,
        )
        return None

    if not is_admin and vpc_model.owner_id != user_id:
        logger.warning(
            "User: %s is not authorized to delete VPC blueprint: %s.",
            user_id,
            vpc_model.id,
        )
        return None

    try:
        await db.delete(vpc_model)
        await db.flush()
        logger.debug(
            "Successfully marked VPC blueprint: %s for deletion.", vpc_model.id
        )
    except Exception as e:
        logger.exception(
            "Failed to mark VPC blueprint: %s for deletion in database session for user: %s, Exception: %s.",
            vpc_model.id,
            user_id,
            e,
        )
        raise

    return BlueprintVPCSchema.model_validate(vpc_model)


# ==================== Deployed (Instances) =====================


def build_deployed_vpc_models(
    vpcs: list[DeployedVPCCreateSchema], user_id: int
) -> list[DeployedVPCModel]:
    """Build a list of deployed VPC ORM models from creation schemas.

    Args:
    ----
        vpcs (list[DeployedVPCCreateSchema]): VPC object data.
        user_id (int): User who created the VPCs.

    Returns:
    -------
        list[DeployedVPCModel]: Corresponding deployed VPC models.

    """
    vpc_models: list[DeployedVPCModel] = []
    for vpc in vpcs:
        vpc_model = DeployedVPCModel(**vpc.model_dump(), owner_id=user_id)
        vpc_model.subnets = build_deployed_subnet_models(vpc.subnets, user_id)
        vpc_models.append(vpc_model)

    logger.debug("Build %s deployed VPC models for user: %s.", len(vpc_models), user_id)
    return vpc_models
