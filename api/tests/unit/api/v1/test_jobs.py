import random

from fastapi import status
from httpx import AsyncClient
from pytest_mock import MockerFixture

from src.app.api.v1 import jobs as jobs_api
from src.app.schemas.job_schemas import JobSchema

from .config import BASE_ROUTE, complete_job_payload


async def test_jobs_get_all_jobs(
    mocker: MockerFixture,
    auth_client: AsyncClient,
) -> None:
    """Test that we get a 200 when we have jobs in the database."""
    job_list = [JobSchema.model_validate(complete_job_payload)]
    mocker.patch.object(jobs_api, "get_jobs", return_value=job_list)

    response = await auth_client.get(f"{BASE_ROUTE}/jobs")
    assert response.status_code == status.HTTP_200_OK


async def test_jobs_get_job(
    mocker: MockerFixture,
    auth_client: AsyncClient,
) -> None:
    """Test that we get a 200 when we request a job that exists in the database."""
    job = JobSchema.model_validate(complete_job_payload)
    job.id = random.randint(50, 1000)  # noqa: S311

    mock_get_job = mocker.patch.object(jobs_api, "get_job", return_value=job)

    response = await auth_client.get(f"{BASE_ROUTE}/jobs/{job.id}")
    assert response.status_code == status.HTTP_200_OK

    # Make sure it is requesting the correct job
    mock_get_job.assert_awaited_once()
    assert (
        str(job.id) in mock_get_job.call_args.args
    )  # Ints are converted by FastAPI to strings because we accept int | str
