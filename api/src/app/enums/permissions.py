from enum import Enum


class BlueprintPermissionType(str, Enum):
    """Permission types for blueprint ranges.

    READ: Allows user to view the blueprint range configuration and details.
          Users can see the blueprint in lists and access its properties.

    WRITE: Allows user to modify the blueprint range configuration and deploy it.
           Users can edit the blueprint, update its settings, and create deployed
           ranges from it. Write permission includes read permission.
    """

    READ = "read"
    WRITE = "write"

    @classmethod
    def values(cls) -> str:
        """Return formatted tuple string of all permission values."""
        return f"({', '.join(repr(t.value) for t in cls)})"


class DeployedRangePermissionType(str, Enum):
    """Permission types for deployed ranges.

    READ: Allows user to view the deployed range status and configuration.
          Users can see the range in lists, check its state, and view properties
          but cannot interact with or modify it.

    WRITE: Allows user to modify deployed range settings and manage its lifecycle.
           Users can start/stop the range, update configurations, and delete the
           deployed range. Write permission includes read permission.

    EXECUTE: Allows user to interact with the live deployed range infrastructure.
             Users can access SSH keys, connect to VMs, and interact with the
             running environment. Execute permission includes read permission but
             not write permission.
    """

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"

    @classmethod
    def values(cls) -> str:
        """Return formatted tuple string of all permission values."""
        return f"({', '.join(repr(t.value) for t in cls)})"
