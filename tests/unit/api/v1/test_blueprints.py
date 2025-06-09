import copy
import random
import string

import pytest
from fastapi import status
from httpx import AsyncClient

from src.app.models.range_models import BlueprintRangeModel
from tests.conftest import authenticate_client, remove_key_recursively

from .config import (
    BASE_ROUTE,
    valid_blueprint_host_create_payload,
    valid_blueprint_range_create_payload,
    valid_blueprint_range_multi_create_payload,
    valid_blueprint_subnet_create_payload,
    valid_blueprint_subnet_multi_create_payload,
    valid_blueprint_vpc_create_payload,
    valid_blueprint_vpc_multi_create_payload,
)

###### Test /blueprints/ranges #######


async def test_blueprint_range_get_all_empty_list(
    client: AsyncClient,
) -> None:
    """Test that we get a 404 response when there are no range blueprints."""
    assert await authenticate_client(client)
    response = await client.get(f"{BASE_ROUTE}/blueprints/ranges")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_vpc_get_all_empty_list(auth_client: AsyncClient) -> None:
    """Test that we get a 404 response when there are no vpc blueprints."""
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/vpcs")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_subnet_get_all_empty_list(auth_client: AsyncClient) -> None:
    """Test that we get a 404 response when there are no subnet blueprints."""
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/subnets")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_host_get_all_empty_list(auth_client: AsyncClient) -> None:
    """Test that we get a 404 response when there are no host blueprints."""
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/hosts")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_range_get_non_empty_list(client: AsyncClient) -> None:
    """Test all blueprints to see that we get a 200 response and that correct IDs exist."""
    assert await authenticate_client(client)

    # Add blueprint
    response = await client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    # Retrieve blueprint
    response = await client.get(f"{BASE_ROUTE}/blueprints/ranges")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    recieved_range = response.json()[0]
    assert recieved_range["id"] == blueprint_id

    # Validate response
    # Mimic the header response with the valid JSON
    valid_blueprint_copy = copy.deepcopy(valid_blueprint_range_create_payload)
    del valid_blueprint_copy["vpcs"]
    remove_key_recursively(
        recieved_range, "id"
    )  # Our creation payload doesn't have IDs
    assert recieved_range == valid_blueprint_copy


