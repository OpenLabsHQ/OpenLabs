import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.vpc_model import VPCModel
from ..schemas.range_schema import RangeID
from ..schemas.vpc_schema import VPCID, VPCBaseSchema, VPCSchema
from .crud_subnets import create_subnet


async def create_vpc(
    db: AsyncSession,
    vpc_base_schema: VPCBaseSchema,
    owner_id: uuid.UUID | None,
    range_id: RangeID,
) -> VPCModel:
    """Create and add a new VPC to the database.

    Args:
    ----
        db (Session): Database connection.
        vpc_base_schema (VPCBaseSchema): VPC base schema data.
        owner_id (uuid.UUID | None): The ID of the user who owns this template.
        range_id (Optional[str]): Range ID to link VPC back too.

    Returns:
    -------
        VPCModel: The newly created VPC.

    """
    vpc_schema = VPCSchema(**vpc_base_schema.model_dump())
    vpc_dict = vpc_schema.model_dump(exclude={"subnets"})

    # Set owner ID and range ID if provided
    if owner_id:
        vpc_dict["owner_id"] = owner_id

    vpc_dict["range_id"] = range_id.id

    vpc_obj = VPCModel(**vpc_dict)
    db.add(vpc_obj)

    # Add subnets
    subnet_objects = [
        await create_subnet(db, subnet_data, VPCID(id=vpc_obj.id), owner_id)
        for subnet_data in vpc_base_schema.subnets
    ]

    db.add_all(subnet_objects)
    return vpc_obj
