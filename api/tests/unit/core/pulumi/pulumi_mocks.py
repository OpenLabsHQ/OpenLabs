"""Mock objects for Pulumi testing."""
import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pulumi.automation as auto


class MockOutputValue:
    """Mock Pulumi OutputValue."""
    
    def __init__(self, value: Any, secret: bool = False):
        self.value = value
        self.secret = secret


class MockUpResult:
    """Mock Pulumi up result."""
    
    def __init__(self, outputs: Dict[str, Any], result: str = "succeeded"):
        self.outputs = {k: MockOutputValue(v) for k, v in outputs.items()}
        self.summary = MagicMock()
        self.summary.result = result


class MockDestroyResult:
    """Mock Pulumi destroy result."""
    
    def __init__(self, result: str = "succeeded"):
        self.summary = MagicMock()
        self.summary.result = result


class MockStack:
    """Mock Pulumi Stack for testing."""
    
    def __init__(self, stack_name: str, outputs: Dict[str, Any] = None):
        self.stack_name = stack_name
        self.workspace = MagicMock()
        self._outputs = outputs or {}
        self._state_data = {"version": 3, "deployment": {}}
        
    def set_config(self, key: str, value: auto.ConfigValue) -> None:
        """Mock set_config method."""
        pass
        
    def up(self, on_output=None) -> MockUpResult:
        """Mock up method."""
        return MockUpResult(self._outputs)
        
    def destroy(self, on_output=None) -> MockDestroyResult:
        """Mock destroy method."""
        return MockDestroyResult()
        
    def export_stack(self) -> Dict[str, Any]:
        """Mock export_stack method."""
        return self._state_data
        
    def import_stack(self, deployment: auto.Deployment) -> None:
        """Mock import_stack method."""
        self._state_data = deployment


def mock_create_or_select_stack(
    stack_name: str,
    project_name: str,
    program: callable,
    work_dir: str = None,
    outputs: Dict[str, Any] = None
) -> MockStack:
    """Mock create_or_select_stack function."""
    stack = MockStack(stack_name, outputs)
    
    # Mock workspace methods
    stack.workspace.install_plugin = MagicMock()
    
    return stack


# Standard test outputs that match the expected range structure
TEST_OUTPUTS = {
    "test-range-JumpboxInstanceId": "i-1234567890abcdef0",
    "test-range-JumpboxPublicIp": "203.0.113.12",
    "test-range-private-key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----",
    "test-range-vpc1-resource-id": "vpc-12345678",
    "test-range-vpc1-subnet1-resource-id": "subnet-12345678",
    "test-range-vpc1-subnet1-web-server-resource-id": "i-0987654321fedcba0",
    "test-range-vpc1-subnet1-web-server-private-ip": "10.0.1.10",
}