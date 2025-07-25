from typing import Any, Generator

import pytest
from pytest_mock import MockerFixture, MockType

from src.app.utils.name_utils import CloudResourceNamer, normalize_name


@pytest.fixture(scope="session")
def name_utils_path() -> str:
    """Path to name utils."""
    return "src.app.utils.name_utils"


@pytest.fixture(scope="module")
def default_namer() -> CloudResourceNamer:
    """Create a pytest fixture for a standard CloudResourceNamer instance."""
    return CloudResourceNamer(deployment_id="dep123", range_name="my-web-app")


@pytest.fixture
def mock_uid_generator(
    mocker: MockerFixture, name_utils_path: str
) -> Generator[MockType, Any, Any]:
    """Generate uid and return a predictable UID."""
    # Create a fake UID based on the class constant for length
    fake_uid = "a" * CloudResourceNamer.SHORT_UID_LEN  # "aaaaaaaaaa"

    mock_uid = mocker.patch(
        f"{name_utils_path}.generate_short_uid", return_value=fake_uid
    )
    yield mock_uid


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


def test_cloud_resource_namer_init_success() -> None:
    """Test successful initialization of the CloudResourceNamer."""
    default_max_len = 63

    namer = CloudResourceNamer(deployment_id="dep123", range_name="my-range")
    assert namer.deployment_id == "dep123"
    assert namer.range_name == "my-range"
    assert namer.max_len == default_max_len


@pytest.mark.parametrize(
    "deployment_id, range_name, max_len, error_msg",
    [
        pytest.param(
            "",
            "my-range",
            63,
            "empty",
            id="empty_deployment_id",
        ),
        pytest.param("dep123", "", 63, "empty", id="empty_range_name"),
        pytest.param(
            "a-very-long-dep-id",
            "my-range",
            63,
            "longer",
            id="long_deployment_id",
        ),
        pytest.param(
            "dep123",
            "my-range",
            10,
            "too short",
            id="max_len_too_short",
        ),
        pytest.param(
            "------", "my-range", 63, "empty", id="deployment_id_normalizes_empty"
        ),
        pytest.param("dep123", "------", 63, "empty", id="range_name_normalizes_empty"),
    ],
)
def test_cloud_resource_namer_init_failures(
    deployment_id: str, range_name: str, max_len: int, error_msg: str
) -> None:
    """Verify CloudResourceNamer raises errors for invalid initialization parameters."""
    with pytest.raises(ValueError, match=error_msg):
        CloudResourceNamer(
            deployment_id=deployment_id, range_name=range_name, max_len=max_len
        )


def test_cloud_resource_namer_init_min_len_success() -> None:
    """Verify that initialization succeeds with the absolute minimum valid max_len."""
    # Prefix (2) + max len deployment_id (10) + max truncated range name (15) + min resource name (5) + worst case uses uid (10) + 4 hyphens
    # as separators for the 5 name parts
    try:
        CloudResourceNamer(deployment_id="dep123", range_name="my-range", max_len=46)
    except ValueError:
        pytest.fail("Initialization failed with minimum valid max_len=46")


def test_gen_name_standard_case_unique(
    default_namer: CloudResourceNamer, mock_uid_generator: MockType
) -> None:
    """Test a standard case with unique=True where all parts fit."""
    resource_name = "database-server"
    expected = "ol-dep123-my-web-app-database-server-aaaaaaaaaa"
    result = default_namer.gen_cloud_resource_name(resource_name, unique=True)

    assert result == expected
    assert len(result) <= default_namer.max_len
    mock_uid_generator.assert_called_once()


def test_gen_name_standard_case_not_unique(default_namer: CloudResourceNamer) -> None:
    """Test a standard case with unique=False."""
    resource_name = "load-balancer"
    expected = "ol-dep123-my-web-app-load-balancer"
    result = default_namer.gen_cloud_resource_name(resource_name, unique=False)
    assert result == expected


def test_gen_name_with_normalization_and_truncation(
    mock_uid_generator: MockType,
) -> None:
    """Test with inputs that require normalization and truncation for all parts."""
    long_range_name = "This is my Frontend Application Range!!"
    long_resource_name = "Primary User Authentication Service Instance"

    namer = CloudResourceNamer(
        deployment_id="DEP--ID", range_name=long_range_name, max_len=63
    )
    result = namer.gen_cloud_resource_name(long_resource_name, unique=True)

    # The resource name is truncated to fit the remaining 26 characters.
    expected = "ol-dep-id-this-is-my-fron-primary-user-authenticatio-aaaaaaaaaa"

    assert result == expected
    assert len(result) == namer.max_len


def test_gen_name_truncation_strips_trailing_hyphen(
    default_namer: CloudResourceNamer,
) -> None:
    """Test that when truncation leaves a hyphen at the end of a part it gets stripped."""
    # The available length for the resource name here is 42 characters.
    # The normalized resource name "a-long-name-that-will-be-truncated-at-the-X" is 43 chars.
    # Truncating to 42 leaves a trailing hyphen, which should be stripped.
    resource_name = "a-long-name-that-will-be-truncated-at-the-X"
    expected = "ol-dep123-my-web-app-a-long-name-that-will-be-truncated-at-the"
    result = default_namer.gen_cloud_resource_name(resource_name, unique=False)
    assert result == expected
    assert len(result) == (default_namer.max_len - 1)  # Stripped trailing hyphen


def test_gen_name_exact_fit(default_namer: CloudResourceNamer) -> None:
    """Test a scenario where the generated name is exactly the max_len."""
    # Fixed parts: ol(2) + dep123(6) + my-web-app(10) + 3 hyphens = 21
    # Available for resource name: 63 - 21 = 42 chars.
    resource_name = "a" * 42
    expected = f"ol-dep123-my-web-app-{'a' * 42}"
    result = default_namer.gen_cloud_resource_name(resource_name, unique=False)

    assert result == expected
    assert len(result) == default_namer.max_len