async def test_blueprint_all_get_non_standalone_blueprints(
    client: AsyncClient,
) -> None:
    """Test that, after uploading range blueprint previously, we have all non-standalone blueprints."""
    assert await authenticate_client(client)

    # Add a range blueprint
    response = await client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    # Checks VPCs
    response = await client.get(f"{BASE_ROUTE}/blueprints/vpcs?standalone_only=false")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1

    blueprint_vpc = response.json()[0]
    remove_key_recursively(blueprint_vpc, "id")  # Our payload does not have IDs
    expected_vpc = copy.deepcopy(valid_blueprint_vpc_create_payload)
    del expected_vpc["subnets"]  # The endpoint returns headers (no nested attributes)
    assert blueprint_vpc == expected_vpc

    # Check Subnets
    response = await client.get(
        f"{BASE_ROUTE}/blueprints/subnets?standalone_only=false"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1

    blueprint_subnet = response.json()[0]
    remove_key_recursively(blueprint_subnet, "id")  # Our payload does not have IDs
    expected_subnet = copy.deepcopy(valid_blueprint_subnet_create_payload)
    del expected_subnet["hosts"]  # The endpoint returns headers (no nested attributes)
    assert blueprint_subnet == expected_subnet

    # Check Hosts
    response = await client.get(f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1

    blueprint_host = response.json()[0]
    remove_key_recursively(blueprint_host, "id")  # Our payload does not have IDs
    assert blueprint_host == valid_blueprint_host_create_payload


async def test_blueprint_vpc_get_non_empty_list(auth_client: AsyncClient) -> None:
    """Test VPC blueprints to see that we get a 200 response and that correct headers exist."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
    )
    blueprint_id = int(response.json()["id"])
    assert response.status_code == status.HTTP_200_OK

    # Check VPCs
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/vpcs?standalone_only=true"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1
    assert any(blueprint_id == blueprint_vpc["id"] for blueprint_vpc in response.json())

    blueprint_vpc = next(vpc for vpc in response.json() if vpc["id"] == blueprint_id)
    remove_key_recursively(blueprint_vpc, "id")  # Our payload does not have IDs

    expected_vpc = copy.deepcopy(valid_blueprint_vpc_create_payload)
    del expected_vpc["subnets"]  # Endpoint returns headers (no nested attributes)
    assert blueprint_vpc == expected_vpc


async def test_blueprint_subnet_get_non_empty_list(auth_client: AsyncClient) -> None:
    """Test subnet blueprints to see that we get a 200 response and that correct headers exist."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=valid_blueprint_subnet_create_payload
    )
    blueprint_id = int(response.json()["id"])
    assert response.status_code == status.HTTP_200_OK

    # Check subnets
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/subnets?standalone_only=true"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1

    blueprint_subnet = next(
        subnet for subnet in response.json() if subnet["id"] == blueprint_id
    )
    remove_key_recursively(blueprint_subnet, "id")  # Our payload doesn't have IDs

    expected_subnet = copy.deepcopy(valid_blueprint_subnet_create_payload)
    del expected_subnet["hosts"]  # Endpoint returns headers (no nested attributes)
    assert blueprint_subnet == expected_subnet


async def test_blueprint_host_get_non_empty_list(auth_client: AsyncClient) -> None:
    """Test host blueprints to see that we get a 201 response and that correct headers exist."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
    )
    blueprint_id = int(response.json()["id"])
    assert response.status_code == status.HTTP_200_OK

    # Check hosts
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/hosts?standalone_only=true"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1

    blueprint_host = next(
        host for host in response.json() if host["id"] == blueprint_id
    )
    remove_key_recursively(blueprint_host, "id")  # Our payload doesn't have IDs
    assert (
        blueprint_host == valid_blueprint_host_create_payload
    )  # Host has no nested attriutes


async def test_blueprint_range_valid_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 and a valid ID in response."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()["id"])


async def test_blueprint_range_valid_multi_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 and a valid ID in response to a payload with multiple VPCs, subnets, and hosts."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_multi_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()["id"])


async def test_blueprint_range_get_range_invalid_id(auth_client: AsyncClient) -> None:
    """Test that we get a 422 when providing an non-int ID when fetching range blueprints."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    # Test that invalid IDs don't work
    random_str = "".join(
        random.choice(string.ascii_letters)  # noqa: S311
        for i in range(random.randint(1, 10))  # noqa: S311
    )
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/ranges/{random_str}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test that the valid ID still works
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}")
    assert response.status_code == status.HTTP_200_OK


