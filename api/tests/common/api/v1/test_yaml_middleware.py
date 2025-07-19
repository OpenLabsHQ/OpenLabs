import pytest
import yaml
from fastapi import status
from httpx import AsyncClient

from tests.common.api.v1.config import (
    AUTH_API_CLIENT_PARAMS,
    BASE_ROUTE,
    valid_blueprint_host_create_payload,
    valid_blueprint_range_create_payload,
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
class TestYamlMiddleware:
    """Test suite for JSON to YAML middleware."""

    async def test_blueprint_range_yaml_to_json(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that YAML payload is correctly converted to JSON for range blueprints."""
        yaml_payload = yaml.dump(valid_blueprint_range_create_payload)

        # Post with YAML content type
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges",
            content=yaml_payload,
            headers={"Content-Type": "application/yaml"},
        )
        assert response.status_code == status.HTTP_200_OK
        range_id = response.json()["id"]

        # Verify the blueprint was correctly stored
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{range_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Validate response
        recieved_range = response.json()
        remove_key_recursively(recieved_range, "id")
        assert recieved_range == valid_blueprint_range_create_payload

    async def test_blueprint_vpc_yaml_to_json(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that YAML payload is correctly converted to JSON for VPC blueprints."""
        yaml_payload = yaml.dump(valid_blueprint_vpc_create_payload)

        # Post with YAML content type
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/vpcs",
            content=yaml_payload,
            headers={"Content-Type": "application/yaml"},
        )
        assert response.status_code == status.HTTP_200_OK
        vpc_id = response.json()["id"]

        # Verify the blueprint was correctly stored
        response = await auth_api_client.get(f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}")
        assert response.status_code == status.HTTP_200_OK

        # Validate response
        recieved_vpc = response.json()
        remove_key_recursively(recieved_vpc, "id")
        assert recieved_vpc == valid_blueprint_vpc_create_payload

    async def test_blueprint_subnet_yaml_to_json(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that YAML payload is correctly converted to JSON for subnet blueprints."""
        yaml_payload = yaml.dump(valid_blueprint_subnet_create_payload)

        # Post with YAML content type
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/subnets",
            content=yaml_payload,
            headers={"Content-Type": "application/yaml"},
        )
        assert response.status_code == status.HTTP_200_OK
        subnet_id = response.json()["id"]

        # Verify the blueprint was correctly stored
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/subnets/{subnet_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Validate response
        recieved_subnet = response.json()
        remove_key_recursively(recieved_subnet, "id")
        assert recieved_subnet == valid_blueprint_subnet_create_payload

    async def test_blueprint_host_yaml_to_json(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that YAML payload is correctly converted to JSON for host blueprints."""
        yaml_payload = yaml.dump(valid_blueprint_host_create_payload)

        # Post with YAML content type
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/hosts",
            content=yaml_payload,
            headers={"Content-Type": "application/yaml"},
        )
        assert response.status_code == status.HTTP_200_OK
        host_id = response.json()["id"]

        # Verify the blueprint was correctly stored
        response = await auth_api_client.get(f"{BASE_ROUTE}/blueprints/hosts/{host_id}")
        assert response.status_code == status.HTTP_200_OK

        # Validate response
        recieved_host = response.json()
        remove_key_recursively(recieved_host, "id")
        assert recieved_host == valid_blueprint_host_create_payload

    async def test_blueprint_yaml_to_json_invalid_yaml(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that invalid YAML payloads are properly handled with an error."""
        # Invalid YAML content (missing colon after field)
        invalid_yaml = """
        name example-range-invalid
        provider: aws
        vpn: false
        vnc: false
        vpcs:
        - name: example-vpc-1
        cidr: 192.168.0.0/16
        """

        # Post with YAML content type
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges",
            content=invalid_yaml,
            headers={"Content-Type": "application/yaml"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "yaml" in str(response.json()["detail"]).lower()

    async def test_yaml_middleware_scoped_properly(
        self, auth_api_client: AsyncClient
    ) -> None:
        """Test that the YAML middleware is properly scoped to the correct routes."""
        # Create a minimal user payload
        user_payload = {
            "email": "test-yaml-scope@example.com",
            "password": "testPassword123!",
            "name": "Test User",
        }
        yaml_payload = yaml.dump(user_payload)
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/auth/register",
            content=yaml_payload,
            headers={"Content-Type": "application/yaml"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_yaml_tag_propagation(self, auth_api_client: AsyncClient) -> None:
        """Test that tags are processed but the test verifies request conversion not database storage."""
        # Create a payload with minimal required attributes but with tags at all levels
        range_with_tags = {
            "name": "tags-test-range",
            "provider": "aws",
            "vnc": False,
            "vpn": False,
            "tags": ["range-tag"],
            "vpcs": [
                {
                    "name": "tags-test-vpc",
                    "cidr": "10.0.0.0/16",
                    "tags": ["vpc-tag"],
                    "subnets": [
                        {
                            "name": "tags-test-subnet",
                            "cidr": "10.0.1.0/24",
                            "tags": ["subnet-tag"],
                            "hosts": [
                                {
                                    "hostname": "tags-test-host",
                                    "os": "debian_11",
                                    "spec": "tiny",
                                    "size": 8,
                                    "tags": ["host-tag"],
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        yaml_payload = yaml.dump(range_with_tags)

        # Post with YAML content type
        response = await auth_api_client.post(
            f"{BASE_ROUTE}/blueprints/ranges",
            content=yaml_payload,
            headers={"Content-Type": "application/yaml"},
        )
        assert response.status_code == status.HTTP_200_OK
        range_id = response.json()["id"]

        # Verify the blueprint was correctly stored
        response = await auth_api_client.get(
            f"{BASE_ROUTE}/blueprints/ranges/{range_id}"
        )
        assert response.status_code == status.HTTP_200_OK

        # Expected tags
        assert set(response.json()["vpcs"][0]["subnets"][0]["hosts"][0]["tags"]) == {
            "host-tag",
            "subnet-tag",
            "vpc-tag",
            "range-tag",
        }
