import pytest

ONE_ALL_DEPLOYED_RANGE_PARAMS = [
    pytest.param(
        "aws",
        marks=[pytest.mark.deploy, pytest.mark.aws],
        id="AWS",
    )
]
