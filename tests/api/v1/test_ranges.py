import copy
import json
import uuid

import pytest
from fastapi import status
from httpx import AsyncClient

from src.app.models.template_range_model import TemplateRangeModel
from src.app.schemas.template_host_schema import TemplateHostSchema
from src.app.schemas.template_subnet_schema import TemplateSubnetHeaderSchema

from .config import (
    BASE_ROUTE,
    valid_host_payload,
    valid_range_deploy_payload,
    valid_range_payload,
    valid_subnet_payload,
    valid_vpc_payload,
)

###### Test /ranges/deploy #######



async def test_deploy_without_enc_key(client: AsyncClient) -> None:
    """Test that attempting to deploy a range without being logged in will fail since the encryption key was not given from successful login."""
    response = await client.post(
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

async def test_deploy_without_valid_secrets(auth_client: AsyncClient) -> None:
    """Test that attempting to deploy a range without valid credentials will fail."""
    enc_key = "VGhpcyBpcyBhIHRlc3Qgc3RyaW5nIGZvciBiYXNlNjQgZW5jb2Rpbmcu"
    auth_client.cookies.update({"enc_key": enc_key})
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges",
        json=valid_range_payload,
    )
    range_template_id = response.json()["id"]
    assert response.status_code == status.HTTP_200_OK
