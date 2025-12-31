import tempfile


def create_pulumi_dir() -> str:
    """Create temp dir for Pulumi workspaces."""
    # /tmp/.openlabs-pulumi-XXXX
    return tempfile.mkdtemp(prefix=".openlabs-pulumi-")
