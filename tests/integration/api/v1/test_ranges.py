import pytest

from src.app.schemas.range_schemas import DeployedRangeSchema
from tests.integration.api.v1.config import PROVIDER_DEPLOYED_RANGE_PARAMS

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "parallel_deployed_ranges_for_provider",
    PROVIDER_DEPLOYED_RANGE_PARAMS,
    indirect=True,
)
@pytest.mark.asyncio(loop_scope="session")
async def test_one_all_deployed_range(
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


@pytest.mark.parametrize(
    "parallel_deployed_ranges_for_provider",
    PROVIDER_DEPLOYED_RANGE_PARAMS,
    indirect=True,
)
@pytest.mark.asyncio(loop_scope="session")
async def test_multi_deployed_range(
    multi_deployed_range: tuple[DeployedRangeSchema, str, str],
) -> None:
    """Test that the deployment was successful.

    If this test fails or has an error that means that the AWS
    one-all range deployment fixture failed. This means that the
    deployment logic in the application is broken.
    """
    range_info, email, password = multi_deployed_range

    # Check that we recieved auth info
    assert email
    assert password

    # Check that range deployed
    if not range_info:
        pytest.fail("Multi range failed to deploy!")
