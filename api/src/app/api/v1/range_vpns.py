import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_jobs import add_job
from ...crud.crud_ranges import get_deployed_range
from ...crud.crud_vpns import get_vpn_client, get_vpn_clients
from ...enums.job_status import JobSubmissionDetail
from ...models.user_model import UserModel
from ...schemas.job_schemas import (
    JobCreateSchema,
    JobSubmissionResponseSchema,
)
from ...schemas.vpn_client_schemas import VPNClientCreateRequest, VPNClientSchema
from ...utils.api_utils import create_file_download_response
from ...utils.job_utils import enqueue_arq_job
from ...utils.vpn_utils import generate_vpn_client_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ranges", tags=["ranges", "vpns"])


@router.post("/{range_id}/vpn_clients", status_code=status.HTTP_202_ACCEPTED)
async def create_vpn_client_endpoint(
    range_id: int,
    client_request: VPNClientCreateRequest,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> JobSubmissionResponseSchema:
    """Create new VPN client."""
    deployed_range = await get_deployed_range(
        db, range_id, current_user.id, current_user.is_admin
    )
    if not deployed_range:
        logger.info(
            "Failed to retrieve deployed range: %s VPN configuration for user: %s (%s).",
            range_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to retrieve range VPN clients. Deployed range with ID: {range_id} not found or you don't have access to it!",
        )

    # Queue VPN client job
    job_name = "add_vpn_client"

    arq_job_id = await enqueue_arq_job(
        job_name,
        range_id,
        client_request.name,
        user_id=current_user.id,
    )
    if not arq_job_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed queue up job! Try again later.",
        )

    # Pre-fetch/save data for logging incase of a database error
    current_user_email = current_user.email
    current_user_id = current_user.id

    try:
        job_to_add = JobCreateSchema.create_queued(
            arq_job_id=arq_job_id, job_name=job_name
        )
        await add_job(db, job_to_add, current_user.id)
        detail_message = JobSubmissionDetail.DB_SAVE_SUCCESS
    except Exception:
        logger.warning(
            "Failed to save %s job with ARQ ID: %s to database on behalf of user: %s (%s)!",
            job_name,
            arq_job_id,
            current_user_email,
            current_user_id,
        )
        detail_message = JobSubmissionDetail.DB_SAVE_FAILURE

    return JobSubmissionResponseSchema(arq_job_id=arq_job_id, detail=detail_message)


@router.get("/{range_id}/vpn_clients")
async def get_vpn_clients_endpoint(
    range_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[VPNClientSchema]:
    """Get a list of all VPN clients for a specific deployed range.

    Args:
    ----
        range_id (int): ID of the deployed range.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[VPNClientSchema]: A list of VPN client configurations.

    """
    vpn_clients = await get_vpn_clients(
        db, range_id, current_user.id, current_user.is_admin
    )

    if not vpn_clients:
        logger.info(
            "No VPN clients found for range_id: %s for user: %s (%s).",
            range_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No VPN clients found for range ID: {range_id}. The range may not exist, "
                "you may not have access, or no clients have been created yet."
            ),
        )

    logger.info(
        "Successfully retrieved %s VPN clients for range_id: %s for user: %s (%s).",
        len(vpn_clients),
        range_id,
        current_user.email,
        current_user.id,
    )

    return vpn_clients


# @router.get("{range_id}/vpn_clients/{client_id}")
# async def get_vpn_client_endpoint(
#     range_id: int,
#     client_id: int,
#     db: AsyncSession = Depends(async_get_db),  # noqa: B008
#     current_user: UserModel = Depends(get_current_user),  # noqa: B008
# ) -> list[AnyVPNClient]:
#     pass


@router.get("/{range_id}/vpn_clients/{client_id}/config")
async def get_vpn_client_config_endpoint(
    range_id: int,
    client_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> Response:
    """Get a specific VPN client configuration by its ID.

    Args:
    ----
        range_id (int): ID of the deployed range.
        client_id (int): ID of the VPN client.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        VPNClientSchema: The requested VPN client configuration.

    """
    vpn_client = await get_vpn_client(
        db, client_id, current_user.id, current_user.is_admin
    )

    # Ensure the client exists AND belongs to the range specified in the URL.
    if not vpn_client or vpn_client.range_id != range_id:
        logger.info(
            "Failed to retrieve VPN client_id: %s for range_id: %s for user: %s (%s).",
            client_id,
            range_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"VPN client with ID: {client_id} not found within range ID: {range_id}, "
                "or you don't have access to it."
            ),
        )

    deployed_range = await get_deployed_range(
        db, range_id, current_user.id, current_user.is_admin
    )
    if not deployed_range:
        logger.error(
            "VPN client associated range: %s not found for user: %s",
            range_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated range was not found or you do not have permissions!",
        )

    config_content = generate_vpn_client_config(vpn_client, deployed_range)

    logger.info(
        "Successfully retrieved VPN client_id: %s for user: %s (%s).",
        client_id,
        current_user.email,
        current_user.id,
    )

    return create_file_download_response(
        content=config_content, filename=f"{vpn_client.name}.conf"
    )


# @router.delete("/{range_id}/vpn_clients/{client_id}")
# async def delete_vpn_client_endpoint() -> None:
#     pass
