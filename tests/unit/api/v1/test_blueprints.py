from typing import Never

import pytest
from fastapi import status
from httpx import AsyncClient

from src.app.models.range_models import BlueprintRangeModel

from .config import (
    BASE_ROUTE,
    valid_blueprint_host_create_payload,
    valid_blueprint_range_create_payload,
    valid_blueprint_subnet_create_payload,
    valid_blueprint_vpc_create_payload,
)

pytestmark = pytest.mark.unit


async def test_blueprint_range_delete_non_standalone(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that we get a 404 when trying to delete a non-standalone range blueprint.

    **Note:** When this test was written, ranges could never be non-standalone. Ranges
    were the highest level blueprint and as a result the is_standalone() method was
    hardcoded to always return True for compatibility. This is why the method is mocked.
    """
    # Patch range model method to return False
    monkeypatch.setattr(BlueprintRangeModel, "is_standalone", lambda self: False)

    # Add a blueprint range
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    blueprint_id = int(response.json()["id"])

    # Delete range
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_range_create_database_error(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that when crud function fails to create the range blueprint we return a 500 error."""

    def fake_db_error(*args: dict, **kwargs: dict) -> Never:  # type: ignore
        msg = "Fake database error!"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "src.app.api.v1.blueprints.create_blueprint_range", fake_db_error
    )

    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "failed to save range blueprint" in response.json()["detail"].lower()


async def test_blueprint_range_delete_database_error(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that when crud function fails to delete the range blueprint we return a 500 error."""

    def fake_db_error(*args: dict, **kwargs: dict) -> Never:  # type: ignore
        msg = "Fake database error!"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "src.app.api.v1.blueprints.delete_blueprint_range", fake_db_error
    )

    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/ranges/42")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "failed to delete range blueprint" in response.json()["detail"].lower()


async def test_blueprint_vpc_create_database_error(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that when crud function fails to create the VPC blueprint we return a 500 error."""

    def fake_db_error(*args: dict, **kwargs: dict) -> Never:  # type: ignore
        msg = "Fake database error!"
        raise RuntimeError(msg)

    monkeypatch.setattr("src.app.api.v1.blueprints.create_blueprint_vpc", fake_db_error)

    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "failed to save vpc blueprint" in response.json()["detail"].lower()


async def test_blueprint_vpc_delete_database_error(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that when crud function fails to delete the VPC blueprint we return a 500 error."""

    def fake_db_error(*args: dict, **kwargs: dict) -> Never:  # type: ignore
        msg = "Fake database error!"
        raise RuntimeError(msg)

    monkeypatch.setattr("src.app.api.v1.blueprints.delete_blueprint_vpc", fake_db_error)

    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/vpcs/42")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "failed to delete vpc blueprint" in response.json()["detail"].lower()


async def test_blueprint_subnet_create_database_error(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that when crud function fails to create the subnet blueprint we return a 500 error."""

    def fake_db_error(*args: dict, **kwargs: dict) -> Never:  # type: ignore
        msg = "Fake database error!"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "src.app.api.v1.blueprints.create_blueprint_subnet", fake_db_error
    )

    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=valid_blueprint_subnet_create_payload
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "failed to save subnet blueprint" in response.json()["detail"].lower()


async def test_blueprint_subnet_delete_database_error(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that when crud function fails to delete the subnet blueprint we return a 500 error."""

    def fake_db_error(*args: dict, **kwargs: dict) -> Never:  # type: ignore
        msg = "Fake database error!"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "src.app.api.v1.blueprints.delete_blueprint_subnet", fake_db_error
    )

    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/subnets/42")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "failed to delete subnet blueprint" in response.json()["detail"].lower()


async def test_blueprint_host_create_database_error(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that when crud function fails to create the host blueprint we return a 500 error."""

    def fake_db_error(*args: dict, **kwargs: dict) -> Never:  # type: ignore
        msg = "Fake database error!"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "src.app.api.v1.blueprints.create_blueprint_host", fake_db_error
    )

    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "failed to save host blueprint" in response.json()["detail"].lower()


async def test_blueprint_host_delete_database_error(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that when crud function fails to delete the host blueprint we return a 500 error."""

    def fake_db_error(*args: dict, **kwargs: dict) -> Never:  # type: ignore
        msg = "Fake database error!"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "src.app.api.v1.blueprints.delete_blueprint_host", fake_db_error
    )

    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/hosts/42")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "failed to delete host blueprint" in response.json()["detail"].lower()
