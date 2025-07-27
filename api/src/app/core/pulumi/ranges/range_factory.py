import logging
from typing import Any, ClassVar, Type

from ....enums.providers import OpenLabsProvider
from ....enums.regions import OpenLabsRegion
from ....schemas.range_schemas import BlueprintRangeSchema, DeployedRangeSchema
from ....schemas.secret_schema import SecretSchema
from .aws_range import AWSPulumiRange
from .base_range import AbstractBasePulumiRange

# Configure logging
logger = logging.getLogger(__name__)


class PulumiRangeFactory:
    """Create Pulumi range objects."""

    _registry: ClassVar[dict[OpenLabsProvider, Type[AbstractBasePulumiRange]]] = {
        OpenLabsProvider.AWS: AWSPulumiRange,
    }

    @classmethod
    def create_range(  # noqa: PLR0913
        cls,
        name: str,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        region: OpenLabsRegion,
        secrets: SecretSchema,
        description: str | None,
        state_data: dict[str, Any] | None = None,
    ) -> AbstractBasePulumiRange:
        """Create Pulumi range object.

        Args:
        ----
            cls (PulumiRangeFactory): The PulumiRangeFactory class.
            name (str): Name of the range to deploy.
            range_obj (BlueprintRangeSchema | DeployedRangeSchema): The range object used to manipulate provider resources.
            region (OpenLabsRegion): Supported cloud region.
            secrets (SecretSchema): Cloud account secrets to use for deploying via Pulumi.
            description (str | None): Description of the range.
            state_data (dict[str, Any]): The Pulumi state data of the deployed resources.

        Returns:
        -------
            AbstractBasePulumiRange: Pulumi range object that can be deployed.

        """
        range_class = cls._registry.get(range_obj.provider)

        if range_class is None:
            msg = f"Failed to build range object. Non-existent provider given: {range_obj.provider}"
            logger.error(msg)
            raise ValueError(msg)

        if not description:
            logger.info("Range has no description, defaulting to empty string.")
            description = ""

        return range_class(
            name=name,
            range_obj=range_obj,
            region=region,
            secrets=secrets,
            description=description,
            state_data=state_data,
        )