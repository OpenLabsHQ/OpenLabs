import copy

import pytest

from src.app.cloud.aws_creds import AWSCreds
from src.app.cloud.creds_factory import CredsFactory
from src.app.schemas.creds_verify_schema import CredsVerifySchema
from tests.unit.api.v1.config import aws_secrets_payload


def test_creds_factory_non_existent_provider_type() -> None:
    """Test that CredsFactory.create_creds_verification() raises a ValueError when invalid provider is provided."""
    # Set provider to non-existent provider
    bad_provider_creds_payload = copy.deepcopy(aws_secrets_payload)

    invalid_creds_verify_schema = CredsVerifySchema.model_validate(
        bad_provider_creds_payload
    )
    # Ignore invalid string assignment since we are triggering a ValueError
    invalid_creds_verify_schema.provider = "FakeProvider"  # type: ignore

    with pytest.raises(ValueError):
        _ = CredsFactory.create_creds_verification(
            provider=invalid_creds_verify_schema.provider,
            credentials=invalid_creds_verify_schema.credentials,
        )


def test_creds_factory_build_aws_creds() -> None:
    """Test that CredsFactory can build an AWSCreds."""
    # Use AWS secrets payload with provider already set to AWS
    aws_creds = CredsVerifySchema.model_validate(aws_secrets_payload)

    creds_object = CredsFactory.create_creds_verification(
        provider=aws_creds.provider, credentials=aws_creds.credentials
    )

    assert type(creds_object) is AWSCreds
