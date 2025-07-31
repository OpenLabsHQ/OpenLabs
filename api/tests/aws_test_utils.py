import logging
import os

from src.app.enums.providers import OpenLabsProvider
from tests.deploy_test_utils import get_provider_test_creds

# Configure logging
logger = logging.getLogger(__name__)


def set_test_boto_creds() -> bool:
    """Set credentials for the AWS boto client."""
    aws_provider = OpenLabsProvider.AWS
    creds = get_provider_test_creds(aws_provider)
    if not creds:
        logger.error(
            "Failed to set test boto creds. Test credentials for %s not set.",
            aws_provider.value.upper(),
        )
        return False

    # Set environment variables
    os.environ["AWS_ACCESS_KEY_ID"] = creds["aws_access_key"]
    os.environ["AWS_SECRET_ACCESS_KEY"] = creds["aws_secret_key"]

    return True
