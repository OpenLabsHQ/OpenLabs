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
    base_user_login_payload,
    base_user_register_payload,
    valid_host_payload,
    valid_range_payload,
    valid_subnet_payload,
    valid_vpc_payload,
)

###### Test /template/range #######

# global auth token to be used in all tests
auth_token = None

user_register_payload = copy.deepcopy(base_user_register_payload)
user_login_payload = copy.deepcopy(base_user_login_payload)

user_register_payload["email"] = "test-templates@ufsit.club"
user_login_payload["email"] = user_register_payload["email"]


async def test_template_range_get_all_empty_list(
    auth_client: AsyncClient,
) -> None:
    """Test that we get a 404 response when there are no range templates."""
    response = await auth_client.get(f"{BASE_ROUTE}/templates/ranges")
    print(response.json())
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_vpc_get_all_empty_list(auth_client: AsyncClient) -> None:
    """Test that we get a 404 response when there are no vpc templates."""
    response = await auth_client.get(f"{BASE_ROUTE}/templates/vpcs")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_subnet_get_all_empty_list(auth_client: AsyncClient) -> None:
    """Test that we get a 404 response when there are no subnet templates."""
    response = await auth_client.get(f"{BASE_ROUTE}/templates/subnets")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_host_get_all_empty_list(auth_client: AsyncClient) -> None:
    """Test that we get a 404 response when there are no template templates."""
    response = await auth_client.get(f"{BASE_ROUTE}/templates/hosts")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_range_get_non_empty_list(auth_client: AsyncClient) -> None:
    """Test all templates to see that we get a 200 response and that correct UUIDs exist."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    range_template_id = response.json()["id"]
    assert response.status_code == status.HTTP_200_OK

    response = await auth_client.get(f"{BASE_ROUTE}/templates/ranges")
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert len(response_json) == 1

    non_nested_range_dict = copy.deepcopy(valid_range_payload)
    del non_nested_range_dict["vpcs"]
    assert response_json[0] == {"id": range_template_id, **non_nested_range_dict}


async def test_template_all_get_non_standalone_templates(
    auth_client: AsyncClient,
) -> None:
    """Test that, after uploading range template previously, we have all non-standalone templates."""
    # Add a range
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK

    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/vpcs?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert len(response_json) == 1

    non_nested_vpc_dict = copy.deepcopy(valid_vpc_payload)
    del non_nested_vpc_dict["subnets"]
    assert response_json[0] == {"id": response_json[0]["id"], **non_nested_vpc_dict}

    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert len(response_json) == 1

    non_nested_subnet_dict = copy.deepcopy(valid_subnet_payload)
    del non_nested_subnet_dict["hosts"]
    assert response_json[0] == {"id": response_json[0]["id"], **non_nested_subnet_dict}

    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert len(response_json) == 1

    non_nested_host_dict = copy.deepcopy(valid_host_payload)
    assert response_json[0] == {"id": response_json[0]["id"], **non_nested_host_dict}


async def test_template_vpc_get_non_empty_list(auth_client: AsyncClient) -> None:
    """Test all templates to see that we get a 200 response and that correct headers exist."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=valid_vpc_payload
    )
    vpc_template_id = response.json()["id"]
    assert response.status_code == status.HTTP_200_OK

    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/vpcs?standalone_only=true"
    )
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert len(response_json) == 1

    non_nested_vpc_dict = copy.deepcopy(valid_vpc_payload)
    del non_nested_vpc_dict["subnets"]
    assert response_json[0] == {"id": vpc_template_id, **non_nested_vpc_dict}


async def test_template_subnet_get_non_empty_list(auth_client: AsyncClient) -> None:
    """Test all templates to see that we get a 200 response and that correct headers exist."""
    # Create unique subnet object for this test
    unique_valid_subnet_payload = copy.deepcopy(valid_subnet_payload)
    unique_valid_subnet_payload["name"] = str(uuid.uuid4())

    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/subnets", json=unique_valid_subnet_payload
    )
    subnet_template_id = response.json()["id"]
    assert response.status_code == status.HTTP_200_OK

    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets?standalone_only=true"
    )
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert len(response_json) >= 1  # Our subnet template must be in there

    # Dynamically build header object to avoid future updates breaking tests
    concat_dict = {"id": subnet_template_id, **unique_valid_subnet_payload}
    subnet_header_obj = TemplateSubnetHeaderSchema(**concat_dict)

    expected = json.loads(subnet_header_obj.model_dump_json())
    assert expected in response_json


