import copy
import random
from datetime import datetime, timezone
from typing import Any

import pytest

from src.app.enums.providers import OpenLabsProvider
from src.app.enums.range_states import RangeState
from src.app.enums.regions import OpenLabsRegion
from src.app.utils.api_utils import get_api_base_route

# Pytest configuration
API_CLIENT_PARAMS = [
    pytest.param("client", marks=pytest.mark.unit, id="UNIT_TEST"),
    pytest.param(
        "integration_client", marks=pytest.mark.integration, id="INTEGRATION_TEST"
    ),
]

AUTH_API_CLIENT_PARAMS = [
    pytest.param("auth_client", marks=pytest.mark.unit, id="UNIT_TEST"),
    pytest.param(
        "auth_integration_client", marks=pytest.mark.integration, id="INTEGRATION_TEST"
    ),
]

COMBO_API_CLIENT_PARAMS = [
    pytest.param("client", "auth_client", marks=pytest.mark.unit, id="UNIT_TEST"),
    pytest.param(
        "integration_client",
        "auth_integration_client",
        marks=pytest.mark.integration,
        id="INTEGRATION_TEST",
    ),
]

# Base route
BASE_ROUTE = get_api_base_route(version=1)


# ==============================
#       Blueprint Payloads
# ==============================

# Valid payload for comparison
valid_blueprint_range_create_payload: dict[str, Any] = {
    "vpcs": [
        {
            "cidr": "192.168.0.0/16",
            "name": "example-vpc-1",
            "subnets": [
                {
                    "cidr": "192.168.1.0/24",
                    "name": "example-subnet-1",
                    "hosts": [
                        {
                            "hostname": "example-host-1",
                            "os": "debian_11",
                            "spec": "tiny",
                            "size": 8,
                            "tags": ["web", "linux"],
                        }
                    ],
                }
            ],
        }
    ],
    "description": "This is a test range blueprint.",
    "provider": "aws",
    "name": "example-range-1",
    "vnc": False,
    "vpn": False,
}

# Valid range payload for deployment
valid_range_deploy_payload: dict[str, Any] = {
    "name": "test-deploy-range-1",
    "description": "test range to deploy",
    "blueprint_id": str(random.randint(1, 100)),  # noqa: S311
    "region": OpenLabsRegion.US_EAST_1.value,
}

valid_blueprint_vpc_create_payload = copy.deepcopy(
    valid_blueprint_range_create_payload["vpcs"][0]
)
valid_blueprint_subnet_create_payload = copy.deepcopy(
    valid_blueprint_vpc_create_payload["subnets"][0]
)
valid_blueprint_host_create_payload = copy.deepcopy(
    valid_blueprint_subnet_create_payload["hosts"][0]
)

valid_blueprint_range_multi_create_payload: dict[str, Any] = {
    "vpcs": [
        {
            "cidr": "10.0.0.0/16",
            "name": "Dev VPC",  # NOTE: Spaces are intentionally included to test space handling in VPC names and prevent regression of parsing issues
            "subnets": [
                {
                    "cidr": "10.0.1.0/24",
                    "name": "dev-subnet-web",
                    "hosts": [
                        {
                            "hostname": "dev-web-01",
                            "os": "ubuntu_22",
                            "spec": "medium",
                            "size": 20,
                            "tags": ["web", "frontend", "ubuntu"],
                        },
                        {
                            "hostname": "dev-db-01",
                            "os": "suse_15",
                            "spec": "large",
                            "size": 50,
                            "tags": ["database", "backend", "rocky"],
                        },
                    ],
                },
                {
                    "cidr": "10.0.2.0/24",
                    "name": "dev-subnet-app",
                    "hosts": [
                        {
                            "hostname": "dev-app-01",
                            "os": "debian_11",
                            "spec": "medium",
                            "size": 30,
                            "tags": ["app", "linux"],
                        }
                    ],
                },
            ],
        },
        {
            "cidr": "172.16.0.0/16",
            "name": "prod-vpc",
            "subnets": [
                {
                    "cidr": "172.16.1.0/24",
                    "name": "Prod Subnet-DMZ",  # NOTE: Spaces are intentionally included to test space handling in subnet names and prevent regression of parsing issues
                    "hosts": [
                        {
                            "hostname": "prod-gateway-01",
                            "os": "kali",
                            "spec": "small",
                            "size": 32,
                            "tags": ["gateway", "security"],
                        }
                    ],
                }
            ],
        },
    ],
    "description": "Multi-VPC, Multi-Subnet, Multi-Host test blueprint for OpenLabs.",
    "provider": "aws",
    "name": "multi-env-test-range",
    "vnc": True,
    "vpn": True,
}

valid_blueprint_vpc_multi_create_payload: dict[str, Any] = copy.deepcopy(
    valid_blueprint_range_multi_create_payload["vpcs"][0]
)
valid_blueprint_subnet_multi_create_payload: dict[str, Any] = copy.deepcopy(
    valid_blueprint_vpc_multi_create_payload["subnets"][0]
)

# ==============================
#       Deployed Payloads
# ==============================

valid_deployed_range_header_data: dict[str, Any] = {
    "id": random.randint(1, 100),  # noqa: S311
    "name": "Fake Deployed Range",
    "description": "Description of fake deployed range for testing.",
    "date": datetime.now(tz=timezone.utc),
    "state": RangeState.ON,
    "region": OpenLabsRegion.US_EAST_1,
    "provider": OpenLabsProvider.AWS,
}

