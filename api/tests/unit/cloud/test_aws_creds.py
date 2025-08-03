import pytest
from pytest_mock import MockerFixture
from botocore.exceptions import ClientError

from src.app.cloud.aws_creds import AWSCreds
from src.app.schemas.secret_schema import AWSSecrets, SecretSchema
from src.app.utils.crypto import encrypt_with_public_key, generate_rsa_key_pair
from tests.common.api.v1.config import aws_secrets_payload


@pytest.fixture(scope="module")
def aws_creds_class() -> AWSCreds:
    """Create a AWS creds class object."""
    return AWSCreds(aws_secrets_payload["credentials"])


def test_init(aws_creds_class: AWSCreds) -> None:
    """Test that initializing the aws creds object creates and stores and AWS Secrets Schema object."""
    assert isinstance(aws_creds_class.credentials, AWSSecrets)


def test_get_user_creds(aws_creds_class: AWSCreds) -> None:
    """Test that getting user credentials is returned as a proper dictionary."""
    user_creds = aws_creds_class.get_user_creds()

    # Keys
    access_key = "aws_access_key"
    secret_key = "aws_secret_key"  # noqa: S105

    assert user_creds[access_key] == aws_secrets_payload["credentials"][access_key]
    assert user_creds[secret_key] == aws_secrets_payload["credentials"][secret_key]


def test_update_secret_schema(aws_creds_class: AWSCreds) -> None:
    """Test that Secret Schema is updated with encrypted user credentials."""
    user_creds = aws_creds_class.get_user_creds()

    # Encrypt with the user's public key
    _, public_key = generate_rsa_key_pair()
    encrypted_data = encrypt_with_public_key(data=user_creds, public_key_b64=public_key)

    # Update the secrets with encrypted values
    secrets = SecretSchema()
    secrets = aws_creds_class.update_secret_schema(
        secrets=secrets, encrypted_data=encrypted_data
    )

    assert secrets.aws_access_key == encrypted_data["aws_access_key"]
    assert secrets.aws_secret_key == encrypted_data["aws_secret_key"]


def test_verify_creds_success(aws_creds_class: AWSCreds, mocker: MockerFixture) -> None:
    """Test successful credential verification with sufficient permissions."""
    # Mock the boto3 session and its clients
    mock_session = mocker.patch("boto3.Session").return_value
    mock_sts = mock_session.client.return_value
    mock_iam = mock_session.client.return_value

    # Configure mock responses
    mock_sts.get_caller_identity.return_value = {
        "Arn": "arn:aws:iam::123456789012:user/test-user"
    }
    mock_iam.simulate_principal_policy.return_value = {
        "EvaluationResults": [
            {"EvalDecision": "allowed", "EvalActionName": "ec2:RunInstances"}
        ]
    }

    # Execute the function
    verified, msg = aws_creds_class.verify_creds()

    # Assert the results
    assert verified is True
    assert "authenticated and all required permissions are present" in msg.message
    mock_sts.get_caller_identity.assert_called_once()
    mock_iam.simulate_principal_policy.assert_called_once()


def test_verify_creds_root_user(
    aws_creds_class: AWSCreds, mocker: MockerFixture
) -> None:
    """Test that the permissions check is skipped for the root user."""
    mock_session = mocker.patch("boto3.Session").return_value
    mock_sts = mock_session.client.return_value
    mock_iam = mock_session.client.return_value

    mock_sts.get_caller_identity.return_value = {
        "Arn": "arn:aws:iam::123456789012:root"
    }

    verified, msg = aws_creds_class.verify_creds()

    assert verified is True
    assert "authenticated and all required permissions are present" in msg.message
    mock_iam.simulate_principal_policy.assert_not_called()  # Ensure IAM check was skipped


def test_verify_creds_insufficient_permissions(
    aws_creds_class: AWSCreds, mocker: MockerFixture
) -> None:
    """Test verification failure due to denied actions in the simulation."""
    mock_session = mocker.patch("boto3.Session").return_value
    mock_sts = mock_session.client.return_value
    mock_iam = mock_session.client.return_value

    mock_sts.get_caller_identity.return_value = {
        "Arn": "arn:aws:iam::123456789012:user/limited-user"
    }
    mock_iam.simulate_principal_policy.return_value = {
        "EvaluationResults": [
            {"EvalDecision": "allowed", "EvalActionName": "ec2:DescribeInstances"},
            {"EvalDecision": "implicitDeny", "EvalActionName": "ec2:RunInstances"},
            {"EvalDecision": "implicitDeny", "EvalActionName": "ec2:CreateVpc"},
        ]
    }

    verified, msg = aws_creds_class.verify_creds()

    assert verified is False
    assert "Insufficient permissions" in msg.message
    assert "ec2:RunInstances" in msg.message
    assert "ec2:CreateVpc" in msg.message
    assert (
        "ec2:DescribeInstances" not in msg.message
    )  # Ensure only denied actions are listed


def test_verify_creds_invalid_token(
    aws_creds_class: AWSCreds, mocker: MockerFixture
) -> None:
    """Test verification failure due to invalid credentials."""
    mock_session = mocker.patch("boto3.Session").return_value
    mock_sts = mock_session.client.return_value

    # Simulate a ClientError for an invalid token
    error_response = {
        "Error": {
            "Code": "InvalidTokenId",
            "Message": "The security token included in the request is invalid.",
        }
    }
    mock_sts.get_caller_identity.side_effect = ClientError(
        error_response, "GetCallerIdentity"
    )

    verified, msg = aws_creds_class.verify_creds()

    assert verified is False
    assert msg.message == "The security token included in the request is invalid."


def test_verify_creds_iam_access_denied(
    aws_creds_class: AWSCreds, mocker: MockerFixture
) -> None:
    """Test failure when credentials are valid but cannot perform the IAM simulation."""
    mock_session = mocker.patch("boto3.Session").return_value
    mock_sts = mock_session.client.return_value
    mock_iam = mock_session.client.return_value

    mock_sts.get_caller_identity.return_value = {
        "Arn": "arn:aws:iam::123456789012:user/test-user"
    }

    # Simulate a ClientError for lack of iam:SimulatePrincipalPolicy permission
    error_response = {
        "Error": {
            "Code": "AccessDenied",
            "Message": "User is not authorized to perform iam:SimulatePrincipalPolicy",
        }
    }
    mock_iam.simulate_principal_policy.side_effect = ClientError(
        error_response, "SimulatePrincipalPolicy"
    )

    verified, msg = aws_creds_class.verify_creds()

    assert verified is False
    assert "iam:SimulatePrincipalPolicy permission" in msg.message
