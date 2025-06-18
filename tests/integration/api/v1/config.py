import pytest

from src.app.enums.providers import OpenLabsProvider

PROVIDER_DEPLOYED_RANGE_PARAMS = [
    pytest.param(
        OpenLabsProvider.AWS,
        marks=[pytest.mark.deploy, pytest.mark.aws],
        id=OpenLabsProvider.AWS.value.upper(),
    )
]
