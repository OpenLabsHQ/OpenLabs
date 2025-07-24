from pathlib import Path

from cdktf import LocalBackend, TerraformStack
from constructs import Construct

from ....enums.regions import OpenLabsRegion
from ....schemas.range_schemas import BlueprintRangeSchema, DeployedRangeSchema


class AbstractBaseStack(TerraformStack):
    """A 'pseudo-abstract' base class that extends TerraformStack.

    Simulates abstract methods by raising a NotImplementedError for the
    "psuedo-abstract" functions.
    """

    def __init__(  # noqa: PLR0913
        self,
        scope: Construct,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        cdktf_id: str,
        cdktf_dir: str,
        region: OpenLabsRegion,
        range_name: str,
        deployment_id: str,
    ) -> None:
        """Initialize an abstract terraform stack.

        Args:
        ----
            self (AWSStack): AWSStack class.
            scope (Construct): CDKTF app.
            range_obj (BlueprintRangeSchema | DeployedRangeSchema): Range object used to manipulate provider resources.
            cdktf_id (str): Unique ID for CDKTF app.
            cdktf_dir (str): Directory location for all terraform files.
            region (OpenLabsRegion): Supported OpenLabs cloud region.
            range_name (str): Name of range to deploy.
            deployment_id (str): ID unique to the deployment.

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

        self.build_resources(
            range_obj=range_obj,
            region=region,
            range_name=range_name,
            deployment_id=deployment_id,
        )

    def build_resources(
        self,
        range_obj: BlueprintRangeSchema | DeployedRangeSchema,
        region: OpenLabsRegion,
        range_name: str,
        deployment_id: str,
    ) -> None:
        """'Psuedo-abtract' method to build the CDKTF resources.

        Args:
        ----
            range_obj (BlueprintRangeSchema | DeployedRangeSchema): Range object used to manipulate provider resources.
            region (OpenLabsRegion): Support OpenLabs cloud region.
            range_name (str): Name of range to deploy.
            deployment_id (str): ID unique to the deployment.

        Returns:
        -------
            None

        """
        msg = "Subclasses of AbstractBaseStack must implement build_resources()."
        raise NotImplementedError(msg)
