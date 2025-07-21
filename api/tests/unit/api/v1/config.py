import copy
import random
from datetime import datetime, timezone
from typing import Any

from src.app.enums.job_status import OpenLabsJobStatus
from src.app.enums.providers import OpenLabsProvider
from src.app.enums.range_states import RangeState
from src.app.enums.regions import OpenLabsRegion
from tests.common.api.v1.config import (
    valid_blueprint_range_create_payload,
    valid_blueprint_range_multi_create_payload,
)

# Base route
BASE_ROUTE = "/api/v1"


# ==============================
#       Blueprint Payloads
# ==============================

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
aws_secrets_payload = {
    "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
    "aws_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
}

# Test data for Azure secrets
azure_secrets_payload = {
    "azure_client_id": "00000000-0000-0000-0000-000000000000",
    "azure_client_secret": "example-client-secret-value",
    "azure_tenant_id": "00000000-0000-0000-0000-000000000000",
    "azure_subscription_id": "00000000-0000-0000-0000-000000000000",
}
# ==============================
#         Job Payloads
# ==============================

queued_job_payload = {
    "arq_job_id": "e8ce953f4f6c4a7c884a9afe8112d31f",
    "job_name": "deploy_range",
    "job_try": None,
    "enqueue_time": "2025-07-02T10:22:42.407000Z",
    "start_time": None,
    "finish_time": None,
    "status": "queued",
    "result": None,
    "error_message": None,
    "id": 1,
}

in_progress_job_payload = {
    "arq_job_id": "e8ce953f4f6c4a7c884a9afe8112d31f",
    "job_name": "deploy_range",
    "job_try": 1,
    "enqueue_time": "2025-07-02T10:22:42.407000Z",
    "start_time": "2025-07-02T10:22:42.814805Z",
    "finish_time": None,
    "status": "in_progress",
    "result": None,
    "error_message": None,
    "id": 1,
}

complete_job_payload = {
    "arq_job_id": "e8ce953f4f6c4a7c884a9afe8112d31f",
    "job_name": "deploy_range",
    "job_try": 1,
    "enqueue_time": "2025-07-02T10:22:42.407000Z",
    "start_time": "2025-07-02T10:22:42.814805Z",
    "finish_time": "2025-07-02T10:24:49.224000Z",
    "status": "complete",
    "result": {
        "id": 1,
        "vnc": False,
        "vpn": False,
        "date": "2025-07-02T10:24:49.169656Z",
        "name": "Test-ARQ-Range-v1",
        "state": "on",
        "region": "us_east_1",
        "provider": "aws",
        "description": "This is my test range.",
    },
    "error_message": None,
    "id": 1,
}

# Updates to completed job payload to
# create a failed job payload
failed_job_updates = {
    "result": None,
    "status": OpenLabsJobStatus.FAILED.value,
    "error_message": "Mock error message.",
}
failed_job_payload = copy.deepcopy(complete_job_payload)
failed_job_payload.update(failed_job_updates)
