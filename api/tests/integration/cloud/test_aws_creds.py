import json
import logging
import time
import uuid
from typing import Generator

import boto3
import pytest
from botocore.exceptions import ClientError

from src.app.cloud.aws_creds import AWSCreds
from src.app.schemas.secret_schema import AWSSecrets
from tests.aws_test_utils import set_test_boto_creds

from .aws_config import VERIFY_CREDS_TEST_CASES

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def iam_client(load_test_env_file: bool) -> boto3.client:
    """Create IAM client, skipping if credentials are not set."""
    if not load_test_env_file or not set_test_boto_creds():
        pytest.skip("Credentials for AWS not set.")
    return boto3.client("iam")


@pytest.fixture(scope="session")
def all_test_credentials(
    iam_client: boto3.client,
) -> Generator[dict[str, dict[str, str]], None, None]:
    """Create all necessary IAM users/policies for the entire test session at once."""
    session_id = uuid.uuid4().hex[:8]
    created_resources = {}
    credentials_by_id = {}

    logger.info("Starting batch creation of IAM test resources...")

    try:
        # Batch Create all IAM Resources
        for param in VERIFY_CREDS_TEST_CASES:
            test_id = str(param.id)
            policy_document = param.values[0]

            user_name = f"openlabs-test-{test_id}-{session_id}"
            policy_name = f"OpenLabsTest-{test_id}-{session_id}"

            # Create user, policy, attach, and create key
            iam_client.create_user(UserName=user_name)
            policy_response = iam_client.create_policy(
                PolicyName=policy_name, PolicyDocument=json.dumps(policy_document)
            )
            policy_arn = policy_response["Policy"]["Arn"]
            iam_client.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)
            key_response = iam_client.create_access_key(UserName=user_name)
            access_key = key_response["AccessKey"]

            # Store credentials for the test to use
            credentials_by_id[test_id] = {
                "provider": "aws",
                "aws_access_key": access_key["AccessKeyId"],
                "aws_secret_key": access_key["SecretAccessKey"],
            }
            # Store all identifiers for later cleanup
            created_resources[test_id] = {
                "user_name": user_name,
                "policy_arn": policy_arn,
                "access_key_id": access_key["AccessKeyId"],
            }
            logger.info("Created resources for test ID: %s", test_id)

        prop_wait = 10
        logger.info("Waiting %d seconds for all IAM changes to propagate...", prop_wait)
        time.sleep(prop_wait)

        yield credentials_by_id

    finally:
        # 3. --- Batch Cleanup ---
        logger.info("Starting cleanup of all IAM test resources.")
        for test_id, resources in created_resources.items():
            user_name = resources["user_name"]
            logger.info(
                "Cleaning up resources for %s (user: %s)...", test_id, user_name
            )
            try:
                iam_client.detach_user_policy(
                    UserName=user_name, PolicyArn=resources["policy_arn"]
                )
            except ClientError as e:
                logger.warning("Failed to detach policy for %s: %s", user_name, e)
            try:
                iam_client.delete_policy(PolicyArn=resources["policy_arn"])
            except ClientError as e:
                logger.warning("Failed to delete policy for %s: %s", user_name, e)
            try:
                iam_client.delete_access_key(
                    UserName=user_name, AccessKeyId=resources["access_key_id"]
                )
            except ClientError as e:
                logger.warning("Failed to delete access key for %s: %s", user_name, e)
            try:
                iam_client.delete_user(UserName=user_name)
            except ClientError as e:
                logger.warning("Failed to delete user %s: %s", user_name, e)
        logger.info("IAM resource cleanup complete.")


@pytest.mark.parametrize(
    "test_id, expected_result, expected_message_part",
    [(p.id, p.values[1], p.values[2]) for p in VERIFY_CREDS_TEST_CASES],
    ids=[str(p.id) for p in VERIFY_CREDS_TEST_CASES],
)
def test_verify_aws_creds(
    all_test_credentials: dict[str, dict[str, str]],
    test_id: str,
    expected_result: bool,
    expected_message_part: str,
) -> None:
    """Test the AWS verify_creds method with various scenarios."""
    # The test now receives exactly the arguments it needs. No unpacking!
    credentials = all_test_credentials[test_id]
    aws_creds = AWSSecrets.model_validate(credentials)

    aws_verifier = AWSCreds(credentials=aws_creds)
    is_valid, message_schema = aws_verifier.verify_creds()

    assert is_valid is expected_result
    assert expected_message_part in message_schema.message.lower()
