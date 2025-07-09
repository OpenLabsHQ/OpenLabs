from unittest.mock import Mock

import pytest
from sqlalchemy import Dialect

from src.app.core.db.ipv4_address_type import IPv4AddressType


def test_process_bind_param_invalid_type_ipv4_address_type() -> None:
    """Verify that process_bind_param raises a TypeError when the provided value is not an IPv4Address."""
    custom_type = IPv4AddressType()
    mock_dialect = Mock(spec=Dialect)
    invalid_value = "this-is-not-an-ip-object"

    # Must ignore types since this triggers a type error
    with pytest.raises(TypeError) as exc_info:
        custom_type.process_bind_param(invalid_value, mock_dialect)  # type: ignore

    assert "expected ipv4address" in str(exc_info.value).lower()


def test_process_result_value_invalid_ipv4_address_type() -> None:
    """Verify that process_result_value raises a ValueError when the string from the database is not a valid IPv4 address."""
    custom_type = IPv4AddressType()
    mock_dialect = Mock(spec=Dialect)

    invalid_value = "this-is-not-an-ip-object"

    with pytest.raises(ValueError) as exc_info:
        custom_type.process_result_value(invalid_value, mock_dialect)

    assert "invalid ipv4 address string" in str(exc_info.value).lower()
