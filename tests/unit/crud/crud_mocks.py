# Dummy DB session for testing
from unittest.mock import AsyncMock


class DummyDB:
    """Dummy database class for testing."""

    def __init__(self) -> None:
        """Initialize dummy db."""
        self.delete = AsyncMock()
        self.commit = AsyncMock()


class DummyTemplateHost:
    """Dummy host template model for testing."""

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True


class DummyTemplateSubnet:
    """Dummy template subnet model for testing."""

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True


class DummyTemplateVPC:
    """Dummy template VPC model for testing."""

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True


class DummyTemplateRange:
    """Dummy template range model for testing."""

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True
