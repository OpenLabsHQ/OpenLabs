import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_hosts import (
    create_blueprint_host,
    delete_blueprint_host,
    get_blueprint_host,
    get_blueprint_host_headers,
)
from ...models.user_model import UserModel
from ...schemas.host_schemas import (
    BlueprintHostCreateSchema,
    BlueprintHostHeaderSchema,
    BlueprintHostSchema,
)
from ...schemas.message_schema import MessageSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blueprints", tags=["blueprints"])


@router.get("/hosts/{blueprint_id}")
async def get_blueprint_host_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintHostSchema:
    """Get a host blueprint.

    Args:
    ----
        blueprint_id (int): Id of the host blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintHostSchema: Host data from database. Admin users can access any blueprint.

    """
    blueprint_host = await get_blueprint_host(
        db, blueprint_id, current_user.id, current_user.is_admin
    )
    if not blueprint_host:
        logger.info(
            "Failed to retrieve host blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host blueprint with ID: {blueprint_id} not found or you don't have access to it!",
        )

    return blueprint_host


@router.post("/hosts")
async def upload_blueprint_host_endpoint(
    blueprint_host: BlueprintHostCreateSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintHostHeaderSchema:
    """Upload a host blueprint.

    Args:
    ----
        blueprint_host (BlueprintHostCreateSchema): OpenLabs compliant host blueprint object.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintHostHeaderSchema: Header info of the new host blueprint.

    """
    # Pre-fetch/save data for logging incase of a database error
    current_user_email = current_user.email
    current_user_id = current_user.id

    try:
        # No subnet ID since this a standalone blueprint
        created_blueprint = await create_blueprint_host(
            db, blueprint_host, current_user.id, subnet_id=None
        )
    except Exception:
        await db.rollback()

        logger.error(
            "Failed to flush host blueprint: %s to database on behalf of user: %s (%s)!",
            blueprint_host.hostname,
            current_user_email,
            current_user_id,
        )

        # Notify user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save host blueprint: {blueprint_host.hostname} to database!",
        ) from None

    logger.info(
        "Successfully processed host blueprint creation request for user: %s (%s). Blueprint ID: %s",
        current_user.email,
        current_user.id,
        created_blueprint.id,
    )

    return BlueprintHostHeaderSchema.model_validate(created_blueprint)


@router.delete("/hosts/{blueprint_id}")
async def delete_blueprint_host_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> MessageSchema:
    """Delete a host blueprint.

    Args:
    ----
        blueprint_id (int): Id of the host blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        MessageSchema: Message regarding status of deletion.

    """
    # Pre-fetch/save data for logging incase of a database error
    current_user_email = current_user.email
    current_user_id = current_user.id

    try:
        deleted_blueprint = await delete_blueprint_host(
            db, blueprint_id, current_user.id, current_user.is_admin
        )
    except Exception:
        await db.rollback()

        logger.error(
            "Failed to delete host blueprint: %s from database on behalf of user: %s (%s)!",
            blueprint_id,
            current_user_email,
            current_user_id,
        )

        # Notify user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete host blueprint: {blueprint_id} from database!",
        ) from None

    if not deleted_blueprint:
        logger.info(
            "Failed to delete host blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host blueprint with id: {blueprint_id} not found or you don't have permission to delete it!",
        )

    logger.info(
        "Successfully deleted host blueprint: %s (%s) for user: %s (%s).",
        deleted_blueprint.hostname,
        deleted_blueprint.id,
        current_user.email,
        current_user.id,
    )

    return MessageSchema(
        message=f"Host blueprint: {deleted_blueprint.hostname} ({deleted_blueprint.id}) was successfully deleted!"
    )


@router.get("/hosts")
async def get_blueprint_host_headers_endpoint(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[BlueprintHostHeaderSchema]:
    """Get a list of host blueprint headers.

    Args:
    ----
        standalone_only (bool): Return only standalone host blueprint (not part of a range/vpc/subnet blueprint). Defaults to True.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[BlueprintHostHeaderSchema]: List of host blueprint headers owned by the current user.

    """
    host_headers = await get_blueprint_host_headers(
        db, current_user.id, current_user.is_admin, standalone_only
    )
    if not host_headers:
        logger.info(
            "No host blueprint headers found for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        standalone_text = " standalone" if standalone_only else ""
        msg = (
            f"No{standalone_text} host blueprints found!"
            if current_user.is_admin
            else f"Unable to find any{standalone_text} host blueprints that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )

    return host_headers
