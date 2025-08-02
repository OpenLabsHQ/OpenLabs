import asyncio
import io
import logging
from datetime import datetime, timezone
from typing import Any

import uvloop
from fabric import Connection
from paramiko import RSAKey

from ..core.db.database import get_db_session_context
from ..crud.crud_ranges import get_deployed_range
from ..crud.crud_users import get_user_by_id
from ..crud.crud_vpns import create_vpn_client, get_next_available_wg_vpn_ip
from ..schemas.user_schema import UserID
from ..schemas.vpn_schemas import VPNClientCreateSchema
from ..utils.job_utils import track_job_status
from ..utils.vpn_utils import gen_wg_vpn_client_conf, gen_wg_vpn_key_pair

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)


@track_job_status
async def generate_wireguard_vpn_client(
    ctx: dict[str, Any], range_id: int, client_name: str, user_id: int
) -> dict[str, Any]:
    """Generate a Wireguard VPN config."""

    async with get_db_session_context() as db:
        # Fetch user info
        user = await get_user_by_id(db, UserID(id=user_id))
        if not user:
            msg = f"Unable to generate a Wireguard VPN config! User: {user_id} not found in database."
            logger.error(msg)
            raise ValueError(msg)

        deployed_range = await get_deployed_range(
            db, range_id, user_id, is_admin=user.is_admin
        )
        if not deployed_range:
            msg = f"Unable to generate a Wireguard VPN config! Range: {range_id} not found or user: {user_id} does not have access!"
            logger.warning(msg)
            raise ValueError(msg)

        client_ip = await get_next_available_wg_vpn_ip(db, deployed_range.id)

    client_private_key, client_public_key = gen_wg_vpn_key_pair()

    # Update jumpbox with SSH
    key_file_obj = io.StringIO(deployed_range.range_private_key)
    pkey = RSAKey.from_private_key(key_file_obj)

    with Connection(
        host=str(deployed_range.jumpbox_public_ip),
        user="ubuntu",
        connect_kwargs={"pkey": pkey},
    ) as c:
        # Add peer to running instance (no restart)
        c.sudo(f"wg set wg0 peer {client_public_key} allowed-ips {client_ip}/32")

        # Persist peer config for reboots
        peer_config_block = (
            f"\\n# Client: {client_name} - Added: {datetime.now(tz=timezone.utc).isoformat()}\\n"
            "[Peer]\\n"
            f"PublicKey = {client_public_key}\\n"
            f"AllowedIPs = {client_ip}/32\\n"
        )
        # Use `tee -a` to append with sudo
        c.run(f"echo -e '{peer_config_block}' | sudo tee -a /etc/wireguard/wg0.conf")

    # Step 5: Generate Client .conf File
    config_content = gen_wg_vpn_client_conf(
        client_private_key=client_private_key,
        client_ip=client_ip,
        server_public_key=deployed_range.wg_vpn_public_key,
        server_endpoint=str(deployed_range.jumpbox_public_ip),
    )

    async with get_db_session_context() as db:
        new_client = VPNClientCreateSchema(
            name=client_name,
            wg_public_key=client_public_key,
            wg_assigned_ip=client_ip,
            wg_config_file=config_content,
            range_id=range_id,
        )
        vpn_client = await create_vpn_client(db, new_client, user_id)

    return vpn_client.model_dump(mode="json")