async def test_template_host_get_non_empty_list(auth_client: AsyncClient) -> None:
    """Test all templates to see that we get a 200 response and that correct headers exist."""
    # Create unique host object for this test
    unique_valid_host_payload = copy.deepcopy(valid_host_payload)
    unique_valid_host_payload["name"] = str(uuid.uuid4())

    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/hosts", json=unique_valid_host_payload
    )
    host_template_id = response.json()["id"]
    assert response.status_code == status.HTTP_200_OK

    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=true"
    )
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert len(response_json) >= 1  # Our subnet template must be in there

    # Dynamically build header object to avoid future updates breaking tests
    concat_dict = {"id": host_template_id, **unique_valid_host_payload}
    host_header_obj = TemplateHostSchema(**concat_dict)

    expected = json.loads(host_header_obj.model_dump_json())
    assert expected in response_json


###### Order no longer matters ######


async def test_template_range_valid_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 and a valid uuid.UUID4 in response."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    # Validate UUID returned
    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response


async def test_template_range_get_range_invalid_uuid(auth_client: AsyncClient) -> None:
    """Test that we get a 400 when providing an invalid UUID4."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]
    uuid_response = response.json()["id"]

    # Test that the invalid UUID doesn't work
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/ranges/{uuid_response[:-1]}"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "uuid" in str(response.json()["detail"]).lower()  # Mentions the UUID

    # Test that the valid UUID still works
    response = await auth_client.get(f"{BASE_ROUTE}/templates/ranges/{uuid_response}")
    assert response.status_code == status.HTTP_200_OK


async def test_template_range_invalid_vpc_cidr(auth_client: AsyncClient) -> None:
    """Test for 422 response when VPC CIDR is invalid."""
    # Use deepcopy to ensure all nested dicts are copied
    invalid_payload = copy.deepcopy(valid_range_payload)
    invalid_payload["vpcs"][0][
        "cidr"
    ] = "192.168.300.0/24"  # Assign the invalid CIDR block
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_invalid_subnet_cidr(auth_client: AsyncClient) -> None:
    """Test for 422 response when subnet CIDR is invalid."""
    # Use deepcopy to ensure all nested dicts are copied
    invalid_payload = copy.deepcopy(valid_range_payload)
    invalid_payload["vpcs"][0]["subnets"][0][
        "cidr"
    ] = "192.168.300.0/24"  # Assign the invalid CIDR block
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_invalid_vpc_subnet_cidr_contain(
    auth_client: AsyncClient,
) -> None:
    """Test for 422 response when subnet CIDR is not contained in the VPC CIDR."""
    invalid_payload = copy.deepcopy(valid_range_payload)

    # VPC CIDR
    invalid_payload["vpcs"][0]["cidr"] = "192.168.0.0/16"

    # Subnet CIDR
    invalid_payload["vpcs"][0]["subnets"][0][
        "cidr"
    ] = "172.16.1.0/24"  # Assign the invalid CIDR block

    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_empty_tag(auth_client: AsyncClient) -> None:
    """Test for a 422 response when a tag is empty."""
    invalid_payload = copy.deepcopy(valid_range_payload)
    invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0]["tags"].append("")
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_invalid_provider(auth_client: AsyncClient) -> None:
    """Test for a 422 response when the provider is invalid."""
    invalid_payload = copy.deepcopy(valid_range_payload)
    invalid_payload["provider"] = "invalid_provider"  # Not a valid enum value
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_invalid_hostname(auth_client: AsyncClient) -> None:
    """Test for a 422 response when a hostname is invalid."""
    invalid_payload = copy.deepcopy(valid_range_payload)
    invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0]["hostname"] = "-i-am-invalid"
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_duplicate_vpc_names(auth_client: AsyncClient) -> None:
    """Test for a 422 response when multiple VPCs share the same name."""
    invalid_payload = copy.deepcopy(valid_range_payload)
    invalid_payload["vpcs"].append(
        copy.deepcopy(invalid_payload["vpcs"][0])
    )  # Duplicate the first VPC
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_duplicate_subnet_names(auth_client: AsyncClient) -> None:
    """Test for a 422 response when multiple subnets share the same name."""
    invalid_payload = copy.deepcopy(valid_range_payload)
    invalid_payload["vpcs"][0]["subnets"].append(
        copy.deepcopy(invalid_payload["vpcs"][0]["subnets"][0])
    )
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_duplicate_host_hostnames(
    auth_client: AsyncClient,
) -> None:
    """Test for a 422 response when multiple hosts share the same hostname."""
    invalid_payload = copy.deepcopy(valid_range_payload)
    invalid_payload["vpcs"][0]["subnets"][0]["hosts"].append(
        copy.deepcopy(invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0])
    )
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_get_range(auth_client: AsyncClient) -> None:
    """Test that we can retrieve the correct range after saving it in the database."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK

    range_id = response.json()["id"]

    response = await auth_client.get(f"{BASE_ROUTE}/templates/ranges/{range_id}")
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    expected_response = {"id": range_id, **valid_range_payload}
    assert response.json() == expected_response


