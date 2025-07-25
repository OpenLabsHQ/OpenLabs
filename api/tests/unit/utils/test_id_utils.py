import pytest

from src.app.utils.id_utils import base36_encode


@pytest.mark.parametrize(
    ("number", "expected_str"),
    [
        (0, "0"),
        (10, "a"),
        (35, "z"),
        (36, "10"),
        (1234567890, "kf12oi"),
        (1_125_934_895_897_435, "b33zcm8msb"),
    ],
)
def test_base36_encode_valid_numbers(number: int, expected_str: str) -> None:
    """Verify base36_encode correctly encodes various non-negative integers."""
    assert base36_encode(number) == expected_str


def test_base36_encode_negative_input_error() -> None:
    """Verify base36_encode raises ValueError for negative numbers."""
    with pytest.raises(ValueError, match="negative"):
        base36_encode(-10)
