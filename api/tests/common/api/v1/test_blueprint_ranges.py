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
    valid_blueprint_host_create_payload,
    valid_blueprint_range_create_payload,
    valid_blueprint_range_multi_create_payload,
    valid_blueprint_subnet_create_payload,
    valid_blueprint_vpc_create_payload,
)
from tests.test_utils import remove_key_recursively


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintRangeAuth:
    """Test suite for /blueprints/ranges endpoints using the authenticated client fixture."""

    async def test_blueprint_range_valid_payload(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 200 and a valid ID in response."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert int(response.json()["id"])

    async def test_blueprint_range_valid_multi_payload(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 200 and a valid ID in response to a payload with multiple VPCs, subnets, and hosts."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges",
            json=valid_blueprint_range_multi_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        assert int(response.json()["id"])

    async def test_blueprint_range_get_range_invalid_id(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 422 when providing an non-int ID when fetching range blueprints."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_id = int(response.json()["id"])

        # Test that invalid IDs don't work
        random_str = "".join(
            random.choice(string.ascii_letters)  # noqa: S311
            for i in range(random.randint(1, 10))  # noqa: S311
        )
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{random_str}"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test that the valid ID still works
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_blueprint_range_invalid_vpc_cidr(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test for 422 response when VPC CIDR is invalid."""
        # Use deepcopy to ensure all nested dicts are copied
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        invalid_payload["vpcs"][0][
            "cidr"
        ] = "192.168.300.0/24"  # Assign the invalid CIDR block
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_overlap_vpc_cidr(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 response when the range's VPC's CIDRs overlap."""
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        assert len(invalid_payload["vpcs"]) >= 1
        invalid_payload["vpcs"][0]["cidr"] = "192.168.1.0/24"

        # Create overlapping VPC
        overlapping_vpc = copy.deepcopy(invalid_payload["vpcs"][0])
        overlapping_vpc["cidr"] = "192.168.1.0/26"
        overlapping_vpc["name"] = invalid_payload["vpcs"][0]["name"] + "-1"
        overlapping_vpc["subnets"][0]["cidr"] = "192.168.1.0/27"
        invalid_payload["vpcs"].append(overlapping_vpc)

        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_invalid_subnet_cidr(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test for 422 response when subnet CIDR is invalid."""
        # Use deepcopy to ensure all nested dicts are copied
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        invalid_payload["vpcs"][0]["subnets"][0][
            "cidr"
        ] = "192.168.300.0/24"  # Assign the invalid CIDR block
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_invalid_vpc_subnet_cidr_contain(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test for 422 response when subnet CIDR is not contained in the VPC CIDR."""
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)

        # VPC CIDR
        invalid_payload["vpcs"][0]["cidr"] = "192.168.0.0/16"

        # Subnet CIDR
        invalid_payload["vpcs"][0]["subnets"][0][
            "cidr"
        ] = "172.16.1.0/24"  # Assign the invalid CIDR block

        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_empty_tag(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test for a 422 response when a tag is empty."""
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0]["tags"].append("")
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_invalid_provider(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test for a 422 response when the provider is invalid."""
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        invalid_payload["provider"] = "invalid_provider"  # Not a valid enum value
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_invalid_hostname(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test for a 422 response when a hostname is invalid."""
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0][
            "hostname"
        ] = "-i-am-invalid"
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_duplicate_vpc_names(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test for a 422 response when multiple VPCs share the same name."""
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        invalid_payload["vpcs"].append(
            copy.deepcopy(invalid_payload["vpcs"][0])
        )  # Duplicate the first VPC
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_duplicate_subnet_names(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test for a 422 response when multiple subnets share the same name."""
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        invalid_payload["vpcs"][0]["subnets"].append(
            copy.deepcopy(invalid_payload["vpcs"][0]["subnets"][0])
        )
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_duplicate_host_hostnames(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test for a 422 response when multiple hosts share the same hostname."""
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        invalid_payload["vpcs"][0]["subnets"][0]["hosts"].append(
            copy.deepcopy(invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0])
        )
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_get_range(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we can retrieve the correct range after saving it in the database."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK

        blueprint_id = int(response.json()["id"])

        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check response data
        recieved_blueprint = response.json()
        remove_key_recursively(recieved_blueprint, "id")  # Our payload doesn't have IDs
        assert recieved_blueprint == valid_blueprint_range_create_payload

    async def test_blueprint_range_get_nonexistent_range(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 404 error when requesting an nonexistent blueprint range in the database."""
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{random.randint(-420, -69)}"  # noqa: S311
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_range_subnet_too_many_hosts(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 422 error when more hosts in subnet that CIDR allows."""
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        invalid_payload["vpcs"][0]["subnets"][0][
            "cidr"
        ] = "192.168.1.0/31"  # Maximum 2 hosts

        # Add extra hosts
        for i in range(3):
            copy_host = copy.deepcopy(
                invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0]
            )
            copy_host["hostname"] = copy_host["hostname"] + str(i)
            invalid_payload["vpcs"][0]["subnets"][0]["hosts"].append(copy_host)

        max_hosts_allowed = 2
        assert (
            len(invalid_payload["vpcs"][0]["subnets"][0]["hosts"]) > max_hosts_allowed
        )

        # Request
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_host_size_too_small(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 422 error when the disk size of a host is too small."""
        invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
        invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0]["size"] = 2

        # Request
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_delete(self, auth_api_client: AsyncClient) -> None:
        """Test that we can sucessfully delete a blueprint range."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK

        blueprint_id = int(response.json()["id"])

        # Delete blueprint range
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check that range is no longer in database
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_range_delete_invalid_id(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 404 when providing an invalid ID."""
        random_str = "".join(
            random.choice(string.ascii_letters)  # noqa: S311
            for i in range(random.randint(1, 10))  # noqa: S311
        )
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/ranges/{random_str}"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_range_delete_non_existent(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 404 when trying to delete a nonexistent blueprint range."""
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/ranges/{random.randint(-420, -69)}"  # noqa: S311
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_range_delete_cascade_single_vpc_subnet_and_host(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that when we delete a range blueprint it cascades and deletes the associated single vpc, subnet, and host."""
        # Add a range blueprint
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_range_id = response.json()["id"]

        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_range_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_range = response.json()

        # VPC
        assert len(blueprint_range["vpcs"]) == 1
        blueprint_vpc = blueprint_range["vpcs"][0]

        # Subnet
        assert len(blueprint_vpc["subnets"]) == 1
        blueprint_subnet = blueprint_vpc["subnets"][0]

        # Host
        assert len(blueprint_subnet["hosts"]) == 1
        blueprint_host = blueprint_subnet["hosts"][0]

        # Delete standalone range blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_range["id"]}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check to see if dependent vpc blueprint was removed
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/vpcs?standalone_only=false"
        )

        if response.status_code == status.HTTP_200_OK:
            blueprint_vpc_ids = [vpc["id"] for vpc in response.json()]
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            blueprint_vpc_ids = []
        else:
            pytest.fail(f"Unknown status code: {response.status_code} recieved!")

        assert blueprint_vpc["id"] not in blueprint_vpc_ids

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

        assert blueprint_subnet["id"] not in blueprint_subnet_ids

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

        assert blueprint_host["id"] not in blueprint_host_ids

    async def test_blueprint_range_delete_cascade_multi_vpc_subnet_and_host(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that when we delete range blueprint with multiple vpcs, subnets, and hosts it cascades and deletes the associated vpcs, subnets, and hosts."""
        # Add range blueprint
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges",
            json=valid_blueprint_range_multi_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_range_id = response.json()["id"]

        # Fetch range details
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_range_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_range = response.json()

        # VPC
        assert len(blueprint_range["vpcs"]) > 1
        blueprint_vpc = random.choice(blueprint_range["vpcs"])  # noqa: S311

        # Subnet
        multi_subnet_vpcs = [
            vpc for vpc in blueprint_range["vpcs"] if len(vpc["subnets"]) > 1
        ]
        assert len(multi_subnet_vpcs) >= 1
        random_vpc = random.choice(multi_subnet_vpcs)  # noqa: S311
        blueprint_subnet = random.choice(random_vpc["subnets"])  # noqa: S311

        # Host
        blueprint_host = random.choice(blueprint_subnet["hosts"])  # noqa: S311

        # Delete range blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_range["id"]}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check VPC removal
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/vpcs?standalone_only=false"
        )

        if response.status_code == status.HTTP_200_OK:
            blueprint_vpc_ids = [vpc["id"] for vpc in response.json()]
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            blueprint_vpc_ids = []
        else:
            pytest.fail(f"Unknown status code: {response.status_code} recieved!")

        assert blueprint_vpc["id"] not in blueprint_vpc_ids

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

    async def test_blueprint_range_add_remove_user_flow(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test the user flow of submitting a range blueprint, listing it out, then deleting it."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id: int = response.json()["id"]

        # Attempt to fetch the range
        response = await auth_api_client.get(
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
        response = await auth_api_client.get(f"{BASE_ROUTE}/blueprints/ranges")
        assert response.status_code == status.HTTP_200_OK
        assert any(
            blueprint_range["id"] == blueprint_id for blueprint_range in response.json()
        )

        # Delete the range blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check that the blueprint is gone
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintRangeNoAuth:
    """Test suite for /blueprints/ranges endpoints using the UNauthenticated client fixture."""

    async def test_blueprint_range_get_all_empty_list(
        self,
        api_client: AsyncClient,
    ) -> None:
        """Test that we get a 404 response when there are no range blueprints."""
        assert await authenticate_client(api_client)
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/ranges")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_range_get_non_empty_list(
        self, api_client: AsyncClient
    ) -> None:
        """Test all blueprints to see that we get a 200 response and that correct IDs exist."""
        assert await authenticate_client(api_client)

        # Add blueprint
        response = await api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_id = int(response.json()["id"])

        # Retrieve blueprint
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/ranges")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
        recieved_range = response.json()[0]
        assert recieved_range["id"] == blueprint_id

        # Validate response
        # Mimic the header response with the valid JSON
        valid_blueprint_copy = copy.deepcopy(valid_blueprint_range_create_payload)
        del valid_blueprint_copy["vpcs"]
        remove_key_recursively(
            recieved_range, "id"
        )  # Our creation payload doesn't have IDs
        assert recieved_range == valid_blueprint_copy

    async def test_blueprint_range_vpc_subnet_host_non_standalone(
        self,
        api_client: AsyncClient,
    ) -> None:
        """Test that, after uploading range blueprint previously, we have all non-standalone blueprints."""
        assert await authenticate_client(api_client)

        # Add a range blueprint
        response = await api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK

        # Checks VPCs
        response = await api_client.get(
            f"{BASE_ROUTE}/blueprints/vpcs?standalone_only=false"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

        blueprint_vpc = response.json()[0]
        remove_key_recursively(blueprint_vpc, "id")  # Our payload does not have IDs
        expected_vpc = copy.deepcopy(valid_blueprint_vpc_create_payload)
        del expected_vpc[
            "subnets"
        ]  # The endpoint returns headers (no nested attributes)
        assert blueprint_vpc == expected_vpc

        # Check Subnets
        response = await api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets?standalone_only=false"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

        blueprint_subnet = response.json()[0]
        remove_key_recursively(blueprint_subnet, "id")  # Our payload does not have IDs
        expected_subnet = copy.deepcopy(valid_blueprint_subnet_create_payload)
        del expected_subnet[
            "hosts"
        ]  # The endpoint returns headers (no nested attributes)
        assert blueprint_subnet == expected_subnet

        # Check Hosts
        response = await api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1

        blueprint_host = response.json()[0]
        remove_key_recursively(blueprint_host, "id")  # Our payload does not have IDs
        assert blueprint_host == valid_blueprint_host_create_payload

    async def test_blueprint_range_headers(
        self,
        api_client: AsyncClient,
    ) -> None:
        """Test that blueprint range headers endpoint works and sees the range blueprint we add."""
        # Create a new user so we don't have to filter through
        # existing range header entries
        assert await authenticate_client(api_client)

        # New users should have no blueprint ranges
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/ranges")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Add a range blueprint
        response = await api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id = int(response.json()["id"])

        # Fetch range blueprint headers
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/ranges")
        assert response.status_code == status.HTTP_200_OK

        # Should only be our range
        assert len(response.json())
        assert blueprint_id == int(response.json()[0]["id"])


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client, auth_api_client",
    COMBO_API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintRangeComboAuth:
    """Test suite for /blueprints/ranges endpoints using both the UNauthenticated and authenticated fixtures."""

    async def test_blueprint_range_invalid_other_user_delete(
        self,
        api_client: AsyncClient,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that the API doesn't allow us to remove blueprint ranges that don't exist for the user."""
        # Create a second user session (user2)
        assert await authenticate_client(api_client)

        # Add a range blueprint as user1
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id = int(response.json()["id"])

        # Check that user2 can't delete it as it
        # does not exist as a deletable range for
        # user2
        response = await api_client.delete(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Check that invalid IDs don't work either
        response = await api_client.delete(
            f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id * -1}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_range_not_visible_to_other_users(
        self, api_client: AsyncClient, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 404 response when trying to access another user's blueprints."""
        # Add a range user1
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges",
            json=valid_blueprint_range_multi_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK

        # Get user1 ranges
        response = await auth_api_client.get(f"{BASE_ROUTE}/blueprints/ranges")
        assert response.status_code == status.HTTP_200_OK
        user1_blueprint_ids = {blueprint["id"] for blueprint in response.json()}

        # Login as new user2
        assert await authenticate_client(api_client)

        # Add range to user2
        response = await api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
        )
        assert response.status_code == status.HTTP_200_OK

        # Get user2 ranges
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/ranges")
        user2_blueprint_ids = {blueprint["id"] for blueprint in response.json()}

        assert user1_blueprint_ids.isdisjoint(user2_blueprint_ids)

        for blueprint_id in user1_blueprint_ids:
            response = await api_client.get(
                f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND
