import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_ranges import (
    create_blueprint_range,
    delete_blueprint_range,
    get_blueprint_range,
    get_blueprint_range_headers,
)
from ...models.user_model import UserModel
from ...schemas.message_schema import MessageSchema
from ...schemas.range_schemas import (
    BlueprintRangeCreateSchema,
    BlueprintRangeHeaderSchema,
    BlueprintRangeSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blueprints", tags=["blueprints"])


@router.get("/ranges")
async def get_blueprint_range_headers_endpoint(
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[BlueprintRangeHeaderSchema]:
    """Get a list of blueprint range headers.

    Args:
    ----
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[BlueprintRangeHeaderSchema]: List of blueprint range headers. For admin users, shows all blueprints.
                               For regular users, shows only blueprints they own.

    """
    range_headers = await get_blueprint_range_headers(
        db, current_user.id, current_user.is_admin
    )

    if not range_headers:
        logger.info(
            "No range blueprint headers found for user: %s (%s)",
            current_user.email,
            current_user.id,
        )
        msg = (
            "No range blueprints found!"
            if current_user.is_admin
            else "Unable to find any range blueprints that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )

    logger.info(
        "Successfully retrieved %s range blueprint headers for user: %s (%s).",
        len(range_headers),
        current_user.email,
        current_user.id,
    )

    return range_headers


@router.get("/ranges/{blueprint_id}")
async def get_blueprint_range_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintRangeSchema:
    """Get a range blueprint.

    Args:
    ----
        blueprint_id (int): ID of the range blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintRangeSchema: Range blueprint data from database. Admin users can access any blueprint.

    """
    blueprint_range = await get_blueprint_range(
        db, blueprint_id, current_user.id, current_user.is_admin
    )

    if not blueprint_range:
        logger.info(
            "Failed to retrieve range blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range blueprint with ID: {blueprint_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully retrieved range blueprint: %s for user: %s (%s).",
        blueprint_range.id,
        current_user.email,
        current_user.id,
    )

    return blueprint_range


@router.post("/ranges")
async def upload_blueprint_range_endpoint(
    blueprint_range: BlueprintRangeCreateSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintRangeHeaderSchema:
    """Upload a range blueprint.

    Args:
    ----
        blueprint_range (BlueprintRangeHeaderSchema): OpenLabs compliant blueprint range object.
        db (AsynSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintRangeHeaderSchema: Header info of the new range blueprint.

    """
    # Pre-fetch/save data for logging incase of a database error
    current_user_email = current_user.email
    current_user_id = current_user.id

    try:
        created_blueprint = await create_blueprint_range(
            db, blueprint_range, current_user.id
        )
    except Exception:
        await db.rollback()

        logger.error(
            "Failed to flush range blueprint: %s to database on behalf of user: %s (%s)!",
            blueprint_range.name,
            current_user_email,
            current_user_id,
        )

        # Notify user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save range blueprint: {blueprint_range.name} to database!",
        ) from None

    logger.info(
        "Successfully processed range blueprint creation request for user: %s (%s). Blueprint ID: %s",
        current_user.email,
        current_user.id,
        created_blueprint.id,
    )

    return BlueprintRangeHeaderSchema.model_validate(created_blueprint)


@router.delete("/ranges/{blueprint_id}")
async def delete_blueprint_range_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> MessageSchema:
    """Delete a blueprint range.

    Args:
    ----
        blueprint_id (str): Id of the blueprint range.
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
        deleted_blueprint = await delete_blueprint_range(
            db, blueprint_id, current_user.id, current_user.is_admin
        )
    except Exception:
        await db.rollback()

        logger.error(
            "Failed to delete range blueprint: %s from database on behalf of user: %s (%s)!",
            blueprint_id,
            current_user_email,
            current_user_id,
        )

        # Notify user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete range blueprint: {blueprint_id} from database!",
        ) from None

    if not deleted_blueprint:
        logger.info(
            "Failed to delete range blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range blueprint with id: {blueprint_id} not found or you don't have permission to delete it!",
        )

    logger.info(
        "Successfully deleted range blueprint: %s (%s) for user: %s (%s).",
        deleted_blueprint.name,
        deleted_blueprint.id,
        current_user.email,
        current_user.id,
    )

    return MessageSchema(
        message=f"Range blueprint: {deleted_blueprint.name} ({deleted_blueprint.id}) was successfully deleted!"
    )