async def test_blueprint_range_invalid_vpc_cidr(auth_client: AsyncClient) -> None:
    """Test for 422 response when VPC CIDR is invalid."""
    # Use deepcopy to ensure all nested dicts are copied
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
    invalid_payload["vpcs"][0][
        "cidr"
    ] = "192.168.300.0/24"  # Assign the invalid CIDR block
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_overlap_vpc_cidr(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when the range's VPC's CIDRs overlap."""
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
    assert len(invalid_payload["vpcs"]) >= 1
    invalid_payload["vpcs"][0]["cidr"] = "192.168.1.0/24"

    # Create overlapping VPC
    overlapping_vpc = copy.deepcopy(invalid_payload["vpcs"][0])
    overlapping_vpc["cidr"] = "192.168.1.0/26"
    overlapping_vpc["name"] = invalid_payload["vpcs"][0]["name"] + "-1"
    overlapping_vpc["subnets"][0]["cidr"] = "192.168.1.0/27"
    invalid_payload["vpcs"].append(overlapping_vpc)

    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_invalid_subnet_cidr(auth_client: AsyncClient) -> None:
    """Test for 422 response when subnet CIDR is invalid."""
    # Use deepcopy to ensure all nested dicts are copied
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
    invalid_payload["vpcs"][0]["subnets"][0][
        "cidr"
    ] = "192.168.300.0/24"  # Assign the invalid CIDR block
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_invalid_vpc_subnet_cidr_contain(
    auth_client: AsyncClient,
) -> None:
    """Test for 422 response when subnet CIDR is not contained in the VPC CIDR."""
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)

    # VPC CIDR
    invalid_payload["vpcs"][0]["cidr"] = "192.168.0.0/16"

    # Subnet CIDR
    invalid_payload["vpcs"][0]["subnets"][0][
        "cidr"
    ] = "172.16.1.0/24"  # Assign the invalid CIDR block

    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_empty_tag(auth_client: AsyncClient) -> None:
    """Test for a 422 response when a tag is empty."""
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
    invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0]["tags"].append("")
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_invalid_provider(auth_client: AsyncClient) -> None:
    """Test for a 422 response when the provider is invalid."""
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
    invalid_payload["provider"] = "invalid_provider"  # Not a valid enum value
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_invalid_hostname(auth_client: AsyncClient) -> None:
    """Test for a 422 response when a hostname is invalid."""
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
    invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0]["hostname"] = "-i-am-invalid"
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_duplicate_vpc_names(auth_client: AsyncClient) -> None:
    """Test for a 422 response when multiple VPCs share the same name."""
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
    invalid_payload["vpcs"].append(
        copy.deepcopy(invalid_payload["vpcs"][0])
    )  # Duplicate the first VPC
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_duplicate_subnet_names(auth_client: AsyncClient) -> None:
    """Test for a 422 response when multiple subnets share the same name."""
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
    invalid_payload["vpcs"][0]["subnets"].append(
        copy.deepcopy(invalid_payload["vpcs"][0]["subnets"][0])
    )
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_duplicate_host_hostnames(
    auth_client: AsyncClient,
) -> None:
    """Test for a 422 response when multiple hosts share the same hostname."""
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
    invalid_payload["vpcs"][0]["subnets"][0]["hosts"].append(
        copy.deepcopy(invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0])
    )
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_get_range(auth_client: AsyncClient) -> None:
    """Test that we can retrieve the correct range after saving it in the database."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    blueprint_id = int(response.json()["id"])

    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}")
    assert response.status_code == status.HTTP_200_OK

    # Check response data
    recieved_blueprint = response.json()
    remove_key_recursively(recieved_blueprint, "id")  # Our payload doesn't have IDs
    assert recieved_blueprint == valid_blueprint_range_create_payload


