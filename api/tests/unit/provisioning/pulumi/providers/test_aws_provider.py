import pytest

from src.app.enums.regions import AWS_REGION_MAP, OpenLabsRegion
from src.app.provisioning.pulumi.providers.aws_provider import aws_provider
from src.app.schemas.secret_schema import SecretSchema


def test_has_secrets_with_valid_keys_returns_true() -> None:
    """Test that has secrets checks for the correct secrets schema attributes."""
    test_secrets = SecretSchema(
        aws_access_key="string", aws_secret_key="string"  # noqa: S106
    )
    assert aws_provider.has_secrets(test_secrets)


@pytest.mark.parametrize(
    "secrets_obj",
    [
        SecretSchema(aws_access_key="key", aws_secret_key=None),
        SecretSchema(aws_access_key=None, aws_secret_key="secret"),  # noqa: S106
        SecretSchema(aws_access_key="", aws_secret_key="secret"),  # noqa: S106
        SecretSchema(aws_access_key="key", aws_secret_key=""),
        SecretSchema(aws_access_key=None, aws_secret_key=None),
    ],
)
def test_has_secrets_with_invalid_or_missing_keys_returns_false(
    secrets_obj: SecretSchema,
) -> None:
    """Test edge cases for has_secrets where keys are missing or empty."""
    assert aws_provider.has_secrets(secrets_obj) is False


def test_get_config_values_with_valid_inputs_returns_correct_dict() -> None:
    """Test the happy path for get_config_values."""
    test_secrets = SecretSchema(
        aws_access_key="my-access-key", aws_secret_key="my-secret-key"  # noqa: S106
    )
    test_region = OpenLabsRegion.US_EAST_1

    config = aws_provider.get_config_values(region=test_region, secrets=test_secrets)

    assert config["aws:region"].value == AWS_REGION_MAP[test_region]
    assert config["aws:accessKey"].value == test_secrets.aws_access_key
    assert config["aws:accessKey"].secret is True
    assert config["aws:secretKey"].value == test_secrets.aws_secret_key
    assert config["aws:secretKey"].secret is True


def test_get_config_values_with_missing_credentials_raises_value_error() -> None:
    """Test error handling for get_config_values when credentials are missing."""
    test_secrets = SecretSchema(aws_access_key="fake-key", aws_secret_key=None)
    with pytest.raises(ValueError, match="AWS credentials"):
        aws_provider.get_config_values(OpenLabsRegion.US_EAST_1, test_secrets)


def test_get_cred_env_vars_with_valid_secrets_returns_correct_dict() -> None:
    """Test the happy path for get_cred_env_vars."""
    test_secrets = SecretSchema(
        aws_access_key="fake-key", aws_secret_key="fake-secret"  # noqa: S106
    )
    env_vars = aws_provider.get_cred_env_vars(test_secrets)
    assert env_vars["AWS_ACCESS_KEY_ID"] == test_secrets.aws_access_key
    assert env_vars["AWS_SECRET_ACCESS_KEY"] == test_secrets.aws_secret_key


def test_get_cred_env_vars_cure() -> None:
    """Test error handling for get_cred_env_vars when credentials are missing."""
    test_secrets = SecretSchema(aws_access_key="fake-key", aws_secret_key=None)
    with pytest.raises(ValueError, match="AWS credentials"):
        aws_provider.get_cred_env_vars(test_secrets)
