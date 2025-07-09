from ipaddress import IPv4Network

from src.app.enums.operating_systems import OpenLabsOS
from src.app.validators.network import (
    is_valid_disk_size,
    is_valid_hostname,
    max_num_hosts_in_subnet,
)


def test_valid_hostnames() -> None:
    """Test valid hostnames."""
    valid_hostnames: list[str] = [
        "example.com",
        "sub.example.com",
        "localhost",
        "my-site123.org",
        "a.co",
        "example.co.uk",
        "example.com.",  # With trailing dot
        "xn--d1acpjx3f.xn--p1ai",  # Punycode for international domains
        "example",
        "example-host-1",
    ]

    for hostname in valid_hostnames:
        assert is_valid_hostname(hostname)


def test_invalid_hostnames() -> None:
    """Test invalid hostnames."""
    invalid_hostnames: list[str] = [
        "",  # Empty string
        "-example.com",  # Starts with a hyphen
        "example-.com",  # Ends with a hyphen
        "exa_mple.com",  # Underscore is invalid
        "example..com",  # Double dot
        "123.456.789.0",  # All numeric TLD
        "example.123",  # Numeric TLD
        "a" * 64 + ".com",  # Label too long (>63)
        "a" * 254 + ".com",  # Hostname too long (>253)
        "example!.com",  # Special character '!' invalid
    ]

    for hostname in invalid_hostnames:
        assert not is_valid_hostname(hostname)


def test_hostname_with_trailing_dot() -> None:
    """Test hostname with a trailing dot."""
    assert is_valid_hostname("example.com.")
    assert not is_valid_hostname("example..com.")


def test_hostname_length_limits() -> None:
    """Test hostname length limits."""
    valid_hostname = ".".join(
        ["a" * 63] * 4
    )  # Total length = 63*4 + 3 dots = 255 (valid without trailing dot)
    invalid_hostname = valid_hostname + "a"

    assert is_valid_hostname(valid_hostname[:-2])
    assert not is_valid_hostname(invalid_hostname)


def test_numeric_tld() -> None:
    """Test hostnames with numeric TLDs."""
    assert not is_valid_hostname("example.123")
    assert is_valid_hostname("123.example")


def test_valid_host_size() -> None:
    """Test host disk size minimums."""
    assert is_valid_disk_size(OpenLabsOS.DEBIAN_11, 10)
    assert is_valid_disk_size(OpenLabsOS.WINDOWS_2016, 32)
    assert not is_valid_disk_size(OpenLabsOS.WINDOWS_2016, 10)


def test_max_number_of_hosts_in_subnet() -> None:
    """Test max number of hosts in subnet."""
    standard_24_subnet = IPv4Network("192.168.1.0/24")
    max_hosts_in_24_subnet = 256
    max_usable_hosts_in_24_subnet = max_hosts_in_24_subnet - 5
    assert max_num_hosts_in_subnet(standard_24_subnet) == max_usable_hosts_in_24_subnet

    standard_25_subnet = IPv4Network("192.168.1.0/25")
    max_usable_hosts_in_25_subnet = (max_hosts_in_24_subnet / 2) - 5
    assert max_num_hosts_in_subnet(standard_25_subnet) == max_usable_hosts_in_25_subnet

    standard_31_subnet = IPv4Network("192.168.1.0/31")
    max_hosts_31_subnet = 0
    assert max_num_hosts_in_subnet(standard_31_subnet) == max_hosts_31_subnet
