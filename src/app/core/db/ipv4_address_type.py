from ipaddress import IPv4Address

from sqlalchemy import Dialect, types
from sqlalchemy.dialects.postgresql import INET


class IPv4AddressType(types.TypeDecorator[IPv4Address]):
    """Custom SQLAlchemy type to store an IPv4Address object as a INET string in PostgreSQL."""

    impl = INET  # Use PostgreSQL's INET type as the underlying type
    cache_ok = True  # Can be cached by the ORM

    def process_bind_param(
        self, value: IPv4Address | None, dialect: Dialect
    ) -> str | None:
        """Convert the Python IPv4Address object to its string representation before sending it to the database."""
        if value is None:
            return None
        if not isinstance(value, IPv4Address):
            msg = f"Expected IPv4Address, got {type(value).__name__}"
            raise TypeError(msg)
        return str(value)

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> IPv4Address | None:
        """Convert the string representation from the database back to an IPv4Address object when retrieving data."""
        if value is None:
            return None
        try:
            return IPv4Address(value)
        except ValueError as e:
            msg = f"Invalid IPv4 address string from database: {value}"
            raise ValueError(msg) from e
