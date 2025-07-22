def normalize_resource_name(name: str) -> str:
    """Remove problematic characters from user-supplied resource names."""
    return name.strip().replace(" ", "")
