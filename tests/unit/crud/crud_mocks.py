# Dummy DB session for testing
from unittest.mock import AsyncMock


class DummyDB:
    """Dummy database class for testing."""

    def __init__(self) -> None:
        """Initialize dummy db."""
        self.get = AsyncMock()
        self.delete = AsyncMock()
        self.commit = AsyncMock()
        self.execute = AsyncMock()
        self.flush = AsyncMock()


class DummyBlueprintHost:
    """Dummy blueprint host model for testing."""

    def __init__(self) -> None:
        """Initialize dummy host."""
        self.id = 1

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True


class DummyBlueprintSubnet:
    """Dummy blueprint subnet model for testing."""

    def __init__(self) -> None:
        """Initialize dummy subnet."""
        self.id = 1

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True


class DummyBlueprintVPC:
    """Dummy blueprint VPC model for testing."""

    def __init__(self) -> None:
        """Initialize dummy VPC."""
        self.id = 1

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True


class DummyBlueprintRange:
    """Dummy blueprint range model for testing."""

    def __init__(self) -> None:
        """Initialize dummy range."""
        self.id = 1

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True


class DummyDeployedRange:
    """Dummy deployed range model for testing."""

    def __init__(self) -> None:
        """Initialize dummy deployed range."""
        self.id = 1
        self.owner_id = 1

    pass
