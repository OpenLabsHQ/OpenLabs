import copy
import random
import string
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from tests.api_test_utils import authenticate_client
from tests.common.api.v1.config import (
    API_CLIENT_PARAMS,
    AUTH_API_CLIENT_PARAMS,
    BASE_ROUTE,
    COMBO_API_CLIENT_PARAMS,
    valid_blueprint_subnet_create_payload,
    valid_blueprint_subnet_multi_create_payload,
    valid_blueprint_vpc_create_payload,
)
from tests.test_utils import remove_key_recursively


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintSubnetAuth:
    """Test suite for /blueprints/subnets endpoints using the authenticated client fixture."""

    async def test_blueprint_subnet_get_non_empty_list(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test subnet blueprints to see that we get a 200 response and that correct headers exist."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        blueprint_id = int(response.json()["id"])
        assert response.status_code == status.HTTP_200_OK

        # Check subnets
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets?standalone_only=true"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) >= 1

        blueprint_subnet = next(
            subnet for subnet in response.json() if subnet["id"] == blueprint_id
        )
        remove_key_recursively(blueprint_subnet, "id")  # Our payload doesn't have IDs

        expected_subnet = copy.deepcopy(valid_blueprint_subnet_create_payload)
        del expected_subnet["hosts"]  # Endpoint returns headers (no nested attributes)
        assert blueprint_subnet == expected_subnet

    async def test_blueprint_subnet_valid_payload(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 200 reponse and a valid ID in response."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        assert int(response.json()["id"])

    async def test_blueprint_subnet_valid_multi_payload(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 200 response and a valid ID response when submitting a subnet with multiple hosts."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        assert int(response.json()["id"])

    async def test_blueprint_subnet_get_subnet_invalid_id(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 422 when providing an invalid ID."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_id = int(response.json()["id"])

        # Test invalid ID
        random_str = "".join(
            random.choice(string.ascii_letters)  # noqa: S311
            for i in range(random.randint(1, 10))  # noqa: S311
        )
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets/{random_str}"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test that the valid ID still works
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_blueprint_subnet_invalid_subnet_cidr(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 422 response when the subnet CIDR is invalid."""
        invalid_payload = copy.deepcopy(valid_blueprint_subnet_create_payload)
        invalid_payload["cidr"] = "192.168.300.0/24"
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_subnet_invalid_public_cidr(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 422 response when the subnet CIDR is public."""
        invalid_payload = copy.deepcopy(valid_blueprint_subnet_create_payload)
        invalid_payload["cidr"] = "155.76.15.0/24"
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_subnet_too_many_hosts(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 response when more hosts in subnet than CIDR allows."""
        invalid_payload = copy.deepcopy(valid_blueprint_subnet_create_payload)
        invalid_payload["cidr"] = "192.168.1.0/31"  # Maximum 2 hosts

        # Add extra hosts
        for i in range(3):
            copy_host = copy.deepcopy(invalid_payload["hosts"][0])
            copy_host["hostname"] = copy_host["hostname"] + str(i)
            invalid_payload["hosts"].append(copy_host)

        max_hosts_allowed = 2
        assert len(invalid_payload["hosts"]) > max_hosts_allowed

        # Request
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_subnet_get_subnet(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we can retrieve the correct subnet after saving it in the database."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_id = response.json()["id"]

        # Retrieve new subnet
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        recieved_subnet = response.json()

        # Validate reponse
        remove_key_recursively(recieved_subnet, "id")  # Our payload doesn't have IDs
        assert recieved_subnet == valid_blueprint_subnet_create_payload

    async def test_blueprint_subnet_get_nonexistent_subnet(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 404 error when requesting a nonexistent subnet in the database."""
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets/{random.randint(-420, -69)}"  # noqa: S311
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_subnet_delete(self, auth_api_client: AsyncClient) -> None:
        """Test that we can sucessfully delete a subnet blueprint."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_id = int(response.json()["id"])

        # Delete subnet
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check that subnet is no longer in database
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_subnet_delete_invalid_id(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 404 when providing an invalid non-int ID."""
        random_str = "".join(
            random.choice(string.ascii_letters)  # noqa: S311
            for i in range(random.randint(1, 10))  # noqa: S311
        )
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/subnets/{random_str}"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_subnet_delete_non_standalone(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 404 when trying to delete a non-standalone blueprint subnet."""
        # Add a blueprint VPC
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_vpc_id = response.json()["id"]

        # Fetch VPC details
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_vpc_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_vpc = response.json()

        # New subnet blueprint
        assert len(blueprint_vpc["subnets"]) >= 1
        blueprint_subnet = blueprint_vpc["subnets"][0]

        # Try to delete non-standalone blueprint subnet
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_subnet["id"]}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_subnet_delete_cascade_single_host(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that when we delete a subnet blueprint it cascades and deletes the associated host."""
        # Add a subnet blueprint
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_id = int(response.json()["id"])

        # Get Subnet details
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_subnet = response.json()

        # New host blueprint
        assert len(blueprint_subnet["hosts"]) >= 1
        blueprint_host = blueprint_subnet["hosts"][0]

        # Delete standalone subnet blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check to see if the dependent host blueprint was also removed
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false"
        )

        if response.status_code == status.HTTP_200_OK:
            blueprint_host_ids = [host["id"] for host in response.json()]
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            blueprint_host_ids = []
        else:
            pytest.fail(f"Unknown status code: {response.status_code} recieved!")

        assert blueprint_host["id"] not in blueprint_host_ids

    async def test_blueprint_subnet_delete_cascade_multi_hosts(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that when we delete subnet blueprint with multiple hosts it cascades and deletes the associated hosts."""
        # Add subnet blueprint
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_multi_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_subnet_id = response.json()["id"]

        # Fetch subnet details
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_subnet_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_subnet = response.json()

        # Hosts
        blueprint_hosts = blueprint_subnet["hosts"]

        # Delete subnet blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_subnet["id"]}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check host removal
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false"
        )

        if response.status_code == status.HTTP_200_OK:
            blueprint_host_ids = [host["id"] for host in response.json()]
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            blueprint_host_ids = []
        else:
            pytest.fail(f"Unknown status code: {response.status_code} recieved!")

        assert not any(
            blueprint_host["id"] in blueprint_host_ids
            for blueprint_host in blueprint_hosts
        )

    async def test_blueprint_subnet_add_remove_user_flow(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test the user flow of submitting a subnet blueprint, listing it out, then deleting it."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id: int = response.json()["id"]

        # Attempt to fetch the subnet
        response = await auth_api_client.get(
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
        response = await auth_api_client.get(f"{BASE_ROUTE}/blueprints/subnets")
        assert response.status_code == status.HTTP_200_OK
        assert any(
            blueprint_subnet["id"] == blueprint_id
            for blueprint_subnet in response.json()
        )

        # Delete the subnet blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check that the blueprint is gone
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintSubnetNoAuth:
    """Test suite for /blueprints/subnets endpoints using the UNauthenticated client fixture."""

    async def test_blueprint_subnet_get_all_empty_list(
        self, api_client: AsyncClient
    ) -> None:
        """Test that we get a 404 response when there are no subnet blueprints."""
        assert await authenticate_client(api_client)
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/subnets")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_subnet_headers(
        self,
        api_client: AsyncClient,
    ) -> None:
        """Test that blueprint subnet headers endpoint works and sees the subnet blueprint we add."""
        # Create a new user so we don't have to filter through
        # existing subnet header entries
        assert await authenticate_client(api_client)

        # New users should have no blueprint subnets
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/subnets")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Add a subnet blueprint
        response = await api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id = int(response.json()["id"])

        # Fetch subnet blueprint headers
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/subnets")
        assert response.status_code == status.HTTP_200_OK

        # Should only be our subnet
        assert len(response.json())
        assert blueprint_id == int(response.json()[0]["id"])


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client, auth_api_client",
    COMBO_API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintSubnetComboAuth:
    """Test suite for /blueprints/subnets endpoints using both the UNauthenticated and authenticated fixtures."""

    async def test_blueprint_subnet_invalid_other_user_delete(
        self,
        api_client: AsyncClient,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that the API doesn't allow us to remove blueprint subnets that don't exist for the user."""
        # Create a second user session (user2)
        assert await authenticate_client(api_client)

        # Add a subnet blueprint as user1
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id = int(response.json()["id"])

        # Check that user2 can't delete it as it
        # does not exist as a deletable subnet for
        # user2
        response = await api_client.delete(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Check that invalid IDs don't work either
        response = await api_client.delete(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id * -1}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
