import pytest

from src.app.utils.cdktf_utils import gen_resource_logical_ids


@pytest.mark.parametrize(
    "input_names, expected_ids",
    [
        # Basic cases
        pytest.param([], {}, id="empty_list"),
        pytest.param(["MyServer"], {"MyServer": "myserver"}, id="single_name"),
        pytest.param(
            ["Server1", "Server2"],
            {"Server1": "server1", "Server2": "server2"},
            id="two_unique_names",
        ),
        pytest.param(
            ["Web Server", "Database", "Auth Service"],
            {
                "Auth Service": "auth-service",
                "Database": "database",
                "Web Server": "web-server",
            },
            id="multiple_unique_names_with_spaces",
        ),
        # Collision handling
        pytest.param(
            ["Web Server", "web-server"],
            {"Web Server": "web-server", "web-server": "web-server-1"},
            id="two_collide_after_norm",
        ),
        pytest.param(
            ["Server", "server", "sErVeR"],
            {"Server": "server", "sErVeR": "server-1", "server": "server-2"},
            id="three_collide_after_norm",
        ),
        pytest.param(
            ["App-Service", "App Service", "app_service"],
            {
                "App Service": "app-service",
                "App-Service": "app-service-1",
                "app_service": "app-service-2",
            },
            id="multiple_collision_types",
        ),
        # Sorted order affects suffix assignment
        pytest.param(
            ["A", "a", "A-", "-a"],
            {"A": "a-1", "-a": "a", "A-": "a-2", "a": "a-3"},
            id="complex_collision_leading_trailing_symbols",
        ),
        # Names that normalize to the same base but are distinct in input
        pytest.param(
            ["user-profile", "User Profile"],
            {"user-profile": "user-profile-1", "User Profile": "user-profile"},
            id="distinct_input_same_norm",
        ),
        pytest.param(
            ["my_app", "my-app"],
            {"my_app": "my-app-1", "my-app": "my-app"},
            id="underscore_vs_hyphen",
        ),
    ],
)
def test_gen_resource_logical_ids_success(
    input_names: list[str], expected_ids: dict[str, str]
) -> None:
    """Test various valid inputs for gen_resource_logical_ids to validate ID generation and collision handling."""
    result = gen_resource_logical_ids(input_names)
    assert result == expected_ids


@pytest.mark.parametrize(
    "input_names",
    [
        pytest.param(["Duplicate", "Duplicate"], id="exact_duplicate_names"),
        pytest.param(["Test", "test", "Test"], id="exact_duplicate_mixed_case"),
        pytest.param(["A", "B", "A", "C", "B"], id="multiple_exact_duplicates"),
    ],
)
def test_gen_resource_logical_ids_duplicate_error(
    input_names: list[str],
) -> None:
    """Tests that gen_resource_logical_ids raises a ValueError when the input list contains exact duplicate names."""
    with pytest.raises(ValueError, match="duplicate"):
        gen_resource_logical_ids(input_names)
