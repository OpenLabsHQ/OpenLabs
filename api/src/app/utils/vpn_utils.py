import io
import subprocess
from ipaddress import IPv4Address

from fabric import Connection
from paramiko import RSAKey


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


def gen_wg_vpn_key_pair():
    """Generates a new WireGuard private and public key pair."""
    private_key = (
        subprocess.check_output("wg genkey", shell=True).decode("utf-8").strip()
    )
    public_key = (
        subprocess.check_output(f"echo '{private_key}' | wg pubkey", shell=True)
        .decode("utf-8")
        .strip()
    )
    return private_key, public_key


def gen_wg_vpn_client_conf(
    client_private_key: str,
    client_ip: IPv4Address,
    server_public_key: str,
    server_endpoint: str,
) -> str:
    """Generate the content for the client's .conf file."""
    return f"""
[Interface]
PrivateKey = {client_private_key}
Address = {client_ip}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_endpoint}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
""".strip()
