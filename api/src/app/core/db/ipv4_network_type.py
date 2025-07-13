from ipaddress import IPv4Network

from sqlalchemy import Dialect, types
from sqlalchemy.dialects.postgresql import CIDR


class IPv4NetworkType(types.TypeDecorator[IPv4Network]):
    """Custom SQLAlchemy type to store an IPv4Network object as a CIDR string in PostgreSQL."""

    impl = CIDR  # Use PostgreSQL's CIDR type as the underlying type
    cache_ok = True  # Can be cached by the ORM

    def process_bind_param(
        self, value: IPv4Network | None, dialect: Dialect
    ) -> str | None:
        """Convert the Python IPv4Network object to its string representation before sending it to the database."""
        if value is None:
            return None
        if not isinstance(value, IPv4Network):
            msg = f"Expected IPv4Network, got {type(value).__name__}"
            raise TypeError(msg)
        return str(value)

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> IPv4Network | None:
        """Convert the string representation from the database back to an IPv4Network object when retrieving data."""
        if value is None:
            return None
        try:
            return IPv4Network(value, strict=True)
        except ValueError as e:
            msg = f"Invalid CIDR string from database: {value}"
            raise ValueError(msg) from e
