import logging
from typing import Any, ClassVar, Type

from ....enums.providers import OpenLabsProvider
from ....enums.regions import OpenLabsRegion
from ....schemas.range_schemas import BlueprintRangeSchema
from ....schemas.secret_schema import SecretSchema
from ....schemas.user_schema import UserID
from .aws_range import AWSRange
from .base_range import AbstractBaseRange

# Configure logging
logger = logging.getLogger(__name__)


class RangeFactory:
    """Create range objects."""

    _registry: ClassVar[dict[OpenLabsProvider, Type[AbstractBaseRange]]] = {
        OpenLabsProvider.AWS: AWSRange,
    }

    @classmethod
    def create_range(  # noqa: PLR0913
        cls,
        name: str,
        blueprint_range: BlueprintRangeSchema,
        region: OpenLabsRegion,
        owner_id: UserID,
        secrets: SecretSchema,
        state_file: dict[str, Any] | None = None,
    ) -> AbstractBaseRange:
        """Create range object.

        Args:
        ----
            cls (RangeFactory class): The RangeFactory class.
            name (str): Name of the range to deploy
            blueprint_range (BlueprintRangeSchema): The range blueprint object.
            region (OpenLabsRegion): Supported cloud region.
            owner_id (UserID): The ID of the user deploying range.
            secrets (SecretSchema): Cloud account secrets to use for deploying via terraform
            state_file (dict[str, Any]): The statefile of the deployed resources

        Returns:
        -------
            AbstractBaseRange: Cdktf range object that can be deployed.

        """
        range_class = cls._registry.get(blueprint_range.provider)

        if range_class is None:
            msg = f"Failed to build range object. Non-existent provider given: {blueprint_range.provider}"
            logger.error(msg)
            raise ValueError(msg)

        return range_class(
            name=name,
            blueprint_range=blueprint_range,
            region=region,
            owner_id=owner_id,
            secrets=secrets,
            state_file=state_file,
        )
