from typing import Never

import pytest
from fastapi import status
from httpx import AsyncClient

from tests.common.api.v1.config import (
    BASE_ROUTE,
    valid_blueprint_vpc_create_payload,
)


async def test_blueprint_vpc_create_database_error(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that when crud function fails to create the VPC blueprint we return a 500 error."""

    def fake_db_error(*args: dict, **kwargs: dict) -> Never:  # type: ignore
        msg = "Fake database error!"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "src.app.api.v1.blueprint_vpcs.create_blueprint_vpc", fake_db_error
    )

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

    monkeypatch.setattr(
        "src.app.api.v1.blueprint_vpcs.delete_blueprint_vpc", fake_db_error
    )

    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/vpcs/42")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "failed to delete vpc blueprint" in response.json()["detail"].lower()
