import re

from .id_utils import generate_short_uid


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


class CloudResourceNamer:
    """Utility to streamline and standardize cloud resource naming."""

    # Convention configuration
    PREFIX = "ol"
    MAX_DEPLOYMENT_ID_LEN = 10
    TRUNCATED_RANGE_NAME_LEN = 15
    SHORT_UID_LEN = 10
    MIN_RESOURCE_NAME_LEN = (
        5  # Reserve at least 5 chars for the resource name for readability.
    )

    def __init__(self, deployment_id: str, range_name: str, max_len: int = 63) -> None:
        """Configure the cloud namer utility.

        Args:
        ----
            deployment_id: A unique identifier for the deployment (max 10 chars).
            range_name: The name of the range containing the resources to be named.
            max_len: The maximum allowed length for names. Defaults to 63 a safe default for most major cloud providers.

        """
        if not deployment_id:
            msg = "Deployment ID cannot be empty."
            raise ValueError(msg)

        if len(deployment_id) > self.MAX_DEPLOYMENT_ID_LEN:
            msg = f"Deployment ID cannot be longer than {self.MAX_DEPLOYMENT_ID_LEN} characters."
            raise ValueError(msg)

        if not range_name:
            msg = "Range name cannot be empty."
            raise ValueError(msg)

        # Store values in "private" attributes
        self._deployment_id = deployment_id
        self._range_name = range_name
        self.max_len = max_len

    @property
    def deployment_id(self) -> str:
        """The unique identifier for the deployment (read-only)."""
        return self._deployment_id

    @property
    def range_name(self) -> str:
        """The name of the range containing the resources (read-only)."""
        return self._range_name

    def gen_cloud_resource_name(
        self,
        resource_name: str,
        *,  # Make sure unique is a kwarg for clarity
        unique: bool,
    ) -> str:
        """Generate a standard length-constrained cloud resource name.

        The final format is: "ol-{deployment_id}-{range_name}-{resource_name}-{uid}"

        This format is designed to make it easy for users to identify resources and
        provider a standard format across cloud providers.

        Args:
            resource_name: The name of the specific resource.
            unique: If True, append a unique uid to ensure the name is unique across an entire cloud account.

        Returns:
            A formatted and validated cloud resource name string.

        """
        # Normalize all user-provided parts to ensure they are valid for cloud resource names
        norm_deployment_id = normalize_name(self.deployment_id)
        norm_range_name = normalize_name(self.range_name)
        norm_resource_name = normalize_name(resource_name)

        # Truncate the range name to its allowed length to keep it from dominating the name
        truncated_range_name = norm_range_name[: self.TRUNCATED_RANGE_NAME_LEN].strip(
            "-"
        )

        # The uid provides uniqueness for resources whose names might otherwise collide after normalization
        short_uid = generate_short_uid()[: self.SHORT_UID_LEN] if unique else ""

        # Calculate Available Space for the Resource Name
        fixed_parts_len = (
            len(self.PREFIX) + len(norm_deployment_id) + len(truncated_range_name)
        )
        if unique:
            fixed_parts_len += len(short_uid)

        # Calculate the number of hyphens needed. A name with 5 parts (e.g., prefix, id, range, resource, uid)
        # will require 4 hyphens.
        num_hyphens = 3 + (1 if unique else 0)

        # The remaining space is what's available for the resource name.
        available_len = self.max_len - fixed_parts_len - num_hyphens

        if available_len < self.MIN_RESOURCE_NAME_LEN:
            required = self.max_len - available_len + self.MIN_RESOURCE_NAME_LEN
            msg = (
                f"Cannot generate a name with max_len={self.max_len}. "
                f"Not enough space for the resource name after accommodating other components. "
                f"Required space is at least {required}."
            )
            raise ValueError(msg)

        # Truncate the resource name to the exact calculated available length.
        truncated_resource_name = norm_resource_name[:available_len].strip("-")

        # Build final name
        name_parts = [
            self.PREFIX,
            norm_deployment_id,
            truncated_range_name,
            truncated_resource_name,
        ]
        if unique:
            name_parts.append(short_uid)

        # User a join in case a part becomes empty after normalization
        # and formatting changes
        return "-".join(part for part in name_parts if part)
