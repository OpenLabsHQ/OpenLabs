import pytest
from cdktf import App

from src.app.core.cdktf.stacks.base_stack import AbstractBaseStack
from src.app.enums.regions import OpenLabsRegion
from tests.unit.core.cdktf.config import one_all_template


def test_abstract_stack_creation_not_implemented_error() -> None:
    """Ensure that instantiating the AbstractBaseStack raises NontImplementedError."""
    with pytest.raises(NotImplementedError):
        AbstractBaseStack(
            scope=App(),
            template_range=one_all_template,
            cdktf_id="test-abstract-stack",
            cdktf_dir="/nonexistent/dir",
            region=OpenLabsRegion.US_EAST_1,
        )
