def normalize_name(name: str) -> str:
    """Remove problematic characters from user-supplied names."""
    return name.strip().replace(" ", "")
