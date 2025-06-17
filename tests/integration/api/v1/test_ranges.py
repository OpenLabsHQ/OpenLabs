import pytest

from src.app.schemas.range_schemas import DeployedRangeSchema
from tests.integration.api.v1.config import ONE_ALL_DEPLOYED_RANGE_PARAMS

pytestmark = pytest.mark.integration


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "one_all_deployed_range",
    ONE_ALL_DEPLOYED_RANGE_PARAMS,
    indirect=True,
)
async def test_aws_one_all_deployed_range(
    one_all_deployed_range: tuple[DeployedRangeSchema, str, str],
) -> None:
    """Test that the deployment was successful.

    If this test fails or has an error that means that the AWS
    one-all range deployment fixture failed. This means that the
    deployment logic in the application is broken.
    """
    range_info, email, password = one_all_deployed_range

    # Check that we recieved auth info
    assert email
    assert password

    # Check that range deployed
    if not range_info:
        pytest.fail("One-all range failed to deploy!")
