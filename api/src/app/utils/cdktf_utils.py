import tempfile


def create_cdktf_dir() -> str:
    """Create temp dir for CDKTF."""
    # /tmp/.openlabs-cdktf-XXXX
    return tempfile.mkdtemp(prefix=".openlabs-cdktf-")


def normalize_resource_name(name: str) -> str:
    """Remove problematic characters from user-supplied resource names."""
    return name.strip().replace(" ", "")
