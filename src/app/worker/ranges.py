import asyncio
import base64
import logging
from typing import Any

import uvloop

from src.app.crud.crud_ranges import create_deployed_range, delete_deployed_range
from src.app.enums.range_states import RangeState
from src.app.schemas.user_schema import UserID

from ..core.cdktf.ranges.range_factory import RangeFactory
from ..core.db.database import get_db_session_context
from ..crud.crud_users import get_decrypted_secrets, get_user_by_id
from ..schemas.range_schemas import (
    BlueprintRangeSchema,
    DeployedRangeSchema,
    DeployRangeSchema,
)
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

    range_to_deploy = RangeFactory.create_range(
        name=deploy_request.name,
        range_obj=blueprint_range,
        region=deploy_request.region,
        description=deploy_request.description,
        secrets=decrypted_secrets,
    )

    # Validate deployment
    if not range_to_deploy.has_secrets():
        msg = f"No credentials found for provider: {blueprint_range.provider.value.upper()} for user: {user_email} ({user_id})"
        logger.info(msg)
        raise RuntimeError(msg)

    # Synthesize range
    successful_synth = await range_to_deploy.synthesize()
    if not successful_synth:
        msg = f"Failed to synthesize range: {range_to_deploy.name} from blueprint: {blueprint_range.name} ({blueprint_range.id}) for user: {user_email} ({user_id})"
        logger.error(msg)
        raise RuntimeError(msg)

    # Deploy range
    created_range = await range_to_deploy.deploy()
    if not created_range:
        msg = f"Failed to deploy range: {range_to_deploy.name} from blueprint: {blueprint_range.name} ({blueprint_range.id}) for user: {user_email} ({user_id})"
        logger.error(msg)
        raise RuntimeError(msg)

    cleanup_required = False

    try:
        async with get_db_session_context() as db:
            try:
                deployed_range_header = await create_deployed_range(
                    db, created_range, user_id=user.id
                )
            except Exception as e:
                cleanup_required = True
                logger.exception(
                    "Failed to save range: %s to database on behalf of user: %s (%s)! Exception: %s",
                    range_to_deploy.name,
                    user_email,
                    user_id,
                    e,
                )

                # Fail job
                raise e
    finally:
        if cleanup_required:
            logger.info(
                "Starting auto clean up of deployed range: %s for user %s (%s)...",
                range_to_deploy.name,
                user_email,
                user_id,
            )

            successful_destroy = await range_to_deploy.destroy()
            if not successful_destroy:
                # Don't raise an exception to prevent masking
                logger.critical(
                    "Auto clean up failed! Failed to destroy range: %s from blueprint: %s (%s) for user: %s (%s)",
                    range_to_deploy.name,
                    blueprint_range.name,
                    blueprint_range.id,
                    user_email,
                    user_id,
                )

            logger.info(
                "Finished auto clean up of deployed range: %s for user %s (%s)!",
                range_to_deploy.name,
                user_email,
                user_id,
            )

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

    # Build range object
    range_to_destroy = RangeFactory.create_range(
        name=deployed_range.name,
        range_obj=deployed_range,
        region=deployed_range.region,
        description=deployed_range.description,
        secrets=decrypted_secrets,
        state_file=deployed_range.state_file,
    )

    # Validate deployment
    if not range_to_destroy.has_secrets():
        # Higher level error as users should
        # have an account in a state where they
        # don't have credentials to destroy their
        # own deployed ranges.
        msg = f"No credentials found for provider: {deployed_range.provider.value.upper()} for user: {user_id}"
        logger.critical(msg)
        raise RuntimeError(msg)

    # Destroy range
    successful_synth = await range_to_destroy.synthesize()
    if not successful_synth:
        msg = f"Failed to synthesize range: {range_to_destroy.name} for user: {user_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    successful_destroy = await range_to_destroy.destroy()
    if not successful_destroy:
        msg = f"Failed to deploy range: {range_to_destroy.name} for user: {user_id}"
        logger.error(msg)
        raise RuntimeError(msg)

    async with get_db_session_context() as db:
        # Delete range from database
        try:
            deleted_from_db = await delete_deployed_range(
                db, deployed_range.id, user_id, user_is_admin
            )
            if not deleted_from_db:
                msg = "Failed to delete destroyed range from DB!"
                raise RuntimeError(msg)
        except Exception as e:
            logger.exception(
                "Failed to delete range: %s from database on behalf of user: %s! Exception: %s",
                range_to_destroy.name,
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
