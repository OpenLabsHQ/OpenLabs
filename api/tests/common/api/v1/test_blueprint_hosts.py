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
    valid_blueprint_subnet_create_payload,
)
from tests.test_utils import remove_key_recursively


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintHostAuth:
    """Test suite for /blueprints/hosts endpoints using the authenticated client fixture."""

    async def test_blueprint_host_get_non_empty_list(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test host blueprints to see that we get a 201 response and that correct headers exist."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
        )
        blueprint_id = int(response.json()["id"])
        assert response.status_code == status.HTTP_200_OK

        # Check hosts
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts?standalone_only=true"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) >= 1

        blueprint_host = next(
            host for host in response.json() if host["id"] == blueprint_id
        )
        remove_key_recursively(blueprint_host, "id")  # Our payload doesn't have IDs
        assert (
            blueprint_host == valid_blueprint_host_create_payload
        )  # Host has no nested attriutes

    async def test_blueprint_host_valid_payload(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 200 reponse and a valid ID in response."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert int(response.json()["id"])

    async def test_blueprint_host_get_host_invalid_id(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 when providing an invalid non-int ID."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_id = int(response.json()["id"])

        # Test that the invalid ID doesn't work
        random_str = "".join(
            random.choice(string.ascii_letters)  # noqa: S311
            for i in range(random.randint(1, 10))  # noqa: S311
        )
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts/{random_str}"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test that the valid ID still works
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_blueprint_host_get_host(self, auth_api_client: AsyncClient) -> None:
        """Test that we can retrieve the correct host after saving it in the database."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_id = int(response.json()["id"])

        # Get Host
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        recieved_host = response.json()

        # Validate response
        remove_key_recursively(recieved_host, "id")  # Our payload doesn't have IDs
        assert recieved_host == valid_blueprint_host_create_payload

    async def test_blueprint_host_get_nonexistent_host(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 404 error when requesting a nonexistent host in the database."""
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts/{random.randint(-420, -69)}"  # noqa: S311
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_host_duplicate_tags(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 error when a host has duplicate tags."""
        dup_tags_host = copy.deepcopy(valid_blueprint_host_create_payload)

        for _ in range(2):
            dup_tags_host["tags"].append("duplicate-tag")

        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts", json=dup_tags_host
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_host_long_tag(self, auth_api_client: AsyncClient) -> None:
        """Test that we get a 422 error when a host has a tag that is too long."""
        long_tag_host = copy.deepcopy(valid_blueprint_host_create_payload)

        # Max length 63
        long_tag = "h" + "i" * 75
        long_tag_host["tags"].append(long_tag)

        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts", json=long_tag_host
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_host_delete(self, auth_api_client: AsyncClient) -> None:
        """Test that we get can successfully delete host blueprints."""
        # Add host
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_id = int(response.json()["id"])

        # Delete host
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check that host is no longer in database
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_host_delete_invalid_id(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 422 when providing an invalid non-int ID."""
        random_str = "".join(
            random.choice(string.ascii_letters)  # noqa: S311
            for i in range(random.randint(1, 10))  # noqa: S311
        )
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/hosts/{random_str}"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_blueprint_host_delete_non_existent(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that we get a 404 when trying to delete a nonexistent host."""
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/hosts/{random.randint(-420, -69)}"  # noqa: S311
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_host_delete_non_standalone(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that we get a 404 when trying to delete a non-standalone host blueprint."""
        # Add a subnet blueprint
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            json=valid_blueprint_subnet_create_payload,
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_subnet_id = response.json()["id"]

        # Get subnet details
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets/{blueprint_subnet_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        blueprint_subnet = response.json()

        # Get host
        assert len(blueprint_subnet["hosts"]) >= 1
        blueprint_host = blueprint_subnet["hosts"][0]

        # Try to delete non-standalone host blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/hosts/{blueprint_host["id"]}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_host_add_remove_user_flow(
        self,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test the user flow of submitting a host blueprint, listing it out, then deleting it."""
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id: int = response.json()["id"]

        # Attempt to fetch the host blueprint
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Add id to JSON to mimic GET response
        recieved_host: dict[str, Any] = response.json()
        remove_key_recursively(
            recieved_host, "id"
        )  # Our creation payload doesn't have IDs
        assert recieved_host == valid_blueprint_host_create_payload

        # Attempt to list out all of user's blueprints
        response = await auth_api_client.get(f"{BASE_ROUTE}/blueprints/hosts")
        assert response.status_code == status.HTTP_200_OK
        assert any(
            blueprint_host["id"] == blueprint_id for blueprint_host in response.json()
        )

        # Delete the host blueprint
        response = await auth_api_client.delete(
            f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Check that the blueprint is gone
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintHostNoAuth:
    """Test suite for /blueprints/hosts endpoints using the UNauthenticated client fixture."""

    async def test_blueprint_host_get_all_empty_list(
        self, api_client: AsyncClient
    ) -> None:
        """Test that we get a 404 response when there are no host blueprints."""
        assert await authenticate_client(api_client)
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/hosts")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_blueprint_host_headers(
        self,
        api_client: AsyncClient,
    ) -> None:
        """Test that blueprint host headers endpoint works and sees the host blueprint we add."""
        # Create a new user so we don't have to filter through
        # existing host header entries
        assert await authenticate_client(api_client)

        # New users should have no blueprint hosts
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/hosts")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Add a host blueprint
        response = await api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id = int(response.json()["id"])

        # Fetch host blueprint headers
        response = await api_client.get(f"{BASE_ROUTE}/blueprints/hosts")
        assert response.status_code == status.HTTP_200_OK

        # Should only be our host
        assert len(response.json())
        assert blueprint_id == int(response.json()[0]["id"])


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client, auth_api_client",
    COMBO_API_CLIENT_PARAMS,
    indirect=True,
)
class TestBlueprintHostComboAuth:
    """Test suite for /blueprints/hosts endpoints using both the UNauthenticated and authenticated fixtures."""

    async def test_blueprint_host_invalid_other_user_delete(
        self,
        api_client: AsyncClient,
        auth_api_client: AsyncClient,
    ) -> None:
        """Test that the API doesn't allow us to remove blueprint hosts that don't exist for the user."""
        # Create a second user session (user2)
        assert await authenticate_client(api_client)

        # Add a host blueprint as user1
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"]

        blueprint_id = int(response.json()["id"])

        # Check that user2 can't delete it as it
        # does not exist as a deletable host for
        # user2
        response = await api_client.delete(
            f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Check that invalid IDs don't work either
        response = await api_client.delete(
            f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id * -1}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
