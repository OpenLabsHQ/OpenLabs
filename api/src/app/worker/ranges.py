import asyncio
import base64
import logging
import uuid
from typing import Any

import uvloop

from ..core.db.database import get_db_session_context
from ..crud.crud_ranges import create_deployed_range, delete_deployed_range
from ..crud.crud_users import get_decrypted_secrets, get_user_by_id
from ..enums.range_states import RangeState
from ..provisioning.pulumi.providers.provider_registry import PROVIDER_REGISTRY
from ..provisioning.pulumi.provisioner import PulumiOperation
from ..schemas.range_schemas import (
    BlueprintRangeSchema,
    DeployedRangeSchema,
    DeployRangeSchema,
)
from ..schemas.user_schema import UserID
from ..utils.job_utils import track_job_status

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)


@track_job_status
async def deploy_range(
    ctx: dict[str, Any],
    enc_key: str,
    deploy_request_dump: dict[str, Any],
    blueprint_range_dump: dict[str, Any],
    user_id: int,
) -> dict[str, Any]:
    """Deploy range for a user.

    Args:
    ----
        ctx (dict[str, Any]): ARQ worker context. Automatically provided by ARQ.
        enc_key (str): Base64 encoded master key for user.
        deploy_request_dump (dict[str, Any]): DeployRangeSchema dumped with pydantic's `model_dump(mode='json')`.
        blueprint_range_dump (dict[str, Any]): BlueprintRangeSchema dumped with pydantic's `model_dump(mode='json')`.
        user_id (int): User associated with the deploy request.

    Returns:
    -------
        dict[str, Any]: DeployedRangeHeaderSchema dumped with pydantic's `model_dump(mode='json')`.

    """
    deploy_request = DeployRangeSchema.model_validate(deploy_request_dump)
    blueprint_range = BlueprintRangeSchema.model_validate(blueprint_range_dump)

    logger.info(
        "Starting deployment of range: %s from blueprint: %s (%s) to %s...",
        deploy_request.name,
        blueprint_range.name,
        blueprint_range.id,
        blueprint_range.provider.value.upper(),
    )

    async with get_db_session_context() as db:
        # Fetch user info
        user = await get_user_by_id(db, UserID(id=user_id))
        if not user:
            msg = f"Unable to deploy range! User: {user_id} not found in database."
            logger.error(msg)
            raise ValueError(msg)

        # Fetch all deploy dependencies
        try:
            master_key = base64.b64decode(enc_key)
        except Exception as e:
            msg = f"Unable to deploy range! Failed to decode encryption key for user: {user.email} ({user.id})."
            logger.exception(msg)
            raise RuntimeError(msg) from e

        decrypted_secrets = await get_decrypted_secrets(user, db, master_key)
        if not decrypted_secrets:
            msg = f"Unable to deploy range! Failed to decrypt cloud credentials for user: {user.email} ({user.id})"
            logger.warning(msg)
            raise RuntimeError(msg)

        user_id = user.id
        user_email = user.email

    pulumi_provider = PROVIDER_REGISTRY.get(blueprint_range.provider)
    if not pulumi_provider:
        msg = f"Pulumi provider not available for {blueprint_range.provider.value.upper()}"
        logger.error(msg)
        raise RuntimeError(msg)

    if not pulumi_provider.has_secrets(decrypted_secrets):
        msg = f"User: {user_email} ({user_id}) does not have credentials for provider: {blueprint_range.provider.value.upper()}."
        logger.info(msg)
        raise RuntimeError(msg)

    deployment_id = str(uuid.uuid4().hex)[:8]  # or use your own short hash util

    # Apply range using Pulumi context manager
    async with PulumiOperation(
        deployment_id=deployment_id,
        range_obj=blueprint_range,
        region=deploy_request.region,
        secrets=decrypted_secrets,
        name=deploy_request.name,
        provider=blueprint_range.provider,
        description=deploy_request.description or "",
    ) as pulumi:
        try:
            deployed_range = await pulumi.up()

            # Save to database
            async with get_db_session_context() as db:
                deployed_range_header = await create_deployed_range(
                    db, deployed_range, user_id=user.id
                )
        except Exception as original_exc:
            # The main operation failed
            logger.exception(
                "Deployment failed for deployment_id: %s. Cleaning up resources...",
                deployment_id,
            )

            # Wrap cleanup to prevent masking original exception
            try:
                await pulumi.destroy()
            except Exception as cleanup_exc:
                logger.critical(
                    "Automatic deploy resource clean up failed for deployment_id: %s. Exception: %s",
                    deployment_id,
                    cleanup_exc,
                )

            raise original_exc

    logger.info(
        "Successfully created and deployed range: %s (%s) for user: %s (%s).",
        deployed_range_header.name,
        deployed_range_header.id,
        user_email,
        user_id,
    )

    return deployed_range_header.model_dump(mode="json")


