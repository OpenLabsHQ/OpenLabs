from enum import Enum


class BlueprintPermissionType(str, Enum):
    """Permission types for blueprint ranges."""

    READ = "read"
    WRITE = "write"

    @classmethod
    def values(cls) -> str:
        """Return formatted tuple string of all permission values."""
        return f"({', '.join(repr(t.value) for t in cls)})"


class DeployedRangePermissionType(str, Enum):
    """Permission types for deployed ranges."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"

    @classmethod
    def values(cls) -> str:
        """Return formatted tuple string of all permission values."""
        return f"({', '.join(repr(t.value) for t in cls)})"