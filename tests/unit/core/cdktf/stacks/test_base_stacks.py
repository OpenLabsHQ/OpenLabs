import pytest
from cdktf import App

from src.app.core.cdktf.stacks.base_stack import AbstractBaseStack
from src.app.enums.regions import OpenLabsRegion
from tests.unit.core.cdktf.config import one_all_blueprint

pytestmark = pytest.mark.unit


def test_abstract_stack_creation_not_implemented_error() -> None:
    """Ensure that instantiating the AbstractBaseStack raises NontImplementedError."""
    with pytest.raises(NotImplementedError):
        AbstractBaseStack(
            scope=App(),
            range_obj=one_all_blueprint,
            cdktf_id="test-abstract-stack",
            cdktf_dir="/nonexistent/dir",
            region=OpenLabsRegion.US_EAST_1,
            range_name="test-range",
        )
