import logging

import arq.jobs as arq_job
from fastapi import APIRouter, HTTPException, status
from redis.asyncio import Redis

from ...core.utils import queue
from ...schemas.job import JobInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job_info(job_id: str) -> JobInfo:
    """Return both status and job meta information for the requested job, including the result if available.

    Args:
    ----
        job_id (str): ID of the job.

    Returns:
    -------
        JobInfo: Information about, including status, of the requested job.

    """
    if not isinstance(queue.pool, Redis):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect to the task queue!",
        )

    job = arq_job.Job(job_id, queue.pool)

    # Fetches result as well if available
    job_info = await job.info()

    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find job with ID: {job_id}",
        )

    # Convert the ARQ JobDef or JobResult object to a dictionary for modification.
    job_data = dict(vars(job_info))

    # Add the status, which is not part of the info() result.
    job_data["status"] = await job.status()

    # If job fails the result is a Python exception object
    # so we need to convert it to string to make it
    # serializable
    if not getattr(job_info, "success", True):
        if job_info.result:
            job_data["result"] = str(job_info.result)
        else:
            job_data["result"] = "Job failed without returning a specific exception."

    return JobInfo.model_validate(job_data)
