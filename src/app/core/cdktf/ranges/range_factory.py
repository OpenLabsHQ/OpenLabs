import logging
from typing import Any, ClassVar, Type

from ....enums.providers import OpenLabsProvider
from ....enums.regions import OpenLabsRegion
from ....schemas.range_schemas import BlueprintRangeSchema, DeployedRangeSchema
from ....schemas.secret_schema import SecretSchema
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
    def create_range(
        cls,
        name: str,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        region: OpenLabsRegion,
        secrets: SecretSchema,
        description: str,
        state_file: dict[str, Any] | None = None,
    ) -> AbstractBaseRange:
        """Create range object.

        **Note:** This function accepts a creation schema as the OpenLabs resource ID is not required
        for terraform.

        Args:
        ----
            cls (RangeFactory): The RangeFactory class.
            name (str): Name of the range to deploy.
            range_obj (BlueprintRangeSchema | DeployedRangeSchema): The range object used to manipulate provider resources.
            region (OpenLabsRegion): Supported cloud region.
            secrets (SecretSchema): Cloud account secrets to use for deploying via terraform.
            state_file (dict[str, Any]): The statefile of the deployed resources.

        Returns:
        -------
            AbstractBaseRange: Cdktf range object that can be deployed.

        """
        range_class = cls._registry.get(range_obj.provider)

        if range_class is None:
            msg = f"Failed to build range object. Non-existent provider given: {range_obj.provider}"
            logger.error(msg)
            raise ValueError(msg)

        return range_class(
            name=name,
            range_obj=range_obj,
            region=region,
            secrets=secrets,
            description=description,
            state_file=state_file,
        )
