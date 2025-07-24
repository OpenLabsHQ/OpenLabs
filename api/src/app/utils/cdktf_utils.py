import tempfile
from collections import Counter, defaultdict

from .name_utils import normalize_name


def create_cdktf_dir() -> str:
    """Create temp dir for CDKTF."""
    # /tmp/.openlabs-cdktf-XXXX
    return tempfile.mkdtemp(prefix=".openlabs-cdktf-")


def gen_resource_logical_ids(resource_names: list[str]) -> dict[str, str]:
    """Generate deterministic, normalized, and unique logical IDs from a list of resource names.

    This function handles collisions that occur after normalization by appending
    a numeric suffix.

    Args:
        resource_names: A list of user-supplied resource names.

    Returns:
        A dictionary mapping each original resource name to its unique logical ID.

    Example:
        >>> names = ["Web Server", "Database", "web-server", "Auth Service"]
        >>> gen_resource_logical_ids(names)
        {
            'Auth Service': 'auth-service',
            'Database': 'database',
            'Web Server': 'web-server',
            'web-server': 'web-server-1'
        }

    """
    if len(set(resource_names)) != len(resource_names):
        counts = Counter(resource_names)
        duplicates = [name for name, count in counts.items() if count > 1]
        msg = f"Input list contains duplicate names: {', '.join(duplicates)}"
        raise ValueError(msg)

    logical_ids: dict[str, str] = {}
    seen_counts: defaultdict[str, int] = defaultdict(int)

    # Sorted to ensure deterministic ID generation
    sorted_names = sorted(resource_names)

    for name in sorted_names:
        base_id = normalize_name(name)

        # The first time we see a base_id, its ID is just itself
        # each time we see it again we add a suffix
        if seen_counts[base_id] > 0:
            logical_id = f"{base_id}-{seen_counts[base_id]}"
        else:
            logical_id = base_id

        logical_ids[name] = logical_id

        # Increment the count for the next potential collision
        seen_counts[base_id] += 1

    return logical_ids
