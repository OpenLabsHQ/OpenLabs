import copy
import uuid

import pytest

from src.app.core.cdktf.ranges.aws_range import AWSRange
from src.app.core.cdktf.ranges.range_factory import RangeFactory
from src.app.enums.providers import OpenLabsProvider
from src.app.enums.regions import OpenLabsRegion
from src.app.schemas.secret_schema import SecretSchema
from src.app.schemas.user_schema import UserID
from tests.unit.core.cdktf.config import one_all_template


def test_range_factory_non_existent_range_type() -> None:
    """Test that RangeFactory.create_range() raises a ValueError when invalid provider is provided."""
    # Set provider to non-existent provider
    bad_provider_template = copy.deepcopy(one_all_template)

    # Ignore invalid string assignment since we are triggering a ValueError
    bad_provider_template.provider = "FakeProvider"  # type: ignore

    with pytest.raises(ValueError):
        _ = RangeFactory.create_range(
            id=uuid.uuid4(),
            name="test-range",
            template=bad_provider_template,
            region=OpenLabsRegion.US_EAST_1,
            owner_id=UserID(id=uuid.uuid4()),
            secrets=SecretSchema(),
            state_file=None,
        )


def test_range_factory_build_aws_range() -> None:
    """Test that RangeFactory can build an AWSRange."""
    # Set template to AWS
    aws_template = copy.deepcopy(one_all_template)
    aws_template.provider = OpenLabsProvider.AWS

    created_range = RangeFactory.create_range(
        id=uuid.uuid4(),
        name="test-range",
        template=aws_template,
        region=OpenLabsRegion.US_EAST_1,
        owner_id=UserID(id=uuid.uuid4()),
        secrets=SecretSchema(),
        state_file=None,
    )

    assert type(created_range) is AWSRange
