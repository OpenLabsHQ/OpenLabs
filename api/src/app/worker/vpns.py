import asyncio
import io
import logging
from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Any

import uvloop
from fabric import Connection
from paramiko import RSAKey

from ..core.db.database import get_db_session_context
from ..crud.crud_ranges import get_deployed_range
from ..crud.crud_users import get_user_by_id
from ..crud.crud_vpns import create_vpn_client, get_next_available_vpn_ip
from ..enums.vpns import OpenLabsVPNType
from ..schemas.user_schema import UserID
from ..schemas.vpn_client_schemas import (
    AnyVPNClientCreateSchema,
    VPNClientCreateRequest,
    VPNClientSchema,
    any_vpn_client_create_adapter,
)
from ..utils.job_utils import track_job_status
from ..utils.vpn_utils import gen_wg_vpn_key_pair

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)


async def _add_wireguard_client(
    conn: Connection,
    client_name: str,
    client_ip: IPv4Address,
) -> dict[str, Any]:
    """Generate a Wireguard VPN config."""
    wg_private_key, wg_public_key = gen_wg_vpn_key_pair()

    # Add peer to running instance (no restart)
    conn.sudo(f"wg set wg0 peer {wg_public_key} allowed-ips {client_ip}/32")

    # Persist peer config for reboots
    peer_config_block = (
        f"\\n# Client: {client_name} - Added: {datetime.now(tz=timezone.utc).isoformat()}\\n"
        "[Peer]\\n"
        f"PublicKey = {wg_public_key}\\n"
        f"AllowedIPs = {client_ip}/32\\n"
    )
    # Use `tee -a` to append with sudo
    conn.run(f"echo -e '{peer_config_block}' | sudo tee -a /etc/wireguard/wg0.conf")

    # These keys come from the WireguardVPNClientCreateSchema
    return {"wg_public_key": wg_public_key, "wg_private_key": wg_private_key}


VPN_SERVER_CONFIGURATORS = {OpenLabsVPNType.WIREGUARD: _add_wireguard_client}


@track_job_status
async def add_vpn_client(
    ctx: dict[str, Any],
    range_id: int,
    client_request_dump: dict[str, Any],
    user_id: int,
) -> dict[str, Any]:
    """Create a VPN client.

    Args:
    ----
        ctx: ARQ worker context. Automatically provided by ARQ.
        range_id: ID of range to add new VPN client to.
        client_request_dump: VPNClientCreateRequest dumped with pydantic's `model_dump(mode='json')`.
        user_id (int): User associated with the VPN client creation request.

    Returns:
        dict[str, Any]: VPNClientSchema dumped with pydantic's `model_dump(mode='json')`.

    """
    client_request = VPNClientCreateRequest.model_validate(client_request_dump)

    handler = VPN_SERVER_CONFIGURATORS.get(client_request.type)

    if not handler:
        msg = f"No VPN generator found for type: {client_request.type.value.upper()}"
        logger.error(msg)
        raise ValueError(msg)

    async with get_db_session_context() as db:
        # Fetch user info
        user = await get_user_by_id(db, UserID(id=user_id))
        if not user:
            msg = f"Unable to generate a VPN config! User: {user_id} not found in database."
            logger.error(msg)
            raise ValueError(msg)

        deployed_range = await get_deployed_range(
            db, range_id, user_id, is_admin=user.is_admin
        )
        if not deployed_range:
            msg = f"Unable to generate a VPN config! Range: {range_id} not found or user: {user_id} does not have access!"
            logger.warning(msg)
            raise ValueError(msg)

        client_ip = await get_next_available_vpn_ip(
            db, deployed_range.id, client_request.type
        )

    # Update jumpbox with SSH
    key_file_obj = io.StringIO(deployed_range.range_private_key)
    pkey = RSAKey.from_private_key(key_file_obj)

    with Connection(
        host=str(deployed_range.jumpbox_public_ip),
        user="ubuntu",
        connect_kwargs={"pkey": pkey},
    ) as conn:
        generated_data = await handler(
            conn=conn,
            client_name=client_request.name,
            client_ip=client_ip,
        )

    new_client: AnyVPNClientCreateSchema = (
        any_vpn_client_create_adapter.validate_python(
            {
                "type": client_request.type,
                "name": client_request.name,
                "assigned_ip": client_ip,
                "range_id": deployed_range.id,
                **generated_data,
            }
        )
    )

    async with get_db_session_context() as db:
        added_client = await create_vpn_client(db, new_client, user_id=user_id)

    # Dump into generic VPN client schema prevent storing VPN secrets
    # in the job data
    cleaned_client = VPNClientSchema.model_validate(added_client)

    logger.info(
        "Successfully created a %s VPN client: '%s' and added it to range: %s for user: %s",
        cleaned_client.type,
        cleaned_client.name,
        range_id,
        user_id,
    )

    return cleaned_client.model_dump(mode="json")
