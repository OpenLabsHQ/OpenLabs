import re
from ipaddress import IPv4Address, IPv4Network, IPv6Address
from typing import Annotated, Union

from pydantic import AfterValidator

from ..enums.operating_systems import OS_SIZE_THRESHOLD, OpenLabsOS


def is_valid_hostname(hostname: str) -> bool:
    """Check if string is a valid hostname based on RFC 1035.

    Args:
    ----
        hostname (str): String to check.

    Returns:
    -------
        bool: True if valid hostname. False otherwise.

    """
    max_hostname_length = 253

    if not hostname:
        return False

    if hostname[-1] == ".":
        # strip exactly one dot from the right, if present
        hostname = hostname[:-1]
    if len(hostname) > max_hostname_length:
        return False

    labels = hostname.split(".")

    # the TLD must be not all-numeric
    if re.match(r"[0-9]+$", labels[-1]):
        return False

    allowed = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(label) for label in labels)


def pydantic_hostname_validator(value: str) -> str:
    """Pydantic validator that calls is_valid_hostname."""
    if not is_valid_hostname(value):
        msg = f"'{value}' is not a valid hostname."
        raise ValueError(msg)
    return value


# Pydantic validation types
Hostname = Annotated[str, AfterValidator(pydantic_hostname_validator)]
DNSEntry = Union[IPv4Address, IPv6Address, Hostname]


def max_num_hosts_in_subnet(subnet: IPv4Network) -> int:
    """Get the max number of usable hosts in a subnet.

    Args:
    ----
        subnet (IPv4Network): IPv4 subnet network.

    Returns:
    -------
        int: Max number of usable hosts.

    """
    total_addresses = subnet.num_addresses

    # Minimum subnet mask https://aws.amazon.com/vpc/faqs/
    multi_host_subnet_prefix_max = 28

    # If we can fit more than one host on the subnet
    # then subtract reserved addresses
    if subnet.prefixlen > multi_host_subnet_prefix_max:
        return 0

    return total_addresses - 5


def is_valid_disk_size(os: OpenLabsOS, size: int) -> bool:
    """Check if size for given OS is possible.

    Args:
    ----
        os (OpenLabsOS): Operating system of host to check.
        size (int): Size of disk requested.

    Returns:
    -------
        bool: True if possible host size. False otherwise

    """
    return size >= OS_SIZE_THRESHOLD[os]


def mutually_exclusive_networks_v4(networks: list[IPv4Network]) -> bool:
    """Check if a list of IPv4 networks are mutually exclusive.

    Args:
    ----
        networks (list[IPv4Networks]): List of IPv4 networks.

    Returns:
    -------
        bool: True if the list of networks are mutually exclusive. False otherwise.

    """
    for i, net1 in enumerate(networks):
        for j, net2 in enumerate(networks):
            if i != j and net1.overlaps(net2):
                return False

    return True


def all_subnets_contained(
    parent_network: IPv4Network, child_networks: list[IPv4Network]
) -> bool:
    """Check if all child IPv4 networks are fully contained within the parent IPv4 network.

    Args:
        parent_network: The IPv4Network that is expected to contain all child networks.
        child_networks: A list of IPv4Network objects to check for containment.

    Returns:
        True if all child networks are subnets of the parent network; False otherwise.

    """
    return all(child.subnet_of(parent_network) for child in child_networks)