valid_deployed_range_data: dict[str, Any] = {
    "id": 999,
    "vpcs": [
        {
            "id": 10,
            "name": "production-vpc-main",
            "cidr": "10.100.0.0/16",
            "resource_id": "vpc-abc123xyz789",
            "subnets": [
                {
                    "id": 101,
                    "name": "prod-subnet-web-a",
                    "cidr": "10.100.1.0/24",
                    "resource_id": "subnet-def456uvw123",
                    "hosts": [
                        {
                            "id": 1001,
                            "hostname": "webserver-01",
                            "os": "debian_11",
                            "spec": "small",
                            "size": 30,
                            "tags": ["web", "frontend", "nginx"],
                            "resource_id": "i-hostabc111",
                            "ip_address": "10.100.1.10",
                        },
                        {
                            "id": 1002,
                            "hostname": "webserver-02",
                            "os": "debian_11",
                            "spec": "small",
                            "size": 30,
                            "tags": ["web", "frontend", "nginx"],
                            "resource_id": "i-hostabc222",
                            "ip_address": "10.100.1.11",
                        },
                    ],
                },
                {
                    "id": 102,
                    "name": "prod-subnet-app-a",
                    "cidr": "10.100.2.0/24",
                    "resource_id": "subnet-ghi789rst456",
                    "hosts": [
                        {
                            "id": 1003,
                            "hostname": "appserver-01",
                            "os": "ubuntu_22",
                            "spec": "medium",
                            "size": 50,
                            "tags": ["app", "backend", "api"],
                            "resource_id": "i-hostdef333",
                            "ip_address": "10.100.2.20",
                        }
                    ],
                },
                {
                    "id": 103,
                    "name": "prod-subnet-db-a",
                    "cidr": "10.100.3.0/24",
                    "resource_id": "subnet-jkl012pqr789",
                    "hosts": [
                        {
                            "id": 1004,
                            "hostname": "dbserver-01",
                            "os": "windows_2022",
                            "spec": "large",
                            "size": 80,
                            "tags": ["database", "sql", "critical"],
                            "resource_id": "i-hostghi444",
                            "ip_address": "10.100.3.30",
                        }
                    ],
                },
            ],
        },
        {
            "id": 20,
            "name": "staging-vpc",
            "cidr": "10.200.0.0/16",
            "resource_id": "vpc-lmn456opq012",
            "subnets": [
                {
                    "id": 201,
                    "name": "staging-subnet-main",
                    "cidr": "10.200.1.0/24",
                    "resource_id": "subnet-rst789uvw345",
                    "hosts": [
                        {
                            "id": 2001,
                            "hostname": "staging-app-01",
                            "os": "kali",
                            "spec": "medium",
                            "size": 60,
                            "tags": ["staging", "pentest"],
                            "resource_id": "i-hostjkl555",
                            "ip_address": "10.200.1.15",
                        }
                    ],
                }
            ],
        },
    ],
    "description": "Comprehensive deployed test range with corrected schema attributes.",
    "date": "2025-06-03T10:00:00Z",
    "readme": "# Test Deployed Range: Version 2\n\nThis data uses the updated and correct schema definitions for all nested objects.\n\n## Environment Overview:\n- **Production VPC**: Contains web, app, and database subnets.\n- **Staging VPC**: Contains a general-purpose subnet for testing.\n",
    "state_file": {
        "simplified_mock_state": "Test data placeholder - not a real Terraform state."
    },
    "state": "on",
    "region": "us_east_1",
    "jumpbox_resource_id": "i-jumpbox789012",
    "jumpbox_public_ip": "203.0.113.25",
    "range_private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDIfSjVkaDRtKNO\n... (rest of a mock SSH private key) ...\nhNUC8ZLe06edaNBX6N2jS9Wp3mk3JNGxQjagtrh9TGUrscedop4hCQABAoGALKe1\n-----END OPENSSH PRIVATE KEY-----",
    "provider": "aws",
    "name": "openlabs-deployed-test-v2",
    "vnc": True,
    "vpn": False,
}

valid_deployed_vpc_data: dict[str, Any] = copy.deepcopy(
    valid_deployed_range_data["vpcs"][0]
)

valid_deployed_subnet_data: dict[str, Any] = copy.deepcopy(
    valid_deployed_vpc_data["subnets"][0]
)

valid_deployed_host_data: dict[str, Any] = copy.deepcopy(
    valid_deployed_subnet_data["hosts"][0]
)

valid_range_private_key_data: dict[str, Any] = {
    "range_private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDIfSjVkaDRtKNO\n... (rest of a mock SSH private key) ...\nhNUC8ZLe06edaNBX6N2jS9Wp3mk3JNGxQjagtrh9TGUrscedop4hCQABAoGALKe1\n-----END OPENSSH PRIVATE KEY-----",
}

# ==============================
#      User/Auth Payloads
# ==============================

# Test user credentials
base_user_register_payload = {
    "email": "test@ufsit.club",
    "password": "password123",
    "name": "Test User",
}

base_user_login_payload = copy.deepcopy(base_user_register_payload)
base_user_login_payload.pop("name")

# Test data for password update
password_update_payload = {
    "current_password": "password123",
    "new_password": "newpassword123",
}

# Test data for AWS secrets
aws_secrets_payload: dict[str, Any] = {
    "provider": "aws",
    "credentials": {
        "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
        "aws_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    },
}

# Test data for Azure secrets
azure_secrets_payload = {
    "azure_client_id": "00000000-0000-0000-0000-000000000000",
    "azure_client_secret": "example-client-secret-value",
    "azure_tenant_id": "00000000-0000-0000-0000-000000000000",
    "azure_subscription_id": "00000000-0000-0000-0000-000000000000",
}
