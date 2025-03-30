from abc import ABC, abstractmethod


class CdktfBaseHost(ABC):
    """Abstract class to enforce common functionality across range cloud providers."""

    id: str

    def __init__(
        self,
        host_id: str,
    ) -> None:
        """Initialize a CdktfBaseHost object.

        Args:
        ----
            host_id (str): Unique ID for host given by cloud provider.

        Returns:
        -------
            None

        """
        self.id = host_id

    @abstractmethod
    def stop(self) -> bool:
        """Abstract method to stop the deploye host.

        Returns
        -------
            bool: True if stopped successfully. False otherwise.

        """
        pass

    @abstractmethod
    def start(self) -> bool:
        """Abstract method to start the deployed host.

        Returns
        -------
            bool: True if started successfully. False otherwise.

        """
        pass

    @abstractmethod
    def restart(self) -> bool:
        """Abstract method to restart the deployed host.

        Returns
        -------
            bool: True if restarted successfully. False otherwise.

        """
        pass
