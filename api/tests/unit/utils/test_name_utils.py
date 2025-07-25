import pytest

from src.app.utils.name_utils import normalize_name


@pytest.mark.parametrize(
    "input_name, expected_output",
    [
        # Basic cases
        ("My Awesome Lab", "my-awesome-lab"),
        ("another_test_name", "another-test-name"),
        ("simple-name", "simple-name"),  # Already normalized
        ("TestName", "testname"),  # Mixed case
        ("test123name", "test123name"),  # Numbers
        ("test-123-name", "test-123-name"),  # Numbers with hyphens
        # Special characters
        (
            "Name!@#$%^&*()_+={}|[]\\:;\"'<>,.?/~`",
            "name",
        ),
        ("Name with.dots", "name-with-dots"),
        ("Name with/slashes", "name-with-slashes"),
        ("Name with spaces and -hyphens", "name-with-spaces-and-hyphens"),
        # Multiple consecutive problematic characters
        ("Name--with---multiple____hyphens", "name-with-multiple-hyphens"),
        ("Name   with   many   spaces", "name-with-many-spaces"),
        ("Name_-_With_Mixed_Separators", "name-with-mixed-separators"),
        ("a---b", "a-b"),
        ("a___b", "a-b"),
        ("a...b", "a-b"),
        ("a@@@b", "a-b"),
        # Leading/trailing problematic characters
        ("-Name-Starts-With-Hyphen", "name-starts-with-hyphen"),
        ("Name-Ends-With-Hyphen-", "name-ends-with-hyphen"),
        (
            "  Name With Leading And Trailing Spaces  ",
            "name-with-leading-and-trailing-spaces",
        ),
        ("!@#NameWithSymbols!@#", "namewithsymbols"),
        ("---Name---", "name"),
        ("___Name___", "name"),
        ("...Name...", "name"),
        # Names that are already clean
        ("already-kebab-case", "already-kebab-case"),
        ("lowercasealphanumeric", "lowercasealphanumeric"),
    ],
)
def test_normalize_name_valid_cases(input_name: str, expected_output: str) -> None:
    """Test various valid input names to ensure they are normalized correctly to safe kebab-case versions."""
    assert normalize_name(input_name) == expected_output


@pytest.mark.parametrize(
    "input_name",
    [
        "",  # Empty string
        "   ",  # Only spaces
        "---",  # Only hyphens
        "!!!",  # Only special characters
        " @#$ ",  # Mixed problematic characters
        " _ ",  # Only underscores
        " . ",  # Only dots
    ],
    ids=[
        "empty_string",
        "only_spaces",
        "only_hyphens",
        "only_special_chars",
        "mixed_problematic_chars",
        "only_underscores",
        "only_dots",
    ],
)
def test_normalize_name_empty_raises_value_error(
    input_name: str,
) -> None:
    """Test input names that should result in an empty string after normalization that force a ValueError to be raised."""
    with pytest.raises(ValueError, match="empty"):
        normalize_name(input_name)
