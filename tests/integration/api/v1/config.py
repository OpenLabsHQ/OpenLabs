import pytest

from src.app.enums.providers import OpenLabsProvider
from tests.deploy_test_utils import RangeType

PROVIDER_RANGE_PARAMS = [
    pytest.param(
        OpenLabsProvider.AWS,
        marks=[pytest.mark.deploy, pytest.mark.aws],
    )
]

RANGE_TYPE_PARAMS = [
    pytest.param(
        RangeType.ONE_ALL,
        marks=[
            pytest.mark.deploy,
            pytest.mark.skip(
                reason="Skipping ONE_ALL test range until ARQ jobs implemented."
            ),
        ],
    ),
    pytest.param(RangeType.MULTI, marks=[pytest.mark.deploy]),
]
