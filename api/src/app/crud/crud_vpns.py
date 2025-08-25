import logging
from ipaddress import IPv4Address

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..enums.vpns import OpenLabsVPNType
from ..models.range_models import DeployedRangeModel
from ..models.vpn_client_models import VPNClientModel, WireguardClientModel
from ..schemas.vpn_client_schemas import (
    AnyVPNClient,
    AnyVPNClientCreateSchema,
    VPNClientSchema,
    any_vpn_client_adapter,
)
from ..utils.vpn_utils import get_vpn_cidr

logger = logging.getLogger(__name__)


async def get_next_available_vpn_ip(
    db: AsyncSession, range_id: int, vpn_type: OpenLabsVPNType
) -> IPv4Address:
    """Get the next available IPv4 address for a new VPN client for a given range.

    Args:
        db: The SQLAlchemy database session.
        range_id: The ID of the deployed range.
        vpn_type: VPN client type.

    Returns:
        The next available IPv4Address.

    """
    # The first possible client IP address is the second for the CIDR
    # since the first IP address is reserved for the router
    vpn_cidr = get_vpn_cidr(vpn_type)
    first_client_ip = vpn_cidr[2]

    # Query to find the client with the highest IP for this range
    stmt = (
        select(VPNClientModel)
        .where(VPNClientModel.range_id == range_id)
        .order_by(VPNClientModel.assigned_ip.desc())
        .limit(1)
    )

    result = await db.execute(stmt)
    last_client = result.scalar_one_or_none()

    next_ip = first_client_ip if last_client is None else last_client.assigned_ip + 1

    # A simple check to ensure we don't exceed the subnet
    if next_ip not in vpn_cidr.hosts():
        msg = "No available IP addresses left in VPN subnet."
        raise ValueError(msg)

    logger.info(
        "Fetched next available VPN client IP: %s in range: %s",
        next_ip,
        range_id,
    )

    return next_ip


# async def create_wg_vpn_client(
#     db: AsyncSession, new_client: WireguardVPNClientCreateSchema, user_id: int
# ) -> WireguardVPNClientSchema:
#     """Create a new Wireguard VPN client record."""
#     vpn_client_model = WireguardClientModel(**new_client.model_dump(), owner_id=user_id)

#     db.add(vpn_client_model)
#     logger.debug(
#         "Added Wireguard VPN client model: %s (%s) to database session.",
#         vpn_client_model.name,
#         vpn_client_model.id,
#     )

#     await db.flush()
#     await db.refresh(vpn_client_model)
#     logger.debug(
#         "Successfully flushed Wireguard VPN client model: %s (%s) to database session.",
#         vpn_client_model.name,
#         vpn_client_model.id,
#     )

#     return WireguardVPNClientSchema.model_validate(vpn_client_model)

VPN_MODEL_MAP = {OpenLabsVPNType.WIREGUARD: WireguardClientModel}


async def create_vpn_client(
    db: AsyncSession, new_client: AnyVPNClientCreateSchema, user_id: int
) -> AnyVPNClient:
    """Create a new VPN client record.

    Args:
    ----
        db: Database session.
        new_client: Any VPN client creation schema.
        user_id: User associated with client creation request.

    Returns:
    -------
        The inserted VPN client.

    """
    model_class = VPN_MODEL_MAP.get(new_client.type)
    if not model_class:
        msg = f"Failed to create VPN client in database! Unsupported VPN type: {new_client.type}"
        raise ValueError(msg)

    vpn_client_model = model_class(**new_client.model_dump(), owner_id=user_id)

    db.add(vpn_client_model)
    await db.flush()
    await db.refresh(vpn_client_model)

    logger.info(
        "Successfully created %s client: %s for user: %s",
        new_client.type.value.upper(),
        vpn_client_model.name,
        user_id,
    )

    return any_vpn_client_adapter.validate_python(vpn_client_model)


async def get_vpn_clients(
    db: AsyncSession, range_id: int, user_id: int, is_admin: bool = False
) -> list[VPNClientSchema]:
    """Get a list of VPN clients for a specific deployed range.

    Args:
    ----
        db (AsyncSession): Database session.
        range_id (int): ID of the parent deployed range.
        user_id (int): ID of the user requesting data.
        is_admin (bool): Admins can see other user's VPN clients.

    Returns:
    -------
        list[VPNClientSchema]: A list of VPN client schemas.

    """
    parent_range = await db.get(DeployedRangeModel, range_id)

    if not parent_range:
        logger.info(
            "Failed to fetch VPN clients for range_id: %s. Range not found.", range_id
        )
        return []

    if not is_admin and parent_range.owner_id != user_id:
        logger.warning(
            "User: %s is not authorized to access VPN clients for range_id: %s.",
            user_id,
            range_id,
        )
        return []

    stmt = select(VPNClientModel).where(VPNClientModel.range_id == range_id)
    result = await db.execute(stmt)
    client_models = result.scalars().all()

    # The model now maps directly to the schema.
    client_schemas = [VPNClientSchema.model_validate(model) for model in client_models]

    logger.info(
        "Fetched %s VPN clients for range_id: %s for user: %s.",
        len(client_schemas),
        range_id,
        user_id,
    )
    return client_schemas


async def get_vpn_client(
    db: AsyncSession, client_id: int, user_id: int, is_admin: bool = False
) -> AnyVPNClient | None:
    """Get a specific VPN client by its ID.

    Args:
    ----
        db (AsyncSession): Database session.
        client_id (int): ID of the VPN client.
        user_id (int): ID of the user requesting data.
        is_admin (bool): Admins can see any VPN client.

    Returns:
    -------
        Optional[VPNClientSchema]: The VPN client schema if found and authorized, otherwise None.

    """
    client_model = await db.get(VPNClientModel, client_id)

    if not client_model:
        logger.info("Failed to fetch VPN client: %s. Not found in database!", client_id)
        return None

    if is_admin or client_model.owner_id == user_id:
        logger.debug("Fetched VPN client: %s for user %s.", client_id, user_id)
        return any_vpn_client_adapter.validate_python(client_model)

    logger.warning(
        "User: %s is not authorized to fetch VPN client: %s.", user_id, client_id
    )
    return None
