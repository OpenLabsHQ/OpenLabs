from typing import Any
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession


class DummyDB(AsyncMock):
    """Dummy database class for testing."""

    def __init__(self, *args: Any, **kwargs: dict[str, Any]) -> None:  # noqa: ANN401
        """Initialize dummy db."""
        super().__init__(*args, spec=AsyncSession, **kwargs)


class DummyBlueprintHost(Mock):
    """Dummy blueprint host model for testing."""

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True


class DummyBlueprintSubnet(Mock):
    """Dummy blueprint subnet model for testing."""

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True


class DummyBlueprintVPC(Mock):
    """Dummy blueprint VPC model for testing."""

    def is_standalone(self) -> bool:
        """Return dummy standalone state."""
        return True


class DummyBlueprintRange(Mock):
    """Dummy blueprint range model for testing."""

    pass


class DummyDeployedRange(Mock):
    """Dummy deployed range model for testing."""

    pass
