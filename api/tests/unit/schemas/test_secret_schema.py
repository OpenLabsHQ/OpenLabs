import copy
import re

import pytest
from pydantic import ValidationError

from src.app.schemas.secret_schema import AWSSecrets
from tests.common.api.v1.config import aws_secrets_payload


def test_aws_secrets_schema_invalid_access_key_length() -> None:
    """Test that the AWS Secrets schema fails when aws_access_key is invalid length."""
    invalid_creds = copy.deepcopy(aws_secrets_payload)
    invalid_creds["aws_access_key"] = "string"

    expected_msg = re.compile(r"Invalid AWS access key format.", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        AWSSecrets.model_validate(invalid_creds)


def test_aws_secrets_schema_missing_access_key() -> None:
    """Test that the AWS Secrets schema fails when aws_access_key is missing."""
    invalid_creds = copy.deepcopy(aws_secrets_payload)
    invalid_creds["aws_access_key"] = ""  # Empty string = missing access key

    expected_msg = re.compile(r"No AWS access key provided.", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        AWSSecrets.model_validate(invalid_creds)


def test_aws_secrets_schema_invalid_secret_key_length() -> None:
    """Test that the AWS Secrets schema fails when aws_secret_key is invalid length."""
    invalid_creds = copy.deepcopy(aws_secrets_payload)
    invalid_creds["aws_secret_key"] = "string"  # noqa: S105

    expected_msg = re.compile(r"Invalid AWS secret key format.", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        AWSSecrets.model_validate(invalid_creds)


def test_aws_secrets_schema_missing_secret_key() -> None:
    """Test that the AWS Secrets schema fails when aws_secret_key is missing."""
    invalid_creds = copy.deepcopy(aws_secrets_payload)
    invalid_creds["aws_secret_key"] = ""  # Empty string = missing secret key

    expected_msg = re.compile(r"No AWS secret key provided.", re.IGNORECASE)
    with pytest.raises(ValidationError, match=expected_msg):
        AWSSecrets.model_validate(invalid_creds)
