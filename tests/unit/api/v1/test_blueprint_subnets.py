from typing import Never

import pytest
from fastapi import status
from httpx import AsyncClient

from .config import (
    BASE_ROUTE,
    valid_blueprint_subnet_create_payload,
)


async def test_blueprint_subnet_create_database_error(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that when crud function fails to create the subnet blueprint we return a 500 error."""

    def fake_db_error(*args: dict, **kwargs: dict) -> Never:  # type: ignore
        msg = "Fake database error!"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "src.app.api.v1.blueprint_subnets.create_blueprint_subnet", fake_db_error
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
        "src.app.api.v1.blueprint_subnets.delete_blueprint_subnet", fake_db_error
    )

    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/subnets/42")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "failed to delete subnet blueprint" in response.json()["detail"].lower()
