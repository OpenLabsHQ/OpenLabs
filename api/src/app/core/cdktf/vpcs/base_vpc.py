from abc import ABC
from ipaddress import IPv4Network


class CdktfBaseVPC(ABC):
    """Abstract class to enforce common functionality across range cloud providers."""

    id: str
    name: str
    cidr: IPv4Network

    def __init__(self, vpc_id: str, name: str, cidr: IPv4Network) -> None:
        """Initialize a CdktfBaseVPC object.

        Args:
        ----
            vpc_id (str): Unique ID for the VPC given by cloud provider.
            name (str): Name of the VPC.
            cidr (IPv4Network): VPC CIDR configuration.

        Returns:
        -------
            None

        """
        self.id = vpc_id
        self.name = name
        self.cidr = cidr
