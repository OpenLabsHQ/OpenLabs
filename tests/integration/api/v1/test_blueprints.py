from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from src.app.core.config import settings
from tests.conftest import login_user, register_user, remove_key_recursively
from tests.unit.api.v1.config import (
    BASE_ROUTE,
    valid_blueprint_host_create_payload,
    valid_blueprint_range_create_payload,
    valid_blueprint_subnet_create_payload,
    valid_blueprint_vpc_create_payload,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio(loop_scope="session")
async def test_user_add_remove_range_blueprint_flow(
    auth_integration_client: AsyncClient,
) -> None:
    """Test the user flow of submitting a range blueprint, listing it out, then deleting it."""
    response = await auth_integration_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    blueprint_id: int = response.json()["id"]

    # Attempt to fetch the range
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Validate response
    recieved_range: dict[str, Any] = response.json()
    remove_key_recursively(
        recieved_range, "id"
    )  # Our creation payload doesn't have IDs
    assert recieved_range == valid_blueprint_range_create_payload

    # Attempt to list out all of user's blueprints
    response = await auth_integration_client.get(f"{BASE_ROUTE}/blueprints/ranges")
    assert response.status_code == status.HTTP_200_OK
    assert any(
        blueprint_range["id"] == blueprint_id for blueprint_range in response.json()
    )

    # Delete the range blueprint
    response = await auth_integration_client.delete(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check that the blueprint is gone
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_user_add_remove_vpc_blueprint_flow(
    auth_integration_client: AsyncClient,
) -> None:
    """Test the user flow of submitting a VPC blueprint, listing it out, then deleting it."""
    response = await auth_integration_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    blueprint_id: int = response.json()["id"]

    # Attempt to fetch the VPC
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    recieved_vpc: dict[str, Any] = response.json()
    remove_key_recursively(recieved_vpc, "id")  # Our creation payload doesn't have IDs
    assert recieved_vpc == valid_blueprint_vpc_create_payload

    # Attempt to list out all of user's blueprints
    response = await auth_integration_client.get(f"{BASE_ROUTE}/blueprints/vpcs")
    assert response.status_code == status.HTTP_200_OK
    assert any(blueprint_vpc["id"] == blueprint_id for blueprint_vpc in response.json())

    # Delete the VPC blueprint
    response = await auth_integration_client.delete(
        f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check that the blueprint is gone
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_user_add_remove_subnet_blueprint_flow(
    auth_integration_client: AsyncClient,
) -> None:
    """Test the user flow of submitting a subnet blueprint, listing it out, then deleting it."""
    response = await auth_integration_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=valid_blueprint_subnet_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    blueprint_id: int = response.json()["id"]

    # Attempt to fetch the subnet
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    recieved_subnet: dict[str, Any] = response.json()
    remove_key_recursively(
        recieved_subnet, "id"
    )  # Our creation payload doesn't have IDs
    assert recieved_subnet == valid_blueprint_subnet_create_payload

    # Attempt to list out all of user's blueprints
    response = await auth_integration_client.get(f"{BASE_ROUTE}/blueprints/subnets")
    assert response.status_code == status.HTTP_200_OK
    assert any(
        blueprint_subnet["id"] == blueprint_id for blueprint_subnet in response.json()
    )

    # Delete the subnet blueprint
    response = await auth_integration_client.delete(
        f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check that the blueprint is gone
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_user_add_remove_host_blueprint_flow(
    auth_integration_client: AsyncClient,
) -> None:
    """Test the user flow of submitting a host blueprint, listing it out, then deleting it."""
    response = await auth_integration_client.post(
        f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    blueprint_id: int = response.json()["id"]

    # Attempt to fetch the host blueprint
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    recieved_host: dict[str, Any] = response.json()
    remove_key_recursively(recieved_host, "id")  # Our creation payload doesn't have IDs
    assert recieved_host == valid_blueprint_host_create_payload

    # Attempt to list out all of user's blueprints
    response = await auth_integration_client.get(f"{BASE_ROUTE}/blueprints/hosts")
    assert response.status_code == status.HTTP_200_OK
    assert any(
        blueprint_host["id"] == blueprint_id for blueprint_host in response.json()
    )

    # Delete the host blueprint
    response = await auth_integration_client.delete(
        f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check that the blueprint is gone
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_can_view_all_blueprints(
    auth_integration_client: AsyncClient,
    integration_client: AsyncClient,
) -> None:
    """Test that an admin is able to see blueprints for all users."""
    response = await auth_integration_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    response = await auth_integration_client.get(f"{BASE_ROUTE}/blueprints/ranges")
    assert response.status_code == status.HTTP_200_OK
    user1_blueprint_ids = {blueprint_range["id"] for blueprint_range in response.json()}

    # Login as new user
    _, email, password, _ = await register_user(integration_client)
    assert await login_user(integration_client, email, password)

    response = await integration_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    response = await integration_client.get(f"{BASE_ROUTE}/blueprints/ranges")
    user2_blueprint_ids = {blueprint_range["id"] for blueprint_range in response.json()}

    # Login as admin
    assert await login_user(
        integration_client, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD
    )
    response = await integration_client.get(f"{BASE_ROUTE}/blueprints/ranges")
    assert response.status_code == status.HTTP_200_OK
    admin_blueprint_ids = {blueprint_range["id"] for blueprint_range in response.json()}

    assert admin_blueprint_ids == user1_blueprint_ids.union(user2_blueprint_ids)
