import copy
from typing import Any

from src.app.enums.job_status import OpenLabsJobStatus

# Import all common test data
from tests.common.api.v1.config import *  # noqa: F403, F401

# Override BASE_ROUTE for unit tests (common uses dynamic route)
BASE_ROUTE = "/api/v1"

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

# Override specific payloads that need unit-test specific values
valid_blueprint_range_multi_create_payload: dict[str, Any] = {
    "vpcs": [
        {
            "cidr": "10.0.0.0/16",
            "name": "dev-vpc",  # Unit tests use simpler names without spaces
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
                    "name": "prod-subnet-dmz",  # Unit tests use simpler names without spaces
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