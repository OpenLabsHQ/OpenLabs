import copy
import random
import string

import pytest
from fastapi import status
from httpx import AsyncClient

from tests.api_test_utils import authenticate_client
from tests.common.api.v1.config import (
    API_CLIENT_PARAMS,
    AUTH_API_CLIENT_PARAMS,
    BASE_ROUTE,
    valid_blueprint_range_create_payload,
    valid_range_deploy_payload,
)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_deploy_without_enc_key(api_client: AsyncClient) -> None:
    """Test that attempting to deploy a range without being logged in will fail since the encryption key was not given from successful login."""
    assert await authenticate_client(api_client), "Failed to authenticate to API"

    for cookie in api_client.cookies.jar:
        if cookie.name == "enc_key":
            cookie.value = ""
            break

    response = await api_client.post(
        f"{BASE_ROUTE}/ranges/deploy", json=valid_range_deploy_payload
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_deploy_without_valid_enc_key(auth_api_client: AsyncClient) -> None:
    """Test that attempting to deploy a range with an invalid encryption key will fail."""
    modified_enc_key = "in*vali*^%$"
    auth_api_client.cookies.update({"enc_key": modified_enc_key})
    response = await auth_api_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=valid_range_deploy_payload,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_deploy_without_valid_range_blueprint(
    auth_api_client: AsyncClient,
) -> None:
    """Test that attempting to deploy a range with a non-existent range blueprint will fail."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_api_client.cookies.update({"enc_key": enc_key})
    non_existent_range_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    non_existent_range_deploy_payload["blueprint_id"] = random.randint(  # noqa: S311
        -666, -69
    )
    response = await auth_api_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=valid_range_deploy_payload,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_deploy_without_valid_private_key(auth_api_client: AsyncClient) -> None:
    """Test that attempting to deploy a range without valid private key will fail."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_api_client.cookies.update({"enc_key": enc_key})
    response = await auth_api_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    blueprint_deploy_payload = copy.deepcopy(valid_range_deploy_payload)
    blueprint_deploy_payload["blueprint_id"] = blueprint_id

    response = await auth_api_client.post(
        f"{BASE_ROUTE}/ranges/deploy",
        json=blueprint_deploy_payload,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_destroy_with_invalid_id(auth_api_client: AsyncClient) -> None:
    """Test that attempting to destroy a range without a valid non-int ID with fail."""
    random_str = "".join(
        random.choice(string.ascii_letters)  # noqa: S311
        for i in range(random.randint(1, 10))  # noqa: S311
    )
    response = await auth_api_client.delete(f"{BASE_ROUTE}/ranges/{random_str}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_destroy_without_enc_key(api_client: AsyncClient) -> None:
    """Test that attempting to destroy a range without being logged in will fail since the encryption key was not given from successful login."""
    assert await authenticate_client(api_client), "Failed to authenticate to API"

    for cookie in api_client.cookies.jar:
        if cookie.name == "enc_key":
            cookie.value = ""
            break

    response = await api_client.delete(
        f"{BASE_ROUTE}/ranges/{random.randint(1, 100)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_destroy_without_valid_enc_key(auth_api_client: AsyncClient) -> None:
    """Test that attempting to destroy a range with an invalid encryption key will fail."""
    modified_enc_key = "in*vali*^%$"
    auth_api_client.cookies.update({"enc_key": modified_enc_key})
    response = await auth_api_client.delete(
        f"{BASE_ROUTE}/ranges/{random.randint(1, 100)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_destroy_without_valid_range(auth_api_client: AsyncClient) -> None:
    """Test that attempting to destroy a non-existent range will fail."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_api_client.cookies.update({"enc_key": enc_key})
    response = await auth_api_client.delete(
        f"{BASE_ROUTE}/ranges/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "api_client",
    API_CLIENT_PARAMS,
    indirect=True,
)
async def test_get_range_headers_empty_list(api_client: AsyncClient) -> None:
    """Test that we get a 404 when there are no deployed range headers."""
    # Make a new user that will not have deployed ranges
    assert await authenticate_client(api_client)

    response = await api_client.get(f"{BASE_ROUTE}/ranges")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_get_range_details_non_existent(auth_api_client: AsyncClient) -> None:
    """Test that we get a 404 when we request a non-existent range."""
    non_existent_id = random.randint(-420, -69)  # noqa: S311
    response = await auth_api_client.get(f"{BASE_ROUTE}/ranges/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "auth_api_client",
    AUTH_API_CLIENT_PARAMS,
    indirect=True,
)
async def test_get_range_key_non_existent(auth_api_client: AsyncClient) -> None:
    """Test that we get a 404 when we request a non-existent range's key."""
    non_existent_id = random.randint(-420, -69)  # noqa: S311
    response = await auth_api_client.get(f"{BASE_ROUTE}/ranges/{non_existent_id}/key")
    assert response.status_code == status.HTTP_404_NOT_FOUND
