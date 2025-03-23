import copy
import uuid

from fastapi import status
from httpx import AsyncClient

from src.app.core.cdktf.ranges.base_range import AbstractBaseRange
from src.app.core.cdktf.ranges.range_factory import RangeFactory
from src.app.models.template_range_model import TemplateRangeModel
from src.app.models.user_model import UserModel
from src.app.schemas.secret_schema import SecretSchema
from src.app.schemas.template_host_schema import TemplateHostSchema
from src.app.schemas.template_subnet_schema import TemplateSubnetHeaderSchema

from .config import (
    BASE_ROUTE,
    aws_secrets_payload,
    valid_host_payload,
    valid_range_deploy_payload,
    valid_range_payload,
    valid_subnet_payload,
    valid_vpc_payload,
)

###### Test /ranges/deploy #######


async def test_deploy_without_enc_key(auth_client: AsyncClient) -> None:
    """Test that attempting to deploy a range without being logged in will fail since the encryption key was not given from successful login."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy", json=valid_range_deploy_payload
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_deploy_without_valid_enc_key(auth_client: AsyncClient) -> None:
    """Test that attempting to deploy a range with an invalid encryption key will fail."""
    modified_enc_key = "in*vali*^%$"
    auth_client.cookies.update({"enc_key": modified_enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=valid_range_deploy_payload,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_deploy_without_valid_range_template(auth_client: AsyncClient) -> None:
    """Test that attempting to deploy a range with a non-existent range template will fail."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=valid_range_deploy_payload,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_deploy_without_valid_private_key(auth_client: AsyncClient) -> None:
    """Test that attempting to deploy a range without valid private key will fail."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges",
        json=valid_range_payload,
    )
    range_template_id = response.json()["id"]
    assert response.status_code == status.HTTP_200_OK

    # Validate UUID returned
    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response

    test_template_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    test_template_deploy_payload["template_id"] = range_template_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=test_template_deploy_payload,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_deploy_without_valid_secrets(
    auth_client: AsyncClient, mock_decrypt_no_secrets: None
) -> None:
    """Test that attempting to deploy a range without valid cloud provider credentials will fail (no secrets in database for user)."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges",
        json=valid_range_payload,
    )
    range_template_id = response.json()["id"]
    assert response.status_code == status.HTTP_200_OK

    # Validate UUID returned
    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response

    test_template_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    test_template_deploy_payload["template_id"] = range_template_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=test_template_deploy_payload,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_deploy_range_synthesize_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_synthesize_failure: None,
) -> None:
    """Test to deploy a range but fail during the systhesize step."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges",
        json=valid_range_payload,
    )
    range_template_id = response.json()["id"]
    assert response.status_code == status.HTTP_200_OK

    # Validate UUID returned
    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response

    test_template_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    test_template_deploy_payload["template_id"] = range_template_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=test_template_deploy_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


async def test_deploy_range_deploy_failure(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_deploy_failure: None,
) -> None:
    """Test to deploy a range but fail during the deploy step."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges",
        json=valid_range_payload,
    )
    range_template_id = response.json()["id"]
    assert response.status_code == status.HTTP_200_OK

    # Validate UUID returned
    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response

    test_template_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    test_template_deploy_payload["template_id"] = range_template_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=test_template_deploy_payload,
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


async def test_deploy_range_deploy_success(
    auth_client: AsyncClient,
    mock_decrypt_example_valid_aws_secrets: None,
    mock_deploy_success: None,
) -> None:
    """Test to deploy a range successfully with a returned range ID."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges",
        json=valid_range_payload,
    )
    range_template_id = response.json()["id"]
    assert response.status_code == status.HTTP_200_OK

    # Validate UUID returned
    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response

    test_template_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    test_template_deploy_payload["template_id"] = range_template_id

    response = await auth_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=test_template_deploy_payload,
    )
    assert response.status_code == status.HTTP_200_OK

    # Validate range UUID returned
    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response


###### Test /ranges/destroy #######


async def test_destroy_with_invalid_uuid(auth_client: AsyncClient) -> None:
    """Test that attempting to destroy a range without a valid uuid with fail."""
    invalid_range_id = "invalid-uuid"
    response = await auth_client.delete(f"{BASE_ROUTE}/ranges/{invalid_range_id}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_destroy_without_enc_key(auth_client: AsyncClient) -> None:
    """Test that attempting to destroy a range without being logged in will fail since the encryption key was not given from successful login."""
    test_range_id = uuid.uuid4()
    response = await auth_client.delete(f"{BASE_ROUTE}/ranges/{test_range_id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_destroy_without_valid_enc_key(auth_client: AsyncClient) -> None:
    """Test that attempting to destroy a range with an invalid encryption key will fail."""
    test_range_id = uuid.uuid4()
    modified_enc_key = "in*vali*^%$"
    auth_client.cookies.update({"enc_key": modified_enc_key})
    response = await auth_client.delete(f"{BASE_ROUTE}/ranges/{test_range_id}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_destroy_without_valid_range_owner(
    auth_client: AsyncClient, mock_is_range_owner_false: None
) -> None:
    """Test that attempting to destroy a range that a user does not own will fail."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    test_range_id = uuid.uuid4()
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.delete(f"{BASE_ROUTE}/ranges/{test_range_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_destroy_without_valid_range(
    auth_client: AsyncClient, mock_is_range_owner_true: None
) -> None:
    """Test that attempting to destroy a non-existent range will fail."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    test_range_id = uuid.uuid4()
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.delete(f"{BASE_ROUTE}/ranges/{test_range_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
