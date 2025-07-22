import tempfile


def create_cdktf_dir() -> str:
    """Create temp dir for CDKTF."""
    # /tmp/.openlabs-cdktf-XXXX
    return tempfile.mkdtemp(prefix=".openlabs-cdktf-")
