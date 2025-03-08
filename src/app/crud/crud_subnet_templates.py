import logging
import uuid

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import load_only, selectinload

from ..models.template_subnet_model import TemplateSubnetModel
from ..schemas.template_subnet_schema import (
    TemplateSubnetBaseSchema,
    TemplateSubnetID,
    TemplateSubnetSchema,
)
from ..schemas.template_vpc_schema import TemplateVPCID
from .crud_host_templates import create_host_template

logger = logging.getLogger(__name__)


async def get_subnet_template_headers(
    db: AsyncSession, standalone_only: bool = True, user_id: uuid.UUID | None = None
) -> list[TemplateSubnetModel]:
    """Get list of subnet template headers.

    Args:
    ----
        db (Session): Database connection.
        standalone_only (bool): Include only subnets that are standalone templates
            (i.e. those with a null vpc_id). Defaults to True.
        user_id (Optional[uuid.UUID]): If provided, only return templates owned by this user.

    Returns:
    -------
        list[TemplateSubnetModel]: List of subnet template models.

    """
    # Dynamically select non-nested columns/attributes
    mapped_subnet_model = inspect(TemplateSubnetModel)
    main_columns = [
        getattr(TemplateSubnetModel, attr.key)
        for attr in mapped_subnet_model.column_attrs
    ]

    # Start building the query
    stmt = select(TemplateSubnetModel)

    if standalone_only:
        stmt = stmt.where(TemplateSubnetModel.vpc_id.is_(None))

    if user_id:
        stmt = stmt.filter(TemplateSubnetModel.owner_id == user_id)

    stmt = stmt.options(load_only(*main_columns))

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_subnet_template(
    db: AsyncSession, subnet_id: TemplateSubnetID, user_id: uuid.UUID | None = None
) -> TemplateSubnetModel | None:
    """Get subnet template by id (uuid).

    Args:
    ----
        db (Session): Database connection.
        subnet_id (TemplateSubnetID): UUID of the subnet.
        user_id (Optional[uuid.UUID]): If provided, only return templates owned by this user.

    Returns:
    -------
        Optional[TemplateSubnetModel]: TemplateSubnetModel if it exists in database.

    """
    stmt = (
        select(TemplateSubnetModel)
        .options(selectinload(TemplateSubnetModel.hosts))
        .filter(TemplateSubnetModel.id == subnet_id.id)
    )

    if user_id:
        stmt = stmt.filter(TemplateSubnetModel.owner_id == user_id)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_subnet_template(
    db: AsyncSession,
    template_subnet: TemplateSubnetBaseSchema,
    vpc_id: TemplateVPCID | None = None,
    owner_id: uuid.UUID | None = None,
) -> TemplateSubnetModel:
    """Create and add a new subnet template to the database.

    Args:
    ----
        db (Session): Database connection.
        template_subnet (TemplateSubnetBaseSchema): Dictionary containing OpenLabsSubnet data.
        vpc_id (Optional[TemplateVPCID]): VPC ID to link subnet back too.
        owner_id (Optional[uuid.UUID]): ID of the user who owns this template.

    Returns:
    -------
        TemplateSubnetModel: The newly created subnet template.

    """
    template_subnet = TemplateSubnetSchema(**template_subnet.model_dump())
    subnet_dict = template_subnet.model_dump(exclude={"hosts"})
    if vpc_id:
        subnet_dict["vpc_id"] = vpc_id.id

    if owner_id:
        subnet_dict["owner_id"] = owner_id

    subnet_obj = TemplateSubnetModel(**subnet_dict)
    db.add(subnet_obj)

    # Add hosts
    host_objects = [
        await create_host_template(
            db,
            host_data,
            TemplateSubnetID(id=subnet_obj.id),
            owner_id=owner_id,  # Pass owner_id to hosts
        )
        for host_data in template_subnet.hosts
    ]

    # Commit if we are parent object
    if vpc_id:
        db.add_all(host_objects)
    else:
        await db.commit()
        await db.refresh(subnet_obj)

    return subnet_obj


async def delete_subnet_template(
    db: AsyncSession, subnet_model: TemplateSubnetModel
) -> bool:
    """Delete a standalone subnet template.

    Only allows deletion if the subnet template is standalone (i.e. vpc_id is None).

    Args:
    ----
        db (Sessions): Database connection.
        subnet_model (TemplateSubnetModel): Subnet template model object.

    Returns:
    -------
        bool: True if successfully delete. False otherwise.

    """
    if not subnet_model.is_standalone():
        log_msg = (
            "Cannot delete subnet template because it is not a standalone template."
        )
        logger.error(log_msg)
        return False

    await db.delete(subnet_model)
    await db.commit()
    return True
