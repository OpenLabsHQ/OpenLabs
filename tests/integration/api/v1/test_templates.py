import pytest
from fastapi import status
from httpx import AsyncClient

from .config import (
    BASE_ROUTE,
    valid_host_payload,
    valid_range_payload,
    valid_subnet_payload,
    valid_vpc_payload,
)


@pytest.mark.asyncio(loop_scope="session")
async def test_user_add_remove_range_template_flow(
    auth_integration_client: AsyncClient,
) -> None:
    """Test the user flow of submitting a range template, listing it out, then deleting it."""
    response = await auth_integration_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    range_id: str = response.json()["id"]

    # Attempt to fetch the range
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/templates/ranges/{range_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    expected_response = {"id": range_id, **valid_range_payload}
    assert response.json() == expected_response

    # Attempt to list out all of user's templates
    response = await auth_integration_client.get(f"{BASE_ROUTE}/templates/ranges")
    assert response.status_code == status.HTTP_200_OK
    assert any(r["id"] == range_id for r in response.json())

    # Delete the range template
    response = await auth_integration_client.delete(
        f"{BASE_ROUTE}/templates/ranges/{range_id}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check that the template is gone
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/templates/ranges/{range_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_user_add_remove_vpc_template_flow(
    auth_integration_client: AsyncClient,
) -> None:
    """Test the user flow of submitting a VPC template, listing it out, then deleting it."""
    response = await auth_integration_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=valid_vpc_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    vpc_id: str = response.json()["id"]

    # Attempt to fetch the VPC
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/templates/vpcs/{vpc_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    expected_response = {"id": vpc_id, **valid_vpc_payload}
    assert response.json() == expected_response

    # Attempt to list out all of user's templates
    response = await auth_integration_client.get(f"{BASE_ROUTE}/templates/vpcs")
    assert response.status_code == status.HTTP_200_OK
    assert any(vpc["id"] == vpc_id for vpc in response.json())

    # Delete the VPC template
    response = await auth_integration_client.delete(
        f"{BASE_ROUTE}/templates/vpcs/{vpc_id}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check that the template is gone
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/templates/vpcs/{vpc_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_user_add_remove_subnet_template_flow(
    auth_integration_client: AsyncClient,
) -> None:
    """Test the user flow of submitting a subnet template, listing it out, then deleting it."""
    response = await auth_integration_client.post(
        f"{BASE_ROUTE}/templates/subnets", json=valid_subnet_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    subnet_id: str = response.json()["id"]

    # Attempt to fetch the subnet
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/templates/subnets/{subnet_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    expected_response = {"id": subnet_id, **valid_subnet_payload}
    assert response.json() == expected_response

    # Attempt to list out all of user's templates
    response = await auth_integration_client.get(f"{BASE_ROUTE}/templates/subnets")
    assert response.status_code == status.HTTP_200_OK
    assert any(s["id"] == subnet_id for s in response.json())

    # Delete the subnet template
    response = await auth_integration_client.delete(
        f"{BASE_ROUTE}/templates/subnets/{subnet_id}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check that the template is gone
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/templates/subnets/{subnet_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_user_add_remove_host_template_flow(
    auth_integration_client: AsyncClient,
) -> None:
    """Test the user flow of submitting a host template, listing it out, then deleting it."""
    response = await auth_integration_client.post(
        f"{BASE_ROUTE}/templates/hosts", json=valid_host_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    host_id: str = response.json()["id"]

    # Attempt to fetch the host
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/templates/hosts/{host_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    expected_response = {"id": host_id, **valid_host_payload}
    assert response.json() == expected_response

    # Attempt to list out all of user's templates
    response = await auth_integration_client.get(f"{BASE_ROUTE}/templates/hosts")
    assert response.status_code == status.HTTP_200_OK
    assert any(h["id"] == host_id for h in response.json())

    # Delete the host template
    response = await auth_integration_client.delete(
        f"{BASE_ROUTE}/templates/hosts/{host_id}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check that the template is gone
    response = await auth_integration_client.get(
        f"{BASE_ROUTE}/templates/hosts/{host_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
