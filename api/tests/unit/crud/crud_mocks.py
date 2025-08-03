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

    def __init__(self, *args: Any, **kwargs: dict[str, Any]) -> None:  # noqa: ANN401
        """Initialize dummy blueprint range."""
        super().__init__(*args, **kwargs)
        self.permissions: list[Any] = []
        self.owner_id = 1


class DummyDeployedRange(Mock):
    """Dummy deployed range model for testing."""

    def __init__(self, *args: Any, **kwargs: dict[str, Any]) -> None:  # noqa: ANN401
        """Initialize dummy deployed range."""
        super().__init__(*args, **kwargs)
        self.permissions: list[Any] = []
        self.owner_id = 1


class DummyJob(Mock):
    """Dummy job model for testing."""

    pass
