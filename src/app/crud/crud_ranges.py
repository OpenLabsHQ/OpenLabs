import logging
import uuid

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from ..models.range_model import RangeModel
from ..models.subnet_model import SubnetModel
from ..models.vpc_model import VPCModel
from ..schemas.range_schema import RangeID, RangeSchema
from .crud_vpcs import create_vpc

# Configure logging
logger = logging.getLogger(__name__)


async def get_range_headers(
    db: AsyncSession, range_id: RangeID, user_id: uuid.UUID | None = None
) -> list[RangeModel]:
    """Get list of range headers.

    Args:
    ----
        db (Session): Database connection.
        range_id (RangeID): ID of the deployed range.
        user_id (Optional[uuid.UUID]): If provided, only return templates owned by this user.

    Returns:
    -------
        Optional[RangeModel]: Range if it exists in database.

    """
    mapped_range_model = inspect(RangeModel)
    main_columns = [
        getattr(RangeModel, attr.key) for attr in mapped_range_model.column_attrs
    ]

    stmt = (
        select(RangeModel)
        .where(RangeModel.id == range_id.id)
        .options(load_only(*main_columns))
    )

    if user_id:
        stmt = stmt.filter(RangeModel.owner_id == user_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_range(
    db: AsyncSession, range_id: RangeID, user_id: uuid.UUID | None = None
) -> RangeModel | None:
    """Get range by id (uuid).

    Args:
    ----
        db (Session): Database connection.
        range_id (RangeID): ID of the range.
        user_id (Optional[uuid.UUID]): If provided, only return ranges owned by this user.

    Returns:
    -------
        Optional[RangeModel]: Range if it exists in database.

    """
    # Eagerly fetch relationships to make single query
    stmt = (
        select(RangeModel)
        .options(
            selectinload(RangeModel.vpcs)
            .selectinload(VPCModel.subnets)
            .selectinload(SubnetModel.hosts)
        )
        .filter(RangeModel.id == range_id.id)
    )

    if user_id:
        stmt = stmt.filter(RangeModel.owner_id == user_id)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_range(
    db: AsyncSession, range_schema: RangeSchema, owner_id: uuid.UUID
) -> RangeModel:
    """Create and add a new range template to the database.

    Args:
    ----
        db (Session): Database connection.
        range_schema (RangeSchema): Range schema pydantic class.
        owner_id (uuid.UUID): The ID of the user who owns this template.

    Returns:
    -------
        OpenLabsRange: The newly created range template.

    """
    range_dict = range_schema.model_dump(exclude={"vpcs"})

    range_dict["owner_id"] = owner_id

    # Create the Range object (No commit yet)
    range_obj = RangeModel(**range_dict)
    db.add(range_obj)  # Stage the range

    # Build range ID
    range_id = RangeID(id=range_obj.id)

    # Create VPCs and associate them with the range (No commit yet)
    vpc_objects = [
        await create_vpc(db, vpc_data, owner_id, range_id)
        for vpc_data in range_schema.vpcs
    ]
    db.add_all(vpc_objects)  # Stage VPCs

    # Commit everything in one transaction
    await db.commit()

    return range_obj


async def delete_range(db: AsyncSession, range_model: RangeModel) -> bool:
    """Delete a range entry.

    Args:
    ----
        db (AsyncSession): Database session.
        range_model (RangeModel): Range to delete.

    Returns:
    -------
        bool: True if successuflly delete. False otherwise.

    """
    try:
        await db.delete(range_model)
        await db.commit()
        return True
    except Exception as e:
        logger.error("Failed to delete range. Error: %s", e)
        return False


async def is_range_owner(
    db: AsyncSession, range_id: RangeID, user_id: uuid.UUID
) -> bool:
    """Check if a user is the owner of a range template.

    Args:
    ----
        db (Session): Database connection.
        range_id (RangeID): ID of the range.
        user_id (uuid.UUID): ID of the user.

    Returns:
    -------
        bool: True if the user is the owner, False otherwise.

    """
    stmt = (
        select(RangeModel)
        .filter(RangeModel.id == range_id.id)
        .filter(RangeModel.owner_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
