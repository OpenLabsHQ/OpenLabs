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
    valid_blueprint_range_create_payload,
    valid_blueprint_vpc_create_payload,
    valid_blueprint_vpc_multi_create_payload,
)
from tests.test_utils import remove_key_recursively


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintVPCAuth:
    """Test suite for /blueprints/vpcs endpoints using the authenticated client fixture."""

    async def test_blueprint_vpc_get_non_empty_list(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test VPC blueprints to see that we get a 200 response and that correct headers exist."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
        )
        blueprint_id = int(response.json()["id"])
        assert response.status_code == status.HTTP_200_OK

        # Check VPCs
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/vpcs?standalone_only=true"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) >= 1
        assert any(
            blueprint_id == blueprint_vpc["id"] for blueprint_vpc in response.json()
        )

        blueprint_vpc = next(
            vpc for vpc in response.json() if vpc["id"] == blueprint_id
        )
        remove_key_recursively(blueprint_vpc, "id")  # Our payload does not have IDs

        expected_vpc = copy.deepcopy(valid_blueprint_vpc_create_payload)
        del expected_vpc["subnets"]  # Endpoint returns headers (no nested attributes)
        assert blueprint_vpc == expected_vpc

    async def test_blueprint_vpc_valid_payload(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 200 response and a valid ID in response."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert int(response.json()["id"])

    async def test_blueprint_vpc_valid_multi_payload(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 200 response and a valid ID in response with a payload VPC with multiple subnets."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs",
            json=valid_blueprint_vpc_multi_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        assert int(response.json()["id"])

    async def test_blueprint_vpc_get_vpc_invalid_id(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 when providing an invalid non-int ID."""
        random_str = "".join(
            random.choice(string.ascii_letters)  # noqa: S311
            for i in range(random.randint(1, 10))  # noqa: S311
        )

        # Test that the invalid ID doesn't work
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/vpcs/{random_str}"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_vpc_invalid_cidr(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 response when the VPC CIDR is invalid."""
        invalid_payload = copy.deepcopy(valid_blueprint_vpc_create_payload)
        invalid_payload["cidr"] = "192.168.300.0/24"
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_vpc_invalid_public_cidr(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 response when the VPC CIDR is public."""
        invalid_payload = copy.deepcopy(valid_blueprint_vpc_create_payload)
        invalid_payload["cidr"] = "155.75.140.0/24"
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_vpc_invalid_subnet_cidr(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 response when the VPC subnet CIDR is invalid."""
        invalid_payload = copy.deepcopy(valid_blueprint_vpc_create_payload)
        assert len(invalid_payload["subnets"]) >= 1
        invalid_payload["subnets"][0]["cidr"] = "192.168.300.0/24"
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_vpc_overlap_subnet_cidr(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 response when the VPC subnet's CIDRs overlap."""
        invalid_payload = copy.deepcopy(valid_blueprint_vpc_create_payload)
        assert len(invalid_payload["subnets"]) >= 1
        invalid_payload["subnets"][0]["cidr"] = "192.168.1.0/24"

        # Create overlapping subnet
        overlapping_subnet = copy.deepcopy(invalid_payload["subnets"][0])
        overlapping_subnet["cidr"] = "192.168.1.0/26"
        overlapping_subnet["name"] = invalid_payload["subnets"][0]["name"] + "-1"
        invalid_payload["subnets"].append(overlapping_subnet)

        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_vpc_invalid_vpc_subnet_cidr_contain(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 422 response when the subnet CIDR is not contained in the VPC CIDR."""
        invalid_payload = copy.deepcopy(valid_blueprint_vpc_create_payload)

        # VPC CIDR
        invalid_payload["cidr"] = "192.168.0.0/16"

        # Subnet CIDR
        assert len(invalid_payload["subnets"]) >= 1
        invalid_payload["subnets"][0]["cidr"] = "172.16.1.0/24"

        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_vpc_get_vpc(self, auth_api_client: AsyncClient) -> None:
        """Test that we can retrieve the correct VPC after saving it in the database."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
        )
        assert response.status_code == status.HTTP_200_OK

        vpc_id = int(response.json()["id"])

        response = await auth_api_client.get(f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}")
        assert response.status_code == status.HTTP_200_OK

        # Validate response
        recieved_vpc = response.json()
        remove_key_recursively(recieved_vpc, "id")  # Our payload doesn't have IDs
        assert recieved_vpc == valid_blueprint_vpc_create_payload

    async def test_blueprint_vpc_get_nonexistent_vpc(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 404 error when requesting a nonexistent vpc blueprint in the database."""
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/vpcs/{random.randint(-420, -69)}"  # noqa: S311
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_vpc_delete(self, auth_api_client: AsyncClient) -> None:
        """Test that we can sucessfully delete a VPC blueprint."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
        )
        assert response.status_code == status.HTTP_200_OK

        vpc_id = int(response.json()["id"])

        # Delete VPC
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check that VPC is no longer in database
        response = await auth_api_client.get(f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_vpc_delete_invalid_id(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 when providing an invalid non-int ID."""
        random_str = "".join(
            random.choice(string.ascii_letters)  # noqa: S311
            for i in range(random.randint(1, 10))  # noqa: S311
        )
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/vpcs/{random_str}"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_vpc_delete_non_existent(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 404 when trying to delete a nonexistent VPC blueprint."""
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/vpcs/{random.randint(-420, -69)}"  # noqa: S311
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_vpc_delete_non_standalone(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 404 when trying to delete a non-standalone VPC blueprint part of a range blueprint."""
        # Add a range blueprint
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_range_id = response.json()["id"]

        # Fetch full range details
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_range_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_range = response.json()

        # Get dependent VPC blueprint id
        assert len(blueprint_range["vpcs"]) >= 1
        blueprint_vpc_id = blueprint_range["vpcs"][0]["id"]

        # Attempt to delete non-standalone VPC blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_vpc_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_vpc_delete_cascade_single_subnet_and_host(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that when we delete a VPC blueprint it cascades and deletes the associated hosts."""
        # Add a blueprint VPC
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        vpc_id = int(response.json()["id"])

        # Fetch VPC details
        response = await auth_api_client.get(f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}")
        blueprint_vpc = response.json()

        # Get new subnet ID
        assert len(blueprint_vpc["subnets"]) >= 1
        blueprint_subnet = blueprint_vpc["subnets"][0]
        blueprint_subnet_id = blueprint_subnet["id"]

        # Get new Host ID
        assert len(blueprint_subnet["hosts"]) >= 1
        blueprint_host = blueprint_subnet["hosts"][0]
        blueprint_host_id = blueprint_host["id"]

        # Delete standalone blueprint VPC
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check to see if dependent subnet blueprint was removed
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets?standalone_only=false"
        )

        if response.status_code == status.HTTP_200_OK:
            blueprint_subnet_ids = [subnet["id"] for subnet in response.json()]
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            blueprint_subnet_ids = []
        else:
            pytest.fail(f"Unknown status code: {response.status_code} recieved!")

        assert blueprint_subnet_id not in blueprint_subnet_ids

        # Check to see if the dependent host blueprint was removed
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false"
        )

        if response.status_code == status.HTTP_200_OK:
            blueprint_host_ids = [host["id"] for host in response.json()]
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            blueprint_host_ids = []
        else:
            pytest.fail(f"Unknown status code: {response.status_code} recieved!")

        assert blueprint_host_id not in blueprint_host_ids

    async def test_blueprint_vpc_delete_cascade_multi_subnet_and_host(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that when we delete VPC blueprint with multiple subnets and hosts it cascades and deletes the associated subnets and hosts."""
        # Add VPC blueprint
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs",
            json=valid_blueprint_vpc_multi_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_vpc_id = response.json()["id"]

        # Fetch VPC details
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_vpc_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_vpc = response.json()

        # Subnet
        multi_host_subnets = [
            subnet for subnet in blueprint_vpc["subnets"] if len(subnet["hosts"]) > 1
        ]
        assert len(multi_host_subnets) >= 1
        blueprint_subnet = random.choice(multi_host_subnets)  # noqa: S311

        # Host
        blueprint_host = random.choice(blueprint_subnet["hosts"])  # noqa: S311

        # Delete VPC blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_vpc["id"]}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check Subnet removal
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets?standalone_only=false"
        )

        if response.status_code == status.HTTP_200_OK:
            blueprint_subnet_ids = [subnet["id"] for subnet in response.json()]
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            blueprint_subnet_ids = []
        else:
            pytest.fail(f"Unknown status code: {response.status_code} recieved!")

        assert blueprint_subnet["id"] not in blueprint_subnet_ids

        # Check Host removal
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

    async def test_blueprint_vpc_add_remove_user_flow(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test the user flow of submitting a VPC blueprint, listing it out, then deleting it."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id: int = response.json()["id"]

        # Attempt to fetch the VPC
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Add id to JSON to mimic GET response
        recieved_vpc: dict[str, Any] = response.json()
        remove_key_recursively(
            recieved_vpc, "id"
        )  # Our creation payload doesn't have IDs
        assert recieved_vpc == valid_blueprint_vpc_create_payload

        # Attempt to list out all of user's blueprints
        response = await auth_api_client.get(f"{BASE_ROUTE}/blueprints/vpcs")
        assert response.status_code == status.HTTP_200_OK
        assert any(
            blueprint_vpc["id"] == blueprint_id for blueprint_vpc in response.json()
        )

        # Delete the VPC blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check that the blueprint is gone
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintVPCNoAuth:
    """Test suite for /blueprints/vpcs endpoints using the UNauthenticated client fixture."""

    async def test_blueprint_vpc_get_all_empty_list(
        self, api_client: AsyncClient
    ) -> None:
        """Test that we get a 404 response when there are no VPC blueprints."""
        assert await authenticate_client(api_client)
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/vpcs")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_vpc_headers(
        self,
        api_client: AsyncClient,
    ) -> None:
        """Test that blueprint VPC headers endpoint works and sees the VPC blueprint we add."""
        # Create a new user so we don't have to filter through
        # existing VPC header entries
        assert await authenticate_client(api_client)

        # New users should have no blueprint VPCs
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/vpcs")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Add a VPC blueprint
        response = await api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id = int(response.json()["id"])

        # Fetch VPC blueprint headers
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/vpcs")
        assert response.status_code == status.HTTP_200_OK

        # Should only be our VPC
        assert len(response.json())
        assert blueprint_id == int(response.json()[0]["id"])


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client, auth_api_client",
    COMBO_API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintVPCComboAuth:
    """Test suite for /blueprints/vpcs endpoints using both the UNauthenticated and authenticated fixtures."""

    async def test_blueprint_vpc_invalid_other_user_delete(
        self,
        api_client: AsyncClient,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that the API doesn't allow us to remove blueprint VPCs that don't exist for the user."""
        # Create a second user session (user2)
        assert await authenticate_client(api_client)

        # Add a VPC blueprint as user1
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id = int(response.json()["id"])

        # Check that user2 can't delete it as it
        # does not exist as a deletable VPC for
        # user2
        response = await api_client.delete(
            f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Check that invalid IDs don't work either
        response = await api_client.delete(
            f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_id * -1}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
