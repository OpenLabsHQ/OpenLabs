import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_subnets import (
    create_blueprint_subnet,
    delete_blueprint_subnet,
    get_blueprint_subnet,
    get_blueprint_subnet_headers,
)
from ...models.user_model import UserModel
from ...schemas.message_schema import MessageSchema
from ...schemas.subnet_schemas import (
    BlueprintSubnetCreateSchema,
    BlueprintSubnetHeaderSchema,
    BlueprintSubnetSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blueprints", tags=["blueprints"])


@router.get("/subnets")
async def get_blueprint_subnet_headers_endpoint(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[BlueprintSubnetHeaderSchema]:
    """Get a list of blueprint subnet headers.

    Args:
    ----
        standalone_only (bool): Return only standalone subnet blueprints (not part of a range/vpc blueprint). Defaults to True.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[BlueprintSubnetHeaderSchema]: List of subnet blueprint headers owned by the current user.

    """
    subnet_headers = await get_blueprint_subnet_headers(
        db, current_user.id, current_user.is_admin, standalone_only
    )

    if not subnet_headers:
        logger.info(
            "No subnet blueprint headers found for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        standalone_text = " standalone" if standalone_only else ""
        detail = (
            f"No{standalone_text} subnet blueprints found!"
            if current_user.is_admin
            else f"Unable to find any{standalone_text} subnet blueprints that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return subnet_headers


@router.get("/subnets/{blueprint_id}")
async def get_blueprint_subnet_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintSubnetSchema:
    """Get a subnet blueprint.

    Args:
    ----
        blueprint_id (int): ID of the subnet blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintSubnetSchema: Subnet data from database. Admin users can access any blueprint.

    """
    blueprint_subnet = await get_blueprint_subnet(
        db, blueprint_id, current_user.id, current_user.is_admin
    )
    if not blueprint_subnet:
        logger.info(
            "Failed to retrieve subnet blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subnet blueprint with ID: {blueprint_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully retrieved subnet blueprint: %s for user: %s (%s).",
        blueprint_subnet.id,
        current_user.email,
        current_user.id,
    )

    return blueprint_subnet


@router.post("/subnets")
async def upload_blueprint_subnet_endpoint(
    blueprint_subnet: BlueprintSubnetCreateSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintSubnetHeaderSchema:
    """Upload a subnet blueprint.

    Args:
    ----
        blueprint_subnet (BlueprintSubnetCreateSchema): OpenLabs compliant subnet blueprint object.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintSubnetHeaderSchema: Header info of the new subnet blueprint.

    """
    # Pre-fetch/save data for logging incase of a database error
    current_user_email = current_user.email
    current_user_id = current_user.id

    try:
        # No VPC ID since this a standalone blueprint
        created_blueprint = await create_blueprint_subnet(
            db, blueprint_subnet, current_user.id, vpc_id=None
        )
    except Exception:
        await db.rollback()

        logger.error(
            "Failed to flush subnet blueprint: %s to database on behalf of user: %s (%s)!",
            blueprint_subnet.name,
            current_user_email,
            current_user_id,
        )

        # Notify user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save subnet blueprint: {blueprint_subnet.name} to database!",
        ) from None

    logger.info(
        "Successfully processed subnet blueprint creation request for user: %s (%s). Blueprint ID: %s",
        current_user.email,
        current_user.id,
        created_blueprint.id,
    )

    return BlueprintSubnetHeaderSchema.model_validate(created_blueprint)


@router.delete("/subnets/{blueprint_id}")
async def delete_blueprint_subnet_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> MessageSchema:
    """Delete a subnet blueprint.

    Args:
    ----
        blueprint_id (int): Id of the subnet blueprint.
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
        deleted_blueprint = await delete_blueprint_subnet(
            db, blueprint_id, current_user.id, current_user.is_admin
        )
    except Exception:
        await db.rollback()

        logger.error(
            "Failed to delete subnet blueprint: %s from database on behalf of user: %s (%s)!",
            blueprint_id,
            current_user_email,
            current_user_id,
        )

        # Notify user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete subnet blueprint: {blueprint_id} from database!",
        ) from None

    if not deleted_blueprint:
        logger.info(
            "Failed to delete subnet blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subnet blueprint with id: {blueprint_id} not found or you don't have permission to delete it!",
        )

    logger.info(
        "Successfully deleted subnet blueprint: %s (%s) for user: %s (%s).",
        deleted_blueprint.name,
        deleted_blueprint.id,
        current_user.email,
        current_user.id,
    )

    return MessageSchema(
        message=f"Subnet blueprint: {deleted_blueprint.name} ({deleted_blueprint.id}) was successfully deleted!"
    )
