import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.subnet_model import SubnetModel
from ..schemas.subnet_schema import SubnetBaseSchema, SubnetID, SubnetSchema
from ..schemas.vpc_schema import VPCID
from .crud_hosts import create_host


async def create_subnet(
    db: AsyncSession,
    subnet_base_schema: SubnetBaseSchema,
    vpc_id: VPCID,
    owner_id: uuid.UUID | None,
) -> SubnetModel:
    """Add a new subnet to the database.

    Args:
    ----
        db (Session): Database connection.
        subnet_base_schema (SubnetBaseSchema): Pydantic model with subnet data..
        vpc_id (VPCID): VPC ID to link subnet back too.
        owner_id (Optional[uuid.UUID]): ID of the user who owns this subnet.

    Returns:
    -------
        SubnetModel: The newly created subnet.

    """
    subnet_schema = SubnetSchema(**subnet_base_schema.model_dump())
    subnet_dict = subnet_schema.model_dump(exclude={"hosts"})

    subnet_dict["vpc_id"] = vpc_id.id

    if owner_id:
        subnet_dict["owner_id"] = owner_id

    subnet_obj = SubnetModel(**subnet_dict)
    db.add(subnet_obj)

    # Add hosts
    host_objects = [
        await create_host(
            db,
            host_data,
            SubnetID(id=subnet_obj.id),
            owner_id=owner_id,  # Pass owner_id to hosts
        )
        for host_data in subnet_schema.hosts
    ]

    db.add_all(host_objects)
    return subnet_obj
