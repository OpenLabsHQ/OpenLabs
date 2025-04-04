import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.host_model import HostModel
from src.app.schemas.host_schema import HostBaseSchema, HostSchema
from src.app.schemas.subnet_schema import SubnetID


async def create_host(
    db: AsyncSession,
    host_base_schema: HostBaseSchema,
    subnet_id: SubnetID,
    owner_id: uuid.UUID | None,
) -> HostModel:
    """Add a new host to the database.

    Args:
    ----
        db (Session): Database connection.
        host_base_schema (HostBaseSchema): Pydantic model containing host data.
        subnet_id (SubnetID): Subnet ID to link host back to.
        owner_id (Optional[uuid.UUID]): ID of the user who owns this host.

    Returns:
    -------
        HostModel: The newly created host.

    """
    host_schema = HostSchema(**host_base_schema.model_dump())
    host_dict = host_schema.model_dump()

    host_dict["subnet_id"] = subnet_id.id

    if owner_id:
        host_dict["owner_id"] = owner_id

    host_obj = HostModel(**host_dict)
    db.add(host_obj)

    return host_obj
