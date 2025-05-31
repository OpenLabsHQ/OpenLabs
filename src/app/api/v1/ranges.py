import base64
import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.cdktf.ranges.range_factory import RangeFactory
from ...core.db.database import async_get_db
from ...crud.crud_ranges import (
    create_deployed_range,
    delete_deployed_range,
    get_blueprint_range,
    get_deployed_range,
    get_deployed_range_headers,
    get_deployed_range_key,
)
from ...crud.crud_users import get_decrypted_secrets
from ...models.user_model import UserModel
from ...schemas.message_schema import MessageSchema
from ...schemas.range_schemas import (
    DeployedRangeHeaderSchema,
    DeployedRangeKeySchema,
    DeployedRangeSchema,
    DeployRangeSchema,
)

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
    db: AsyncSession = Depends(async_get_db),
    current_user: UserModel = Depends(get_current_user),
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


@router.post("/deploy")
async def deploy_range_from_blueprint_endpoint(
    deploy_request: DeployRangeSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    enc_key: str | None = Cookie(None, alias="enc_key", include_in_schema=False),
) -> DeployedRangeHeaderSchema:
    """Deploy range blueprints.

    Args:
    ----
        deploy_request (DeployRangeSchema): Range blueprint to deploy with supporting data.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.
        enc_key (str): Encryption key from cookie for decrypting secrets.

    Returns:
    -------
        DeployedRangeHeaderSchema: Header data for the deployed range including it's ID.

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

    # Create deployable range object
    range_to_deploy = RangeFactory.create_range(
        name=deploy_request.name,
        range_obj=blueprint_range,
        region=deploy_request.region,
        description=deploy_request.description,
        secrets=decrypted_secrets,
    )

    if not range_to_deploy.has_secrets():
        logger.info(
            "Failed to deploy range: %s. User: %s (%s) does not have credentials for provider: %s.",
            deploy_request.name,
            current_user.email,
            current_user.id,
            blueprint_range.provider.value,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No credentials found for provider: {blueprint_range.provider}",
        )

    # Deploy range
    successful_synthesize = range_to_deploy.synthesize()
    if not successful_synthesize:
        logger.error(
            "Failed to synthesize range: %s from blueprint: %s (%s) for user: %s (%s).",
            range_to_deploy.name,
            blueprint_range.name,
            blueprint_range.id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synthesize range: {range_to_deploy.name} from blueprint: {blueprint_range.name} ({blueprint_range.id})!",
        )

    create_deployed_range_schema = range_to_deploy.deploy()
    if not create_deployed_range_schema:
        logger.error(
            "Failed to deploy range: %s from blueprint: %s (%s) for user: %s (%s).",
            range_to_deploy.name,
            blueprint_range.name,
            blueprint_range.id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy range: {range_to_deploy.name} from blueprint: {blueprint_range.name} ({blueprint_range.id})!",
        )

    # Store range in database
    try:
        deployed_range = await create_deployed_range(
            db, create_deployed_range_schema, user_id=current_user.id
        )
    except Exception as e:
        logger.exception(
            "Failed to commit range: %s to database on behalf of user: %s (%s)! Exception: %s",
            range_to_deploy.name,
            current_user.email,
            current_user.id,
            e,
        )

        # Auto clean up resources
        range_to_deploy.synthesize()
        range_to_deploy.destroy()
        raise

    logger.info(
        "Successfully created and deployed range: %s (%s) for user: %s (%s).",
        deployed_range.name,
        deployed_range.id,
        current_user.email,
        current_user.id,
    )

    # Avoid returning lots of data
    return DeployedRangeHeaderSchema.model_validate(deployed_range)


@router.delete("/{range_id}")
async def delete_range_endpoint(
    range_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    enc_key: str | None = Cookie(None, alias="enc_key", include_in_schema=False),
) -> MessageSchema:
    """Destroy a deployed range.

    Args:
    ----
        range_id (int): ID of deployed range.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.
        enc_key (str): Encryption key from cookie for decrypting secrets.

    Returns:
    -------
        MessageSchema: Success message. Error otherwise.

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

    # Build range object
    range_to_destroy = RangeFactory.create_range(
        name=deployed_range.name,
        range_obj=deployed_range,
        region=deployed_range.region,
        description=deployed_range.description,
        secrets=decrypted_secrets,
        state_file=deployed_range.state_file,
    )

    if not range_to_destroy.has_secrets():
        logger.info(
            "Failed to destroy range: %s (%s). User: %s (%s) does not have credentials for provider: %s.",
            deployed_range.name,
            deployed_range.id,
            current_user.email,
            current_user.id,
            deployed_range.provider.value,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No credentials found for provider: {deployed_range.provider}",
        )

    # Destroy range
    successful_synthesize = range_to_destroy.synthesize()
    if not successful_synthesize:
        logger.error(
            "Failed to synthesize range: %s (%s) for user: %s (%s).",
            range_to_destroy.name,
            deployed_range.id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synthesize range: {range_to_destroy.name}!",
        )

    successful_destroy = range_to_destroy.destroy()
    if not successful_destroy:
        logger.error(
            "Failed to destroy range: %s (%s) for user: %s (%s).",
            range_to_destroy.name,
            deployed_range.id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to destroy range: {range_to_destroy.name}!",
        )

    # Delete range from database
    try:
        deleted_from_db = await delete_deployed_range(
            db, range_id, current_user.id, current_user.is_admin
        )
        if not deleted_from_db:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete deployed range in database! Range: {range_to_destroy.name}.",
            )
    except Exception as e:
        logger.exception(
            "Failed to commit range deletion: %s to database on behalf of user: %s (%s)! Exception: %s",
            range_to_destroy.name,
            current_user.email,
            current_user.id,
            e,
        )
        raise

    return MessageSchema(
        message=f"Successfully destroyed range: {range_to_destroy.name} ({range_id})"
    )
