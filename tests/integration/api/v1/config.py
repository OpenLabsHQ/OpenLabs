import pytest

ONE_ALL_DEPLOYED_RANGE_PARAMS = [
    pytest.param(
        "aws_one_all_deployed_range",
        marks=[pytest.mark.deploy, pytest.mark.aws],
        id="ONE_ALL_AWS_RANGE",
    )
]
