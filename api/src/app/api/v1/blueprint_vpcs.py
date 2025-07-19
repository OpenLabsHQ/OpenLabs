import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_vpcs import (
    create_blueprint_vpc,
    delete_blueprint_vpc,
    get_blueprint_vpc,
    get_blueprint_vpc_headers,
)
from ...models.user_model import UserModel
from ...schemas.message_schema import MessageSchema
from ...schemas.vpc_schemas import (
    BlueprintVPCCreateSchema,
    BlueprintVPCHeaderSchema,
    BlueprintVPCSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blueprints", tags=["blueprints"])


@router.get("/vpcs")
async def get_blueprint_vpc_headers_endpoint(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[BlueprintVPCHeaderSchema]:
    """Get a list of blueprint VPC headers.

    Args:
    ----
        standalone_only (bool): Return only standalone VPC blueprints (not part of a range blueprint). Defaults to True.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[BlueprintVPCHeaderSchema]: List of VPC blueprint sheaders owned by the current user.

    """
    vpc_headers = await get_blueprint_vpc_headers(
        db, current_user.id, current_user.is_admin, standalone_only
    )

    if not vpc_headers:
        logger.info(
            "No VPC blueprint headers found for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        standalone_text = " standalone" if standalone_only else ""
        msg = (
            f"No{standalone_text} VPC blueprints found!"
            if current_user.is_admin
            else f"Unable to find any{standalone_text} VPC blueprints that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )

    logger.info(
        "Sucessfully retrieved %s VPC blueprint headers for user: %s (%s).",
        len(vpc_headers),
        current_user.email,
        current_user.id,
    )

    return vpc_headers


@router.get("/vpcs/{blueprint_id}")
async def get_blueprint_vpc_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintVPCSchema:
    """Get a bluerprint VPC.

    Args:
    ----
        blueprint_id (int): ID of the VPC blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintVPCSchema: Blueprint VPC data from database if it belongs to the user.

    """
    blueprint_vpc = await get_blueprint_vpc(
        db, blueprint_id, current_user.id, current_user.is_admin
    )
    if not blueprint_vpc:
        logger.info(
            "Failed to retrieve VPC blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPC blueprint with ID: {blueprint_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully retrieved VPC blueprint: %s for user: %s (%s).",
        blueprint_vpc.id,
        current_user.email,
        current_user.id,
    )

    return blueprint_vpc


@router.post("/vpcs")
async def upload_blueprint_vpc_endpoint(
    blueprint_vpc: BlueprintVPCCreateSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintVPCHeaderSchema:
    """Upload a VPC blueprint.

    Args:
    ----
        blueprint_vpc (BlueprintVPCCreateSchema): OpenLabs compliant blueprint VPC object.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintVPCHeaderSchema: Header info of the new VPC blueprint.

    """
    # Pre-fetch/save data for logging incase of a database error
    current_user_email = current_user.email
    current_user_id = current_user.id

    try:
        # No range ID since this is a standalone blueprint
        created_blueprint = await create_blueprint_vpc(
            db, blueprint_vpc, current_user.id, range_id=None
        )
    except Exception:
        await db.rollback()

        logger.error(
            "Failed to flush VPC blueprint: %s to database on behalf of user: %s (%s)!",
            blueprint_vpc.name,
            current_user_email,
            current_user_id,
        )

        # Notify user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save VPC blueprint: {blueprint_vpc.name} to database!",
        ) from None

    logger.info(
        "Successfully processed VPC blueprint creation request for user: %s (%s). Blueprint ID: %s.",
        current_user.email,
        current_user.id,
        created_blueprint.id,
    )

    return BlueprintVPCHeaderSchema.model_validate(created_blueprint)


@router.delete("/vpcs/{blueprint_id}")
async def delete_blueprint_vpc_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> MessageSchema:
    """Delete a VPC blueprint.

    Args:
    ----
        blueprint_id (int): Id of the VPC blueprint.
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
        deleted_blueprint = await delete_blueprint_vpc(
            db, blueprint_id, current_user.id, current_user.is_admin
        )
    except Exception:
        await db.rollback()

        logger.error(
            "Failed to delete VPC blueprint: %s from database on behalf of user: %s (%s)!",
            blueprint_id,
            current_user_email,
            current_user_id,
        )

        # Notify user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete VPC blueprint: {blueprint_id} from database!",
        ) from None

    if not deleted_blueprint:
        logger.info(
            "Failed to delete VPC blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPC blueprint with id: {blueprint_id} not found or you don't have permission to delete it!",
        )

    logger.info(
        "Successfully deleted VPC blueprint: %s (%s) for user: %s (%s).",
        deleted_blueprint.name,
        deleted_blueprint.id,
        current_user.email,
        current_user.id,
    )

    return MessageSchema(
        message=f"VPC blueprint: {deleted_blueprint.name} ({deleted_blueprint.id}) was successfully deleted!"
    )
