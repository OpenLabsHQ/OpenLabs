from abc import ABC


class CdktfBaseSubnet(ABC):
    """Abstract class to enforce common functionality across cloud providers."""

    id: str

    def __init__(self, subnet_id: str) -> None:
        """Initialize a CdktfBaseSubnet object.

        Args:
        ----
            subnet_id (str): Unique ID for the subnet given by cloud provider.

        Returns:
        -------
            None

        """
        self.id = subnet_id
