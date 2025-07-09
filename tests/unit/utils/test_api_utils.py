import pytest

from src.app.utils.api_utils import get_api_base_route


def test_get_api_base_route_v1() -> None:
    """Test that get_api_base_route returns the correct version 1 base route."""
    assert get_api_base_route(version=1) == "/api/v1"


def test_get_api_base_route_invalid() -> None:
    """Test that the get_api_base_route raises a ValueError for invalid versions."""
    # Negative
    with pytest.raises(ValueError):
        get_api_base_route(version=-1)

    # High number
    with pytest.raises(ValueError):
        get_api_base_route(version=1000000)

    # Float; Ignore mypy for testing
    with pytest.raises(ValueError):
        get_api_base_route(version=1.2)  # type: ignore
