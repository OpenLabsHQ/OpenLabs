import base64
import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_jobs import add_job
from ...crud.crud_ranges import (
    get_blueprint_range,
    get_deployed_range,
    get_deployed_range_headers,
    get_deployed_range_key,
)
from ...crud.crud_users import get_decrypted_secrets
from ...enums.job_status import JobSubmissionDetail
from ...models.user_model import UserModel
from ...provisioning.pulumi.providers.provider_registry import PROVIDER_REGISTRY
from ...schemas.job_schemas import (
    JobCreateSchema,
    JobSubmissionResponseSchema,
)
from ...schemas.range_schemas import (
    DeployedRangeHeaderSchema,
    DeployedRangeKeySchema,
    DeployedRangeSchema,
    DeployRangeSchema,
)
from ...utils.job_utils import enqueue_arq_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ranges", tags=["ranges"])


@router.get("")
async def get_deployed_range_headers_endpoint(
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[DeployedRangeHeaderSchema]:
    """Get a list of deployed range headers.

    Args:
    ----
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[DeployedRangeHeaderSchema]: List of deployed range headers. For admin users, shows all deployed ranges.
                               For regular users, shows only the ranges they own.

    """
    range_headers = await get_deployed_range_headers(
        db, current_user.id, current_user.is_admin
    )

    if not range_headers:
        logger.info(
            "No deployed range headers found for user: %s (%s)",
            current_user.email,
            current_user.id,
        )
        msg = (
            "No deployed ranges found!"
            if current_user.is_admin
            else "Unable to find any deployed ranges that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )

    logger.info(
        "Successfully retrieved %s deployed range headers for user: %s (%s).",
        len(range_headers),
        current_user.email,
        current_user.id,
    )

    return range_headers


@router.get("/{range_id}")
async def get_deployed_range_endpoint(
    range_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> DeployedRangeSchema:
    """Get a deployed range.

    Args:
    ----
        range_id (int): ID of the deployed range.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        DeployedRangeSchema: Deployed range data from database. Admin users can access any range.

    """
    deployed_range = await get_deployed_range(
        db, range_id, current_user.id, current_user.is_admin
    )

    if not deployed_range:
        logger.info(
            "Failed to retrieve deployed range: %s for user: %s (%s).",
            range_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployed range with ID: {range_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully retrieved deployed range: %s for user: %s (%s).",
        deployed_range.id,
        current_user.email,
        current_user.id,
    )

    return deployed_range


@router.get("/{range_id}/key")
async def get_deployed_range_key_endpoint(
    range_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> DeployedRangeKeySchema:
    """Get range SSH key.

    Args:
    ----
        range_id (int): ID of the deployed range.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        DeployedRangeKeySchema: Range SSH key response schema.

    """
    range_private_key = await get_deployed_range_key(
        db, range_id, current_user.id, current_user.is_admin
    )

    if not range_private_key:
        logger.info(
            "Failed to retrieve deployed range: %s private key for user: %s (%s).",
            range_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to retrieve range private key. Deployed range with ID: {range_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully retrieved deployed range: %s private key for user: %s (%s).",
        range_id,
        current_user.email,
        current_user.id,
    )

    return range_private_key


@router.post("/deploy", status_code=status.HTTP_202_ACCEPTED)
async def deploy_range_from_blueprint_endpoint(
    deploy_request: DeployRangeSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    enc_key: str | None = Cookie(None, alias="enc_key", include_in_schema=False),
) -> JobSubmissionResponseSchema:
    """Deploy range blueprints.

    Args:
    ----
        deploy_request (DeployRangeSchema): Range blueprint to deploy with supporting data.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.
        enc_key (str): Encryption key from cookie for decrypting secrets.

    Returns:
    -------
        JobSubmissionResponseSchema: Job tracking ID and submission details.

    """
    # Check if we have the encryption key needed to decrypt secrets
    if not enc_key:
        logger.info(
            "Did not find encryption key for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Encryption key not found. Please try logging in again.",
        )

    # Decode the encryption key
    try:
        master_key = base64.b64decode(enc_key)
    except Exception as e:
        # Less common and might point to underlying issue
        logger.warning(
            "Failed to decode encryption key for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid encryption key. Please try logging in again.",
        ) from e

    # Fetch range blueprint
    blueprint_range = await get_blueprint_range(
        db, deploy_request.blueprint_id, current_user.id, current_user.is_admin
    )

    if not blueprint_range:
        logger.info(
            "Failed to fetch range blueprint: %s for user: %s (%s).",
            deploy_request.blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range blueprint with ID: {deploy_request.blueprint_id} not found or you don't have access to it!",
        )

    # Get the decrypted credentials
    decrypted_secrets = await get_decrypted_secrets(current_user, db, master_key)
    if not decrypted_secrets:
        logger.warning(
            "Failed to decrypt cloud secrets for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt cloud credentials. Please try logging in again.",
        )

    pulumi_provider = PROVIDER_REGISTRY.get(blueprint_range.provider)
    if not pulumi_provider:
        logger.error(
            "Pulumi provider not available for %s",
            blueprint_range.provider.value.upper(),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{blueprint_range.provider.value.upper()} provider not supported!",
        )

    if not pulumi_provider.has_secrets(decrypted_secrets):
        logger.info(
            "User: %s (%s) does not have credentials for provider: %s. Failed to queue deploy request for range: %s.",
            current_user.email,
            current_user.id,
            blueprint_range.provider.value.upper(),
            deploy_request.name,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No credentials found for provider: {blueprint_range.provider}",
        )

    # Queue deployment job
    job_name = "deploy_range"

    arq_job_id = await enqueue_arq_job(
        job_name,
        enc_key,
        deploy_request.model_dump(mode="json"),
        blueprint_range.model_dump(mode="json"),
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


@router.delete("/{range_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_range_endpoint(
    range_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    enc_key: str | None = Cookie(None, alias="enc_key", include_in_schema=False),
) -> JobSubmissionResponseSchema:
    """Destroy a deployed range.

    Args:
    ----
        range_id (int): ID of deployed range.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.
        enc_key (str): Encryption key from cookie for decrypting secrets.

    Returns:
    -------
        JobSubmissionResponseSchema: Job tracking ID and submission details.

    """
    # Check if we have the encryption key needed to decrypt secrets
    if not enc_key:
        logger.info(
            "Did not find encryption key for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Encryption key not found. Please try logging in again.",
        )

    # Decode the encryption key
    try:
        master_key = base64.b64decode(enc_key)
    except Exception as e:
        logger.warning(
            "Failed to decode encryption key for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid encryption key. Please try logging in again.",
        ) from e

    # Get range from database
    deployed_range = await get_deployed_range(db, range_id, user_id=current_user.id)

    if not deployed_range:
        logger.info(
            "Failed to fetch deployed range: %s for user: %s (%s).",
            range_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range with ID: {range_id} not found or you don't have access to it!",
        )

    # Get the decrypted credentials
    decrypted_secrets = await get_decrypted_secrets(current_user, db, master_key)
    if not decrypted_secrets:
        logger.warning(
            "Failed to decrypt cloud secrets for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt cloud credentials. Please try logging in again.",
        )

    pulumi_provider = PROVIDER_REGISTRY.get(deployed_range.provider)
    if not pulumi_provider:
        logger.error(
            "Pulumi provider not available for %s",
            deployed_range.provider.value.upper(),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{deployed_range.provider.value.upper()} provider not supported!",
        )

    if not pulumi_provider.has_secrets(decrypted_secrets):
        logger.info(
            "User: %s (%s) does not have credentials for provider: %s. Failed to queue destroy request for range: %s.",
            current_user.email,
            current_user.id,
            deployed_range.provider.value.upper(),
            deployed_range.name,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No credentials found for provider: {deployed_range.provider}",
        )

    # Queue deployment job
    job_name = "destroy_range"

    arq_job_id = await enqueue_arq_job(
        job_name,
        enc_key,
        deployed_range.model_dump(mode="json"),
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
