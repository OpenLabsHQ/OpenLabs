import io
import logging
import subprocess
from ipaddress import IPv4Network
from typing import Callable

from fabric import Connection
from paramiko import RSAKey

from ..core.config import settings
from ..enums.vpns import OpenLabsVPNType
from ..schemas.range_schemas import DeployedRangeSchema
from ..schemas.vpn_client_schemas import AnyVPNClient, WireguardVPNClientSchema

logger = logging.getLogger(__name__)


def get_vpn_cidr(vpn_type: OpenLabsVPNType) -> IPv4Network:
    """Get the VPNs reserved CIDR."""
    if vpn_type == OpenLabsVPNType.WIREGUARD:
        vpn_cidr = settings.VPN_WIREGUARD_CIDR
    else:
        vpn_cidr = None

    if not vpn_cidr:
        msg = f"VPN type: {vpn_type.value.upper()} does not have a configured reserved CIDR!"
        logger.info(msg)
        raise ValueError(msg)

    return vpn_cidr


def get_range_wg_vpn_public_key(
    host: str,
    user: str,
    private_key_string: str,
) -> str:
    """Connect to an OpenLabs jumpbox and get the Wireguard VPN server public key.

    Args:
        host: The IP address or hostname of the jumpbox.
        user: The SSH username (e.g., 'ubuntu').
        private_key_string: The SSH private key as a string.

    Returns:
        The WireGuard public key as a string.

    """
    # Configure private key
    key_file_obj = io.StringIO(private_key_string)
    pkey = RSAKey.from_private_key(key_file_obj)
    connect_kwargs = {"pkey": pkey}

    with Connection(host=host, user=user, connect_kwargs=connect_kwargs) as c:
        # File should be world readable 0644
        result = c.run("cat /etc/wireguard/public.key", hide=True)
        return result.stdout.strip()


def gen_wg_vpn_key_pair() -> tuple[str, str]:
    """Generate a new Wireguard private and public key pair.

    Returns
    -------
        tuple[str, str]: Private, Public key of new Wireguard key pair.

    """
    genkey_process = subprocess.run(
        ["wg", "genkey"],  # noqa: S607
        capture_output=True,
        text=True,  # Decode output as utf-8 automatically
        check=True,
    )
    private_key = genkey_process.stdout.strip()

    pubkey_process = subprocess.run(
        ["wg", "pubkey"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
        input=private_key,  # Pass the private key to stdin
    )
    public_key = pubkey_process.stdout.strip()

    return private_key, public_key


def _gen_wg_vpn_client_conf(
    vpn_client: WireguardVPNClientSchema, deployed_range: DeployedRangeSchema
) -> str:
    """Generate the content for the client's .conf file."""
    return f"""
[Interface]
PrivateKey = {vpn_client.wg_private_key}
Address = {vpn_client.assigned_ip}/32
DNS = {", ".join(str(dns) for dns in settings.VPN_DNS_SERVERS)}

[Peer]
PublicKey = {deployed_range.wg_vpn_public_key}
Endpoint = {deployed_range.jumpbox_resource_id}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
""".strip()


VPN_CONFIG_GENERATORS: dict[OpenLabsVPNType, Callable[..., str]] = {
    OpenLabsVPNType.WIREGUARD: _gen_wg_vpn_client_conf
}


def generate_vpn_client_config(
    vpn_client: AnyVPNClient,
    deployed_range: DeployedRangeSchema,
) -> str:
    """Generate a client VPN configuration for the specified VPN type."""
    handler = VPN_CONFIG_GENERATORS.get(vpn_client.type)

    if not handler:
        msg = f"No VPN config generator found for type: {vpn_client.type.value.upper()}"
        logger.error(msg)
        raise ValueError(msg)

    return handler(vpn_client=vpn_client, deployed_range=deployed_range)
