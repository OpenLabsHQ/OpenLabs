from unittest.mock import Mock

import pytest
from sqlalchemy import Dialect

from src.app.core.db.ipv4_network_type import IPv4NetworkType


def test_process_bind_param_invalid_type_ipv4_network_type() -> None:
    """Verify that process_bind_param raises a TypeError when the provided value is not an IPv4Network."""
    custom_type = IPv4NetworkType()
    mock_dialect = Mock(spec=Dialect)
    invalid_value = "this-is-not-an-ip-object"

    # Must ignore types since this triggers a type error
    with pytest.raises(TypeError) as exc_info:
        custom_type.process_bind_param(invalid_value, mock_dialect)  # type: ignore

    assert "expected ipv4network" in str(exc_info.value).lower()


def test_process_result_value_invalid_cidr_ipv4_network_type() -> None:
    """Verify that process_result_value raises a ValueError when the string from the database is not a valid CIDR network."""
    custom_type = IPv4NetworkType()
    mock_dialect = Mock(spec=Dialect)

    # This is invalid since we are using strict=True
    # which expects ONLY network addresses
    invalid_cidr_string = "192.168.1.1/24"

    with pytest.raises(ValueError) as exc_info:
        custom_type.process_result_value(invalid_cidr_string, mock_dialect)

    assert "invalid cidr string" in str(exc_info.value).lower()