async def test_blueprint_range_get_nonexistent_range(auth_client: AsyncClient) -> None:
    """Test that we get a 404 error when requesting an nonexistent blueprint range in the database."""
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/ranges/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_range_subnet_too_many_hosts(auth_client: AsyncClient) -> None:
    """Test that we get a 422 error when more hosts in subnet that CIDR allows."""
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
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
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_host_size_too_small(auth_client: AsyncClient) -> None:
    """Test that we get a 422 error when the disk size of a host is too small."""
    invalid_payload = copy.deepcopy(valid_blueprint_range_create_payload)
    invalid_payload["vpcs"][0]["subnets"][0]["hosts"][0]["size"] = 2

    # Request
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_range_delete(auth_client: AsyncClient) -> None:
    """Test that we can sucessfully delete a blueprint range."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    blueprint_id = int(response.json()["id"])

    # Delete blueprint range
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check that range is no longer in database
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_range_delete_invalid_id(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when providing an invalid ID."""
    random_str = "".join(
        random.choice(string.ascii_letters)  # noqa: S311
        for i in range(random.randint(1, 10))  # noqa: S311
    )
    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/ranges/{random_str}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_ramge_delete_non_existent(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when trying to delete a nonexistent blueprint range."""
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/ranges/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_range_delete_non_standalone(
    monkeypatch: pytest.MonkeyPatch, auth_client: AsyncClient
) -> None:
    """Test that we get a 404 when trying to delete a non-standalone range blueprint.

    **Note:** When this test was written, ranges could never be non-standalone. Ranges
    were the highest level blueprint and as a result the is_standalone() method was
    hardcoded to always return True for compatibility. This is why the method is mocked.
    """
    # Patch range model method to return False
    monkeypatch.setattr(BlueprintRangeModel, "is_standalone", lambda self: False)

    # Add a blueprint range
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    blueprint_id = int(response.json()["id"])

    # Delete range
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_range_delete_cascade_single_vpc_subnet_and_host(
    auth_client: AsyncClient,
) -> None:
    """Test that when we delete a range blueprint it cascades and deletes the associated single vpc, subnet, and host."""
    # Add a range blueprint
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_range_id = response.json()["id"]

    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_range_id}"
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_range = response.json()

    # VPC
    assert len(blueprint_range["vpcs"]) == 1
    blueprint_vpc = blueprint_range["vpcs"][0]

    # Subnet
    assert len(blueprint_vpc["subnets"]) == 1
    blueprint_subnet = blueprint_vpc["subnets"][0]

    # Host
    assert len(blueprint_subnet["hosts"]) == 1
    blueprint_host = blueprint_subnet["hosts"][0]

    # Delete standalone range blueprint
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_range["id"]}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check to see if dependent vpc blueprint was removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/vpcs?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_vpc_ids = [vpc["id"] for vpc in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_vpc_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_vpc["id"] not in blueprint_vpc_ids

    # Check to see if dependent subnet blueprint was removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/subnets?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_subnet_ids = [subnet["id"] for subnet in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_subnet_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_subnet["id"] not in blueprint_subnet_ids

    # Check to see if the dependent host blueprint was removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_host_ids = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_host_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_host["id"] not in blueprint_host_ids


async def test_blueprint_range_delete_cascade_multi_vpc_subnet_and_host(
    auth_client: AsyncClient,
) -> None:
    """Test that when we delete range blueprint with multiple vpcs, subnets, and hosts it cascades and deletes the associated vpcs, subnets, and hosts."""
    # Add range blueprint
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_multi_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_range_id = response.json()["id"]

    # Fetch range details
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_range_id}"
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_range = response.json()

    # VPC
    assert len(blueprint_range["vpcs"]) > 1
    blueprint_vpc = random.choice(blueprint_range["vpcs"])  # noqa: S311

    # Subnet
    multi_subnet_vpcs = [
        vpc for vpc in blueprint_range["vpcs"] if len(vpc["subnets"]) > 1
    ]
    assert len(multi_subnet_vpcs) >= 1
    random_vpc = random.choice(multi_subnet_vpcs)  # noqa: S311
    blueprint_subnet = random.choice(random_vpc["subnets"])  # noqa: S311

    # Host
    blueprint_host = random.choice(blueprint_subnet["hosts"])  # noqa: S311

    # Delete range blueprint
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_range["id"]}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check VPC removal
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/vpcs?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_vpc_ids = [vpc["id"] for vpc in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_vpc_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_vpc["id"] not in blueprint_vpc_ids

    # Check Subnet removal
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/subnets?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_subnet_ids = [subnet["id"] for subnet in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_subnet_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_subnet["id"] not in blueprint_subnet_ids

    # Check Host removal
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_host_ids = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_host_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_host["id"] not in blueprint_host_ids


async def test_blueprint_vpc_valid_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 response and a valid ID in response."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()["id"])


async def test_blueprint_vpc_valid_multi_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 response and a valid ID in response with a payload VPC with multiple subnets."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_multi_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()["id"])


async def test_blueprint_vpc_get_vpc_invalid_id(auth_client: AsyncClient) -> None:
    """Test that we get a 422 when providing an invalid non-int ID."""
    random_str = "".join(
        random.choice(string.ascii_letters)  # noqa: S311
        for i in range(random.randint(1, 10))  # noqa: S311
    )

    # Test that the invalid ID doesn't work
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/vpcs/{random_str}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_vpc_invalid_cidr(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when the VPC CIDR is invalid."""
    invalid_payload = copy.deepcopy(valid_blueprint_vpc_create_payload)
    invalid_payload["cidr"] = "192.168.300.0/24"
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_vpc_invalid_public_cidr(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when the VPC CIDR is public."""
    invalid_payload = copy.deepcopy(valid_blueprint_vpc_create_payload)
    invalid_payload["cidr"] = "155.75.140.0/24"
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_vpc_invalid_subnet_cidr(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when the VPC subnet CIDR is invalid."""
    invalid_payload = copy.deepcopy(valid_blueprint_vpc_create_payload)
    assert len(invalid_payload["subnets"]) >= 1
    invalid_payload["subnets"][0]["cidr"] = "192.168.300.0/24"
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_vpc_overlap_subnet_cidr(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when the VPC subnet's CIDRs overlap."""
    invalid_payload = copy.deepcopy(valid_blueprint_vpc_create_payload)
    assert len(invalid_payload["subnets"]) >= 1
    invalid_payload["subnets"][0]["cidr"] = "192.168.1.0/24"

    # Create overlapping subnet
    overlapping_subnet = copy.deepcopy(invalid_payload["subnets"][0])
    overlapping_subnet["cidr"] = "192.168.1.0/26"
    overlapping_subnet["name"] = invalid_payload["subnets"][0]["name"] + "-1"
    invalid_payload["subnets"].append(overlapping_subnet)

    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_vpc_invalid_vpc_subnet_cidr_contain(
    auth_client: AsyncClient,
) -> None:
    """Test that we get a 422 response when the subnet CIDR is not contained in the VPC CIDR."""
    invalid_payload = copy.deepcopy(valid_blueprint_vpc_create_payload)

    # VPC CIDR
    invalid_payload["cidr"] = "192.168.0.0/16"

    # Subnet CIDR
    assert len(invalid_payload["subnets"]) >= 1
    invalid_payload["subnets"][0]["cidr"] = "172.16.1.0/24"

    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_vpc_get_vpc(auth_client: AsyncClient) -> None:
    """Test that we can retrieve the correct VPC after saving it in the database."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    vpc_id = int(response.json()["id"])

    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}")
    assert response.status_code == status.HTTP_200_OK

    # Validate response
    recieved_vpc = response.json()
    remove_key_recursively(recieved_vpc, "id")  # Our payload doesn't have IDs
    assert recieved_vpc == valid_blueprint_vpc_create_payload


async def test_blueprint_vpc_get_nonexistent_vpc(auth_client: AsyncClient) -> None:
    """Test that we get a 404 error when requesting a nonexistent vpc blueprint in the database."""
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/vpcs/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_vpc_delete(auth_client: AsyncClient) -> None:
    """Test that we can sucessfully delete a VPC blueprint."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    vpc_id = int(response.json()["id"])

    # Delete VPC
    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}")
    assert response.status_code == status.HTTP_200_OK

    # Check that VPC is no longer in database
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_vpc_delete_invalid_id(auth_client: AsyncClient) -> None:
    """Test that we get a 422 when providing an invalid non-int ID."""
    random_str = "".join(
        random.choice(string.ascii_letters)  # noqa: S311
        for i in range(random.randint(1, 10))  # noqa: S311
    )
    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/vpcs/{random_str}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_vpc_delete_non_existent(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when trying to delete a nonexistent VPC blueprint."""
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/vpcs/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_vpc_delete_non_standalone(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when trying to delete a non-standalone VPC blueprint part of a range blueprint."""
    # Add a range blueprint
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_range_id = response.json()["id"]

    # Fetch full range details
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/ranges/{blueprint_range_id}"
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_range = response.json()

    # Get dependent VPC blueprint id
    assert len(blueprint_range["vpcs"]) >= 1
    blueprint_vpc_id = blueprint_range["vpcs"][0]["id"]

    # Attempt to delete non-standalone VPC blueprint
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_vpc_id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_vpc_delete_cascade_single_subnet_and_host(
    auth_client: AsyncClient,
) -> None:
    """Test that when we delete a VPC blueprint it cascades and deletes the associated hosts."""
    # Add a blueprint VPC
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    vpc_id = int(response.json()["id"])

    # Fetch VPC details
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}")
    blueprint_vpc = response.json()

    # Get new subnet ID
    assert len(blueprint_vpc["subnets"]) >= 1
    blueprint_subnet = blueprint_vpc["subnets"][0]
    blueprint_subnet_id = blueprint_subnet["id"]

    # Get new Host ID
    assert len(blueprint_subnet["hosts"]) >= 1
    blueprint_host = blueprint_subnet["hosts"][0]
    blueprint_host_id = blueprint_host["id"]

    # Delete standalone blueprint VPC
    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/vpcs/{vpc_id}")
    assert response.status_code == status.HTTP_200_OK

    # Check to see if dependent subnet blueprint was removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/subnets?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_subnet_ids = [subnet["id"] for subnet in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_subnet_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_subnet_id not in blueprint_subnet_ids

    # Check to see if the dependent host blueprint was removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_host_ids = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_host_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_host_id not in blueprint_host_ids


async def test_blueprint_vpc_delete_cascade_multi_subnet_and_host(
    auth_client: AsyncClient,
) -> None:
    """Test that when we delete VPC blueprint with multiple subnets and hosts it cascades and deletes the associated subnets and hosts."""
    # Add VPC blueprint
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs",
        json=valid_blueprint_vpc_multi_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_vpc_id = response.json()["id"]

    # Fetch VPC details
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_vpc_id}")
    assert response.status_code == status.HTTP_200_OK
    blueprint_vpc = response.json()

    # Subnet
    multi_host_subnets = [
        subnet for subnet in blueprint_vpc["subnets"] if len(subnet["hosts"]) > 1
    ]
    assert len(multi_host_subnets) >= 1
    blueprint_subnet = random.choice(multi_host_subnets)  # noqa: S311

    # Host
    blueprint_host = random.choice(blueprint_subnet["hosts"])  # noqa: S311

    # Delete VPC blueprint
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_vpc["id"]}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check Subnet removal
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/subnets?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_subnet_ids = [subnet["id"] for subnet in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_subnet_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_subnet["id"] not in blueprint_subnet_ids

    # Check Host removal
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_host_ids = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_host_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_host["id"] not in blueprint_host_ids


async def test_blueprint_subnet_valid_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 reponse and a valid ID in response."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=valid_blueprint_subnet_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()["id"])


async def test_blueprint_subnet_valid_multi_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 response and a valid ID response when submitting a subnet with multiple hosts."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=valid_blueprint_subnet_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()["id"])


async def test_blueprint_subnet_get_subnet_invalid_id(
    auth_client: AsyncClient,
) -> None:
    """Test that we get a 422 when providing an invalid ID."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=valid_blueprint_subnet_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    # Test invalid ID
    random_str = "".join(
        random.choice(string.ascii_letters)  # noqa: S311
        for i in range(random.randint(1, 10))  # noqa: S311
    )
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/subnets/{random_str}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test that the valid ID still works
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}")
    assert response.status_code == status.HTTP_200_OK


async def test_blueprint_subnet_invalid_subnet_cidr(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when the subnet CIDR is invalid."""
    invalid_payload = copy.deepcopy(valid_blueprint_subnet_create_payload)
    invalid_payload["cidr"] = "192.168.300.0/24"
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_subnet_invalid_public_cidr(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when the subnet CIDR is public."""
    invalid_payload = copy.deepcopy(valid_blueprint_subnet_create_payload)
    invalid_payload["cidr"] = "155.76.15.0/24"
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprints_subnet_too_many_hosts(auth_client: AsyncClient) -> None:
    """Test that we get a 422 response when more hosts in subnet than CIDR allows."""
    invalid_payload = copy.deepcopy(valid_blueprint_subnet_create_payload)
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
        f"{BASE_ROUTE}/blueprints/subnets", json=invalid_payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprints_subnet_get_subnet(auth_client: AsyncClient) -> None:
    """Test that we can retrieve the correct subnet after saving it in the database."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=valid_blueprint_subnet_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = response.json()["id"]

    # Retrieve new subnet
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}")
    assert response.status_code == status.HTTP_200_OK
    recieved_subnet = response.json()

    # Validate reponse
    remove_key_recursively(recieved_subnet, "id")  # Our payload doesn't have IDs
    assert recieved_subnet == valid_blueprint_subnet_create_payload


async def test_blueprint_subnet_get_nonexistent_subnet(
    auth_client: AsyncClient,
) -> None:
    """Test that we get a 404 error when requesting a nonexistent subnet in the database."""
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/subnets/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_subnet_delete(auth_client: AsyncClient) -> None:
    """Test that we can sucessfully delete a subnet blueprint."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=valid_blueprint_subnet_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    # Delete subnet
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check that subnet is no longer in database
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_subnet_delete_invalid_id(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when providing an invalid non-int ID."""
    random_str = "".join(
        random.choice(string.ascii_letters)  # noqa: S311
        for i in range(random.randint(1, 10))  # noqa: S311
    )
    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/subnets/{random_str}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_subnet_delete_non_standalone(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when trying to delete a non-standalone blueprint subnet."""
    # Add a blueprint VPC
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/vpcs", json=valid_blueprint_vpc_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_vpc_id = response.json()["id"]

    # Fetch VPC details
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/vpcs/{blueprint_vpc_id}")
    assert response.status_code == status.HTTP_200_OK
    blueprint_vpc = response.json()

    # New subnet blueprint
    assert len(blueprint_vpc["subnets"]) >= 1
    blueprint_subnet = blueprint_vpc["subnets"][0]

    # Try to delete non-standalone blueprint subnet
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/subnets/{blueprint_subnet["id"]}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_subnet_delete_cascade_single_host(
    auth_client: AsyncClient,
) -> None:
    """Test that when we delete a subnet blueprint it cascades and deletes the associated host."""
    # Add a subnet blueprint
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=valid_blueprint_subnet_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    # Get Subnet details
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}")
    assert response.status_code == status.HTTP_200_OK
    blueprint_subnet = response.json()

    # New host blueprint
    assert len(blueprint_subnet["hosts"]) >= 1
    blueprint_host = blueprint_subnet["hosts"][0]

    # Delete standalone subnet blueprint
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/subnets/{blueprint_id}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check to see if the dependent host blueprint was also removed
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_host_ids = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_host_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert blueprint_host["id"] not in blueprint_host_ids


async def test_blueprint_vpc_delete_cascade_multi_hosts(
    auth_client: AsyncClient,
) -> None:
    """Test that when we delete subnet blueprint with multiple hosts it cascades and deletes the associated hosts."""
    # Add subnet blueprint
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets",
        json=valid_blueprint_subnet_multi_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_subnet_id = response.json()["id"]

    # Fetch subnet details
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/subnets/{blueprint_subnet_id}"
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_subnet = response.json()

    # Hosts
    blueprint_hosts = blueprint_subnet["hosts"]

    # Delete subnet blueprint
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/subnets/{blueprint_subnet["id"]}"
    )
    assert response.status_code == status.HTTP_200_OK

    # Check host removal
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/hosts?standalone_only=false"
    )

    if response.status_code == status.HTTP_200_OK:
        blueprint_host_ids = [host["id"] for host in response.json()]
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        blueprint_host_ids = []
    else:
        pytest.fail(f"Unknown status code: {response.status_code} recieved!")

    assert not any(
        blueprint_host["id"] in blueprint_host_ids for blueprint_host in blueprint_hosts
    )


async def test_blueprint_host_valid_payload(auth_client: AsyncClient) -> None:
    """Test that we get a 200 reponse and a valid ID in response."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    assert int(response.json()["id"])


async def test_blueprint_host_get_host_invalid_id(auth_client: AsyncClient) -> None:
    """Test that we get a 422 when providing an invalid non-int ID."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    # Test that the invalid ID doesn't work
    random_str = "".join(
        random.choice(string.ascii_letters)  # noqa: S311
        for i in range(random.randint(1, 10))  # noqa: S311
    )
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/hosts/{random_str}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test that the valid ID still works
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}")
    assert response.status_code == status.HTTP_200_OK


async def test_blueprint_host_get_host(auth_client: AsyncClient) -> None:
    """Test that we can retrieve the correct host after saving it in the database."""
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    # Get Host
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}")
    assert response.status_code == status.HTTP_200_OK
    recieved_host = response.json()

    # Validate response
    remove_key_recursively(recieved_host, "id")  # Our payload doesn't have IDs
    assert recieved_host == valid_blueprint_host_create_payload


async def test_blueprint_host_get_nonexistent_host(auth_client: AsyncClient) -> None:
    """Test that we get a 404 error when requesting a nonexistent host in the database."""
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/hosts/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_host_duplicate_tags(auth_client: AsyncClient) -> None:
    """Test that we get a 422 error when a host has duplicate tags."""
    dup_tags_host = copy.deepcopy(valid_blueprint_host_create_payload)

    for _ in range(2):
        dup_tags_host["tags"].append("duplicate-tag")

    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/hosts", json=dup_tags_host
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_host_long_tag(auth_client: AsyncClient) -> None:
    """Test that we get a 422 error when a host has a tag that is too long."""
    long_tag_host = copy.deepcopy(valid_blueprint_host_create_payload)

    # Max length 63
    long_tag = "h" + "i" * 75
    long_tag_host["tags"].append(long_tag)

    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/hosts", json=long_tag_host
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_user_cant_access_other_blueprints(
    client: AsyncClient, auth_client: AsyncClient
) -> None:
    """Test that we get a 404 response when trying to access another user's blueprints."""
    # Add a range user1
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/ranges",
        json=valid_blueprint_range_multi_create_payload,
    )
    assert response.status_code == status.HTTP_200_OK

    # Get user1 ranges
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/ranges")
    assert response.status_code == status.HTTP_200_OK
    user1_blueprint_ids = {blueprint["id"] for blueprint in response.json()}

    # Login as new user2
    assert await authenticate_client(client)

    # Add range to user2
    response = await client.post(
        f"{BASE_ROUTE}/blueprints/ranges", json=valid_blueprint_range_create_payload
    )
    assert response.status_code == status.HTTP_200_OK

    # Get user2 ranges
    response = await client.get(f"{BASE_ROUTE}/blueprints/ranges")
    user2_blueprint_ids = {blueprint["id"] for blueprint in response.json()}

    assert user1_blueprint_ids.isdisjoint(user2_blueprint_ids)

    for blueprint_id in user1_blueprint_ids:
        response = await client.get(f"{BASE_ROUTE}/blueprints/ranges/{blueprint_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_host_delete(auth_client: AsyncClient) -> None:
    """Test that we get can successfully delete host blueprints."""
    # Add host
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/hosts", json=valid_blueprint_host_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_id = int(response.json()["id"])

    # Delete host
    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}")
    assert response.status_code == status.HTTP_200_OK

    # Check that host is no longer in database
    response = await auth_client.get(f"{BASE_ROUTE}/blueprints/hosts/{blueprint_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_host_delete_invalid_id(auth_client: AsyncClient) -> None:
    """Test that we get a 422 when providing an invalid non-int ID."""
    random_str = "".join(
        random.choice(string.ascii_letters)  # noqa: S311
        for i in range(random.randint(1, 10))  # noqa: S311
    )
    response = await auth_client.delete(f"{BASE_ROUTE}/blueprints/hosts/{random_str}")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_blueprint_host_delete_non_existent(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when trying to delete a nonexistent host."""
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/hosts/{random.randint(-420, -69)}"  # noqa: S311
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_blueprint_host_delete_non_standalone(auth_client: AsyncClient) -> None:
    """Test that we get a 404 when trying to delete a non-standalone host blueprint."""
    # Add a subnet blueprint
    response = await auth_client.post(
        f"{BASE_ROUTE}/blueprints/subnets", json=valid_blueprint_subnet_create_payload
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_subnet_id = response.json()["id"]

    # Get subnet details
    response = await auth_client.get(
        f"{BASE_ROUTE}/blueprints/subnets/{blueprint_subnet_id}"
    )
    assert response.status_code == status.HTTP_200_OK
    blueprint_subnet = response.json()

    # Get host
    assert len(blueprint_subnet["hosts"]) >= 1
    blueprint_host = blueprint_subnet["hosts"][0]

    # Try to delete non-standalone host blueprint
    response = await auth_client.delete(
        f"{BASE_ROUTE}/blueprints/hosts/{blueprint_host["id"]}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
