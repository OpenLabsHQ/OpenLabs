import re


def normalize_name(name: str) -> str:
    """Remove problematic characters from user-supplied names for cloud deployments while maintaining readability.

    Args:
        name: Name to normalize.

    Returns:
        Name normalized to a safe kebab case version.

    """
    normalized_name = name.lower()

    # Strip out disallowed characters
    normalized_name = re.sub(r"[^a-z0-9\-]", "-", normalized_name)

    # Remove extra hyphens
    normalized_name = re.sub(r"-+", "-", normalized_name)
    normalized_name = normalized_name.strip("-")

    if not normalized_name:
        msg = f"Name is empty after normalization. Original name: '{name}'"
        raise ValueError(msg)

    return normalized_name