async def test_template_range_get_nonexistent_range(auth_client: AsyncClient) -> None:
    """Test that we get a 404 error when requesting an nonexistent range in the database."""
    nonexistent_range_id = uuid.uuid4()
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/ranges/{nonexistent_range_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_range_subnet_too_many_hosts(auth_client: AsyncClient) -> None:
    """Test that we get a 422 error when more hosts in subnet that CIDR allows."""
    invalid_payload = copy.deepcopy(valid_range_payload)
    invalid_payload["vpcs"][0]["subnets"][0][
        "cidr"
    ] = "192.168.1.0/31"  # Maximum 2 hosts

    # Add extra hosts
    for i in range(3):
        copy_host = copy.deepcopy(invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0])
        copy_host["hostname"] = copy_host["hostname"] + str(i)
        invalid_payload["vpcs"][0]["subnets"][0]["hosts"].append(copy_host)

    max_hosts_allowed = 2
    assert len(invalid_payload["vpcs"][0]["subnets"][0]["hosts"]) > max_hosts_allowed

    # Request
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_host_size_too_small(auth_client: AsyncClient) -> None:
    """Test that we get a 422 error when the disk size of a host is too small."""
    invalid_payload = copy.deepcopy(valid_range_payload)
    invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0]["size"] = 2

    # Request
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_range_delete(auth_client: AsyncClient) -> None:
    """Test that we can sucessfully delete a range template."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK

    range_id = response.json()["id"]

    # Delete range
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/ranges/{range_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check that range is no longer in database
    response = await auth_client.get(f"{BASE_ROUTE}/templates/ranges/{range_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_range_delete_invalid_uuid(auth_client: AsyncClient) -> None:
    """Test that we get a 400 when providing an invalid UUID4."""
    invalid_uuid = str(uuid.uuid4())[:-1]
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/ranges/{invalid_uuid}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "uuid" in str(response.json()["detail"]).lower()


async def test_template_ramge_delete_non_existent(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when trying to delete a nonexistent range template."""
    random_uuid = str(uuid.uuid4())
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/ranges/{random_uuid}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_range_delete_non_standalone(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that we get a 409 when trying to delete a non-standalone range template.

    **Note:** When this test was written, ranges could never be non-standalone. Ranges
    were the highest level template and as a result the is_standalone() method was
    hardcoded to always return True for compatibility. This is why the method is mocked.
    """
    # Patch range model method to return False
    monkeypatch.setattr(TemplateRangeModel, "is_standalone", lambda self: False)

    # Add a range template
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK

    range_id = response.json()["id"]

    # Delete range
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/ranges/{range_id}")
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "standalone" in str(response.json()["detail"]).lower()


async def test_template_range_delete_cascade_vpcs_subnets_and_hosts(
    auth_client: AsyncClient,
) -> None:
    """Test that when we delete a range template it cascades and deletes the associated vpcs, subnets, and hosts."""
    # Get all existing hosts
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        existing_host_template_id = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        existing_host_template_id = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    # Get all existing subnets
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        existing_subnet_template_id = [subnet["id"] for subnet in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        existing_subnet_template_id = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    # Get all existing vpcs
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/vpcs?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        existing_vpc_template_id = [vpc["id"] for vpc in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        existing_vpc_template_id = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    # Add a range template
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK

    range_id = response.json()["id"]

    # Find new vpc template
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/vpcs?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK

    new_vpc_template_id = ""
    for vpc in response.json():
        if vpc["id"] not in existing_vpc_template_id:
            new_vpc_template_id = vpc["id"]
            break
    assert new_vpc_template_id

    # Find new subnet template
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK

    new_subnet_template_id = ""
    for subnet in response.json():
        if subnet["id"] not in existing_subnet_template_id:
            new_subnet_template_id = subnet["id"]
            break
    assert new_subnet_template_id

    # Find new host template
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK

    new_host_template_id = ""
    for host in response.json():
        if host["id"] not in existing_host_template_id:
            new_host_template_id = host["id"]
            break
    assert new_host_template_id

    # Delete standalone range template
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/ranges/{range_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check to see if dependent vpc template was removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/vpcs?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        leftover_vpc_template_ids = [vpc["id"] for vpc in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        leftover_vpc_template_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert new_vpc_template_id not in leftover_vpc_template_ids

    # Check to see if dependent subnet template was removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        leftover_subnet_template_ids = [subnet["id"] for subnet in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        leftover_subnet_template_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert new_subnet_template_id not in leftover_subnet_template_ids

    # Check to see if the dependent host template was removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        leftover_host_template_ids = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        leftover_host_template_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert new_host_template_id not in leftover_host_template_ids


async def test_template_vpc_valid_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 response and a valid uuid.UUID4 in response."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=valid_vpc_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    # Validate UUID returned
    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response


async def test_template_vpc_get_vpc_invalid_uuid(auth_client: AsyncClient) -> None:
    """Test that we get a 400 when providing an invalid UUID4."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=valid_vpc_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]
    uuid_response = response.json()["id"]

    # Test that the invalid UUID doesn't work
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/vpcs/{uuid_response[:-1]}"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "uuid" in str(response.json()["detail"]).lower()  # Mentions the UUID

    # Test that the valid UUID still works
    response = await auth_client.get(f"{BASE_ROUTE}/templates/vpcs/{uuid_response}")
    assert response.status_code == status.HTTP_200_OK


async def test_template_vpc_invalid_cidr(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when the VPC CIDR is invalid."""
    invalid_payload = copy.deepcopy(valid_vpc_payload)
    invalid_payload["cidr"] = "192.168.300.0/24"
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_vpc_invalid_subnet_cidr(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when the VPC subnet CIDR is invalid."""
    invalid_payload = copy.deepcopy(valid_vpc_payload)
    invalid_payload["subnets"][0]["cidr"] = "192.168.300.0/24"
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_vpc_invalid_vpc_subnet_cidr_contain(
    auth_client: AsyncClient,
) -> None:
    """Test that we get a 422 response when the subnet CIDR is not contained in the VPC CIDR."""
    invalid_payload = copy.deepcopy(valid_vpc_payload)

    # VPC CIDR
    invalid_payload["cidr"] = "192.168.0.0/16"

    # Subnet CIDR
    invalid_payload["subnets"][0]["cidr"] = "172.16.1.0/24"

    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_vpc_get_vpc(auth_client: AsyncClient) -> None:
    """Test that we can retrieve the correct VPC after saving it in the database."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=valid_vpc_payload
    )
    assert response.status_code == status.HTTP_200_OK

    vpc_id = response.json()["id"]

    response = await auth_client.get(f"{BASE_ROUTE}/templates/vpcs/{vpc_id}")
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    expected_response = {"id": vpc_id, **valid_vpc_payload}
    assert response.json() == expected_response


async def test_template_vpc_get_nonexistent_vpc(auth_client: AsyncClient) -> None:
    """Test that we get a 404 error when requesting a nonexistent vpc in the database."""
    nonexistent_vpc_id = uuid.uuid4()
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/vpcs/{nonexistent_vpc_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_vpc_delete(auth_client: AsyncClient) -> None:
    """Test that we can sucessfully delete a VPC template."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=valid_vpc_payload
    )
    assert response.status_code == status.HTTP_200_OK

    vpcs_id = response.json()["id"]

    # Delete VPC
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/vpcs/{vpcs_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check that VPC is no longer in database
    response = await auth_client.get(f"{BASE_ROUTE}/templates/vpcs/{vpcs_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_vpc_delete_invalid_uuid(auth_client: AsyncClient) -> None:
    """Test that we get a 400 when providing an invalid UUID4."""
    invalid_uuid = str(uuid.uuid4())[:-1]
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/vpcs/{invalid_uuid}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "uuid" in str(response.json()["detail"]).lower()


async def test_template_vpc_delete_non_existent(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when trying to delete a nonexistent VPC template."""
    random_uuid = str(uuid.uuid4())
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/vpcs/{random_uuid}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_vpc_delete_non_standalone(auth_client: AsyncClient) -> None:
    """Test that we get a 409 when trying to delete a non-standalone VPC template."""
    # Get all existing subnets
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/vpcs?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        existing_vpc_template_id = [subnet["id"] for subnet in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        existing_vpc_template_id = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    # Add a range template
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK

    # Find new VPC template
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/vpcs?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK

    new_vpc_template_id = ""
    for vpc in response.json():
        if vpc["id"] not in existing_vpc_template_id:
            new_vpc_template_id = vpc["id"]
            break
    assert new_vpc_template_id

    # Try to delete non-standalone VPC template
    response = await auth_client.delete(
        f"{BASE_ROUTE}/templates/vpcs/{new_vpc_template_id}"
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "standalone" in str(response.json()["detail"]).lower()


async def test_template_vpc_delete_cascade_subnets_and_hosts(
    auth_client: AsyncClient,
) -> None:
    """Test that when we delete a subnet template it cascades and deletes the associated hosts."""
    # Get all existing hosts
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        existing_host_template_id = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        existing_host_template_id = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    # Get all existing subnets
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        existing_subnet_template_id = [subnet["id"] for subnet in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        existing_subnet_template_id = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    # Add a VPC template
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=valid_vpc_payload
    )
    assert response.status_code == status.HTTP_200_OK

    vpc_id = response.json()["id"]

    # Find new host template
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK

    new_host_template_id = ""
    for host in response.json():
        if host["id"] not in existing_host_template_id:
            new_host_template_id = host["id"]
            break
    assert new_host_template_id

    # Find new subnet template
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK

    new_subnet_template_id = ""
    for subnet in response.json():
        if subnet["id"] not in existing_subnet_template_id:
            new_subnet_template_id = subnet["id"]
            break
    assert new_subnet_template_id

    # Delete standalone VPC template
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/vpcs/{vpc_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check to see if dependent subnet template was removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        leftover_subnet_template_ids = [subnet["id"] for subnet in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        leftover_subnet_template_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert new_subnet_template_id not in leftover_subnet_template_ids

    # Check to see if the dependent host template was removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        leftover_host_template_ids = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        leftover_host_template_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert new_host_template_id not in leftover_host_template_ids


async def test_template_subnet_valid_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 reponse and a valid uuid.UUID4 in response."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/subnets", json=valid_subnet_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    # Validate UUID returned
    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response


async def test_template_subnet_get_subnet_invalid_uuid(
    auth_client: AsyncClient,
) -> None:
    """Test that we get a 400 when providing an invalid UUID4."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/subnets", json=valid_subnet_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]
    uuid_response = response.json()["id"]

    # Test that the invalid UUID doesn't work
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets/{uuid_response[:-1]}"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "uuid" in str(response.json()["detail"]).lower()  # Mentions the UUID

    # Test that the valid UUID still works
    response = await auth_client.get(f"{BASE_ROUTE}/templates/subnets/{uuid_response}")
    assert response.status_code == status.HTTP_200_OK


async def test_template_subnet_invalid_subnet_cidr(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when the subnet CIDR is invalid."""
    invalid_payload = copy.deepcopy(valid_subnet_payload)
    invalid_payload["cidr"] = "192.168.300.0/24"
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/subnets", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_subnet_too_many_hosts(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when more hosts in subnet than CIDR allows."""
    invalid_payload = copy.deepcopy(valid_subnet_payload)
    invalid_payload["cidr"] = "192.168.1.0/31"  # Maximum 2 hosts

    # Add extra hosts
    for i in range(3):
        copy_host = copy.deepcopy(invalid_payload["hosts"][0])
        copy_host["hostname"] = copy_host["hostname"] + str(i)
        invalid_payload["hosts"].append(copy_host)

    max_hosts_allowed = 2
    assert len(invalid_payload["hosts"]) > max_hosts_allowed

    # Request
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/subnets", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_template_subnet_get_subnet(auth_client: AsyncClient) -> None:
    """Test that we can retrieve the correct subnet after saving it in the database."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/subnets", json=valid_subnet_payload
    )
    assert response.status_code == status.HTTP_200_OK

    subnet_id = response.json()["id"]

    response = await auth_client.get(f"{BASE_ROUTE}/templates/subnets/{subnet_id}")
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    expected_response = {"id": subnet_id, **valid_subnet_payload}
    assert response.json() == expected_response


async def test_template_subnet_get_nonexistent_subnet(auth_client: AsyncClient) -> None:
    """Test that we get a 404 error when requesting a nonexistent subnet in the database."""
    nonexistent_subnet_id = uuid.uuid4()
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets/{nonexistent_subnet_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_subnet_delete(auth_client: AsyncClient) -> None:
    """Test that we can sucessfully delete a subnet template."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/subnets", json=valid_subnet_payload
    )
    assert response.status_code == status.HTTP_200_OK

    subnet_id = response.json()["id"]

    # Delete host
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/subnets/{subnet_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check that host is no longer in database
    response = await auth_client.get(f"{BASE_ROUTE}/templates/subnets/{subnet_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_subnet_delete_invalid_uuid(auth_client: AsyncClient) -> None:
    """Test that we get a 400 when providing an invalid UUID4."""
    invalid_uuid = str(uuid.uuid4())[:-1]
    response = await auth_client.delete(
        f"{BASE_ROUTE}/templates/subnets/{invalid_uuid}"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "uuid" in str(response.json()["detail"]).lower()


async def test_template_subnet_delete_non_existent(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when trying to delete a nonexistent subnet template."""
    random_uuid = str(uuid.uuid4())
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/subnets/{random_uuid}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_subnet_delete_non_standalone(auth_client: AsyncClient) -> None:
    """Test that we get a 409 when trying to delete a non-standalone subnet template."""
    # Get all existing subnets
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        existing_subnet_template_id = [subnet["id"] for subnet in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        existing_subnet_template_id = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    # Add a VPC template
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/vpcs", json=valid_vpc_payload
    )
    assert response.status_code == status.HTTP_200_OK

    # Find new subnet template
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/subnets?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK

    new_subnet_template_id = ""
    for subnet in response.json():
        if subnet["id"] not in existing_subnet_template_id:
            new_subnet_template_id = subnet["id"]
            break
    assert new_subnet_template_id

    # Try to delete non-standalone host template
    response = await auth_client.delete(
        f"{BASE_ROUTE}/templates/subnets/{new_subnet_template_id}"
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "standalone" in str(response.json()["detail"]).lower()


async def test_template_subnet_delete_cascade_hosts(auth_client: AsyncClient) -> None:
    """Test that when we delete a subnet template it cascades and deletes the associated hosts."""
    # Get all existing hosts
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        existing_host_template_id = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        existing_host_template_id = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    # Add a subnet template
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/subnets", json=valid_subnet_payload
    )
    assert response.status_code == status.HTTP_200_OK

    subnet_id = response.json()["id"]

    # Find new host template
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK

    new_host_template_id = ""
    for host in response.json():
        if host["id"] not in existing_host_template_id:
            new_host_template_id = host["id"]
            break
    assert new_host_template_id

    # Delete standalone subnet template
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/subnets/{subnet_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check to see if the dependent host template was also removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        leftover_host_template_ids = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        leftover_host_template_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert new_host_template_id not in leftover_host_template_ids


async def test_template_host_valid_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 reponse and a valid uuid.UUID4 in response."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/hosts", json=valid_host_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]

    # Validate UUID returned
    uuid_response = response.json()["id"]
    uuid_obj = uuid.UUID(uuid_response, version=4)
    assert str(uuid_obj) == uuid_response


async def test_template_host_get_host_invalid_uuid(auth_client: AsyncClient) -> None:
    """Test that we get a 400 when providing an invalid UUID4."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/hosts", json=valid_host_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"]
    uuid_response = response.json()["id"]

    # Test that the invalid UUID doesn't work
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts/{uuid_response[:-1]}"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "uuid" in str(response.json()["detail"]).lower()  # Mentions the UUID

    # Test that the valid UUID still works
    response = await auth_client.get(f"{BASE_ROUTE}/templates/hosts/{uuid_response}")
    assert response.status_code == status.HTTP_200_OK


async def test_template_host_get_host(auth_client: AsyncClient) -> None:
    """Test that we can retrieve the correct host after saving it in the database."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/hosts", json=valid_host_payload
    )
    assert response.status_code == status.HTTP_200_OK

    host_id = response.json()["id"]

    response = await auth_client.get(f"{BASE_ROUTE}/templates/hosts/{host_id}")
    assert response.status_code == status.HTTP_200_OK

    # Add id to JSON to mimic GET response
    expected_response = {"id": host_id, **valid_host_payload}
    assert response.json() == expected_response


async def test_template_host_get_nonexistent_host(auth_client: AsyncClient) -> None:
    """Test that we get a 404 error when requesting a nonexistent host in the database."""
    nonexistent_host_id = uuid.uuid4()
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts/{nonexistent_host_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_user_cant_access_other_templates(
    client: AsyncClient, auth_client: AsyncClient
) -> None:
    """Test that we get a 404 response when trying to access another user's templates."""
    # Add a range
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK

    response = await auth_client.get(f"{BASE_ROUTE}/templates/ranges")
    assert response.status_code == status.HTTP_200_OK
    template_ids = {t["id"] for t in response.json()}

    new_user_register_payload = copy.deepcopy(user_register_payload)
    new_user_register_payload["email"] = "test-templates-2@ufsit.club"

    response = await client.post(
        f"{BASE_ROUTE}/auth/register", json=new_user_register_payload
    )
    assert response.status_code == status.HTTP_200_OK

    response = await client.post(
        f"{BASE_ROUTE}/auth/login", json=new_user_register_payload
    )
    assert response.status_code == status.HTTP_200_OK

    # Ensure that new cookies get sent
    for cookie in client.cookies.jar:
        cookie.secure = False

    response = await client.post(
        f"{BASE_ROUTE}/templates/ranges", json=valid_range_payload
    )
    assert response.status_code == status.HTTP_200_OK

    response = await client.get(f"{BASE_ROUTE}/templates/ranges")
    new_template_ids = {t["id"] for t in response.json()}

    assert template_ids.isdisjoint(new_template_ids)

    for template_id in template_ids:
        response = await client.get(f"{BASE_ROUTE}/templates/ranges/{template_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_host_delete(auth_client: AsyncClient) -> None:
    """Test that we get can successfully delete host templates."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/hosts", json=valid_host_payload
    )
    assert response.status_code == status.HTTP_200_OK

    host_id = response.json()["id"]

    # Delete host
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/hosts/{host_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True  # Strict check for true

    # Check that host is no longer in database
    response = await auth_client.get(f"{BASE_ROUTE}/templates/hosts/{host_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_host_delete_invalid_uuid(auth_client: AsyncClient) -> None:
    """Test that we get a 400 when providing an invalid UUID4."""
    invalid_uuid = str(uuid.uuid4())[:-1]
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/hosts/{invalid_uuid}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "uuid" in str(response.json()["detail"]).lower()


async def test_template_host_delete_non_existent(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when trying to delete a nonexistent host."""
    random_uuid = str(uuid.uuid4())
    response = await auth_client.delete(f"{BASE_ROUTE}/templates/hosts/{random_uuid}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_template_host_delete_non_standalone(auth_client: AsyncClient) -> None:
    """Test that we get a 409 when trying to delete a non-standalone template."""
    # Get all existing hosts
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        existing_host_template_id = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        existing_host_template_id = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    # Add a subnet template
    response = await auth_client.post(
        f"{BASE_ROUTE}/templates/subnets", json=valid_subnet_payload
    )
    assert response.status_code == status.HTTP_200_OK

    # Find new host template
    response = await auth_client.get(
        f"{BASE_ROUTE}/templates/hosts?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK

    new_host_template_id = ""
    for host in response.json():
        if host["id"] not in existing_host_template_id:
            new_host_template_id = host["id"]
            break
    assert new_host_template_id

    # Try to delete non-standalone host template
    response = await auth_client.delete(
        f"{BASE_ROUTE}/templates/hosts/{new_host_template_id}"
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "standalone" in str(response.json()["detail"]).lower()
