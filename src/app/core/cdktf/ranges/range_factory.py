import logging
import uuid
from typing import ClassVar, Type

from ....enums.providers import OpenLabsProvider
from ....enums.regions import OpenLabsRegion
from ....schemas.secret_schema import SecretSchema
from ....schemas.template_range_schema import TemplateRangeSchema
from ....schemas.user_schema import UserID
from .aws_range import AWSRange
from .base_range import CdktfBaseRange

# from .azure_range import AzureRange
# from .gcp_range import GCPRange

# Configure logging
logger = logging.getLogger(__name__)


class RangeFactory:
    """Create range objects."""

    _registry: ClassVar[dict[OpenLabsProvider, Type[CdktfBaseRange]]] = {
        OpenLabsProvider.AWS: AWSRange,
        # OpenLabsProvider.AZURE: AzureRange,
        # OpenLabsProvider.GCP: GCPRange
    }

    @classmethod
    def create_range(
        cls,
        deployed_range_id: uuid.UUID,
        template_range: TemplateRangeSchema,
        region: OpenLabsRegion,
        owner_id: UserID,
        secrets: SecretSchema,
    ) -> CdktfBaseRange:
        """Create range object.

        Args:
        ----
            cls (RangeFactory class): The RangeFactory class.
            deployed_range_id (uuid.UUID): The UUID for the deployed range object.
            template_range (TemplateRangeSchema): The range template object.
            region (OpenLabsRegion): Supported cloud region.
            owner_id (UserID): The ID of the user deploying range.
            secrets (SecretSchema): Cloud account secrets to use for deploying via terraform

        Returns:
        -------
            CdktfBaseRange: Cdktf range object that can be deployed.

        """
        range_class = cls._registry.get(template_range.provider)

        if range_class is None:
            msg = f"Failed to build range object. Non-existent provider given: {template_range.provider}"
            logger.error(msg)
            raise ValueError(msg)

        return range_class(
            range_id=deployed_range_id,
            template=template_range,
            region=region,
            owner_id=owner_id,
            secrets=secrets,
        )
