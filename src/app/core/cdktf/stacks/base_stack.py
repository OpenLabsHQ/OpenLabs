from pathlib import Path

from cdktf import LocalBackend, TerraformStack
from constructs import Construct

from ....enums.regions import OpenLabsRegion
from ....schemas.range_schemas import BlueprintRangeSchema


class AbstractBaseStack(TerraformStack):
    """A 'pseudo-abstract' base class that extends TerraformStack.

    Simulates abstract methods by raising a NotImplementedError for the
    "psuedo-abstract" functions.
    """

    def __init__(  # noqa: PLR0913
        self,
        scope: Construct,
        blueprint_range: BlueprintRangeSchema,
        cdktf_id: str,
        cdktf_dir: str,
        region: OpenLabsRegion,
        range_name: str,
    ) -> None:
        """Initialize AWS terraform stack.

        Args:
        ----
            self (AWSStack): AWSStack class.
            scope (Construct): CDKTF app.
            blueprint_range: Blueprint range object used for create all necessary resources to deploy.
            cdktf_id (str): Unique ID for CDKTF app.
            cdktf_dir (str): Directory location for all terraform files.
            region (OpenLabsRegion): Supported OpenLabs cloud region.
            range_name (str): Name of range to deploy.

        Returns:
        -------
            None

        """
        super().__init__(scope, cdktf_id)

        LocalBackend(
            self,
            path=str(
                Path(f"{cdktf_dir}/stacks/{cdktf_id}/terraform.{cdktf_id}.tfstate")
            ),
        )

        # Will raise NotImplementedError when not-overriden by child class
        parts = cdktf_id.split("-")
        uuid_str = "-".join(parts[-5:])
        range_name = f"{range_name}-{uuid_str}"
        self.build_resources(
            blueprint_range=blueprint_range,
            region=region,
            cdktf_id=cdktf_id,
            range_name=range_name,
        )

    def build_resources(
        self,
        blueprint_range: BlueprintRangeSchema,
        region: OpenLabsRegion,
        cdktf_id: str,
        range_name: str,
    ) -> None:
        """'Psuedo-abtract' method to build the CDKTF resources.

        Args:
        ----
            blueprint_range (BlueprintRangeSchema): Blueprint range object to build terraform for.
            region (OpenLabsRegion): Support OpenLabs cloud region.
            cdktf_id (str): Unique ID for each deployment to use for Terraform resource naming.
            range_name (str): Name of range to deploy.

        Returns:
        -------
            None

        """
        msg = "Subclasses of AbstractBaseStack must implement build_resources()."
        raise NotImplementedError(msg)