@track_job_status
async def destroy_range(
    ctx: dict[str, Any],
    enc_key: str,
    deployed_range_dump: dict[str, Any],
    user_id: int,
) -> dict[str, Any]:
    """Destroy range for a user.

    Args:
    ----
        ctx (JobBaseContextSchema): ARQ worker context. Automatically provided by ARQ.
        enc_key (str): Base64 encoded master key for user.
        deployed_range_dump (dict[str, Any]): DeployedRangeSchema dumped with pydantic's `model_dump(mode='json')`.
        user_id (int): User associated with the destroy request.

    Returns:
    -------
        dict[str, Any]: DeployedRangeHeaderSchema dumped with pydantic's `model_dump(mode='json')`.

    """
    deployed_range = DeployedRangeSchema.model_validate(deployed_range_dump)

    logger.info(
        "Starting destruction of range: %s (%s) on %s...",
        deployed_range.name,
        deployed_range.id,
        deployed_range.provider.value.upper(),
    )

    async with get_db_session_context() as db:
        # Fetch user info
        user = await get_user_by_id(db, UserID(id=user_id))
        if not user:
            msg = f"Unable to destroy range! User: {user_id} not found in database."
            logger.error(msg)
            raise ValueError(msg)

        # Fetch all deploy dependencies
        try:
            master_key = base64.b64decode(enc_key)
        except Exception as e:
            msg = f"Unable to destroy range: {deployed_range.name} ({deployed_range.id})! Failed to decode encryption key for user: {user.email} ({user.id})."
            logger.exception(msg)
            raise RuntimeError(msg) from e

        decrypted_secrets = await get_decrypted_secrets(user, db, master_key)
        if not decrypted_secrets:
            msg = f"Unable to destroy range: {deployed_range.name} ({deployed_range.id})! Failed to decrypt cloud credentials for user: {user.email} ({user.id})"
            logger.warning(msg)
            raise RuntimeError(msg)

        user_id = user.id
        user_is_admin = user.is_admin

    pulumi_provider = PROVIDER_REGISTRY.get(deployed_range.provider)
    if not pulumi_provider:
        msg = (
            f"Pulumi provider not available for {deployed_range.provider.value.upper()}"
        )
        logger.error(msg)
        raise RuntimeError(msg)

    if not pulumi_provider.has_secrets(decrypted_secrets):
        msg = f"User: {user_id} does not have credentials for provider: {deployed_range.provider.value.upper()}."
        logger.info(msg)
        raise RuntimeError(msg)

    async with PulumiOperation(
        deployment_id=deployed_range.deployment_id,
        range_obj=deployed_range,
        region=deployed_range.region,
        secrets=decrypted_secrets,
        name=deployed_range.name,
        provider=deployed_range.provider,
        description=deployed_range.description or "",
    ) as pulumi:
        try:
            await pulumi.destroy()

            async with get_db_session_context() as db:
                deleted_from_db = await delete_deployed_range(
                    db, deployed_range.id, user_id, user_is_admin
                )
                if not deleted_from_db:
                    msg = "Failed to delete destroyed range from DB!"
                    raise RuntimeError(msg)
        except Exception as e:
            logger.exception(
                "Failed to delete range: %s from database on behalf of user: %s! Exception: %s",
                deployed_range.name,
                user_id,
                e,
            )

            # Fail job
            raise e

    logger.info(
        "Successfully destroyed range: %s (%s) for user: %s.",
        deleted_from_db.name,
        deleted_from_db.id,
        user_id,
    )

    # Set range to off since it's destroyed
    deleted_from_db.state = RangeState.OFF

    return deleted_from_db.model_dump(mode="json")
