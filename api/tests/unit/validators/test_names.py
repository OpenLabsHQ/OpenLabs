import re

import pytest

from src.app.validators.names import OPENLABS_NAME_REGEX


@pytest.mark.parametrize(
    "test_name",
    [
        "MyLab",
        "Lab2025",
        "Cyber-Range-1",
        "My_Awesome_Lab",
        "My Lab Environment",
        "Test_Lab-1 For science",
        "abc",
        "A" + "b" * 62 + "C",
        "TestLab1",
        "My  Lab",
        "a---c",
        "My______Lab",
    ],
    ids=[
        "simple_name",
        "name_with_numbers",
        "name_with_hyphen",
        "name_with_underscore",
        "name_with_space",
        "mixed_delimiters",
        "minimum_length",
        "maximum_length",
        "ends_with_number",
        "multiple_spaces",
        "multiple_hyphens",
        "multiple_underscores",
    ],
)
def test_valid_names(test_name: str) -> None:
    """Test strings that should successfully match the OpenLabs name regex."""
    assert re.match(
        OPENLABS_NAME_REGEX, test_name
    ), f"Expected '{test_name}' to be a valid name, but it failed to match."


@pytest.mark.parametrize(
    "test_name",
    [
        "ab",
        "a" * 65,
        "1stLab",
        "-MyLab",
        "_MyLab",
        " MyLab",
        "MyLab-",
        "MyLab_",
        "MyLab ",
        "MyLab!",
        "------",
        "",
        "a",
        "My Lab 👌👌👌👌🤣",
        "🅜🅨 🅠🅤🅘🅡🅚🅨 🅛🅐🅑",
    ],
    ids=[
        "too_short",
        "too_long",
        "starts_with_number",
        "starts_with_hyphen",
        "starts_with_underscore",
        "starts_with_space",
        "ends_with_hyphen",
        "ends_with_underscore",
        "ends_with_space",
        "contains_special_char",
        "only_delimiters",
        "empty_string",
        "single_char",
        "emojis",
        "unicode_text",
    ],
)
def test_invalid_names(test_name: str) -> None:
    """Tests strings that should NOT match the OpenLabs name regex pattern."""
    assert not re.match(
        OPENLABS_NAME_REGEX, test_name
    ), f"Expected '{test_name}' to be an invalid name, but it matched."
