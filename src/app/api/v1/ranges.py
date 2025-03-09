import base64
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.cdktf.ranges.range_factory import RangeFactory
from ...core.db.database import async_get_db
from ...crud.crud_range_templates import get_range_template, is_range_template_owner
from ...crud.crud_ranges import create_range, delete_range, get_range, is_range_owner
from ...crud.crud_users import get_secrets
from ...enums.range_states import RangeState
from ...crud.crud_users import get_decrypted_secrets
from ...models.user_model import UserModel
from ...schemas.range_schema import DeployRangeBaseSchema, RangeID, RangeSchema
from ...schemas.secret_schema import SecretSchema
from ...schemas.template_range_schema import TemplateRangeID, TemplateRangeSchema
from ...schemas.user_schema import UserID
from ...validators.id import is_valid_uuid4

router = APIRouter(prefix="/ranges", tags=["ranges"])


@router.post("/deploy")
async def deploy_range_from_template_endpoint(
    deploy_range: DeployRangeBaseSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> RangeID:
    """Deploy range templates.

    Args:
    ----
        deploy_range (DeployRangeBaseSchema): Range template to deploy.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.
        enc_key (str): Encryption key from cookie for decrypting secrets.

    Returns:
    -------
        RangeID: ID of deployed range.

    """
    # Check if the user is the template owner
    is_owner = await is_range_template_owner(
        db, TemplateRangeID(id=deploy_range.template_id), user_id=current_user.id
    )
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to deploy range with using template: {deploy_range.template_id}",
        )

    template_range_model = await get_range_template(
        db, TemplateRangeID(id=deploy_range.template_id), user_id=current_user.id
    )
    if not template_range_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range template with ID: {deploy_range.template_id} not found or you don't have access to it!",
        )

    # Create deployed range schema
    template = TemplateRangeSchema.model_validate(
        template_range_model, from_attributes=True
    )

    # Create User ID
    user_id = UserID.model_validate(current_user, from_attributes=True)

    # Get Secrets
    secrets_model = await get_secrets(db, user_id)

    if secrets_model is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No configured credentials found.",
        )

    secrets = SecretSchema.model_validate(secrets_model, from_attributes=True)

    # Create deployable range object
    range_to_deploy = RangeFactory.create_range(
        id=uuid.uuid4(),
        template=template,
        region=deploy_range.region,
        owner_id=user_id,
        secrets=secrets,
    )

    if not range_to_deploy.has_secrets():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No credentials found for provider: {template.provider}",
        )

    # Deploy range
    range_to_deploy.synthesize()
    successful_deploy = range_to_deploy.deploy()
    if not successful_deploy:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy range: {template.name} ({range_to_deploy.id})!",
        )

    # Build range schema
    range_schema = RangeSchema(
        **deploy_range.model_dump(),
        id=range_to_deploy.id,
        date=datetime.now(tz=timezone.utc),
        template=template.model_dump(mode="json"),
        state_file=range_to_deploy.get_state_file(),
        state=RangeState.ON,  # User manually starts after deployment
    )

    # Save deployed range info to database
    created_range_model = await create_range(db, range_schema, owner_id=user_id.id)
    if not created_range_model:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save deployed range to database. Range: {range_to_deploy.template.name} ({range_to_deploy.id})",
        )

    return RangeID(id=range_schema.id)


@router.delete("/{range_id}")
async def delete_range_endpoint(
    range_id: str,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> bool:
    """Destroy a deployed range.

    Args:
    ----
        range_id (str): ID of deployed range.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        bool: True if successfully deployed. False otherwise.

    """
    if not is_valid_uuid4(range_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    is_owner = await is_range_owner(db, RangeID(id=range_id), user_id=current_user.id)
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to destroy range with ID: {range_id}",
        )

    # Create User ID
    user_id = UserID.model_validate(current_user, from_attributes=True)

    # Get range from database
    range_model = await get_range(
        db, RangeID(id=uuid.UUID(range_id)), user_id=current_user.id
    )

    if not range_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range with ID: {range_id} not found or you don't have access to it!",
        )

    # Get Secrets
    secrets_model = await get_secrets(db, user_id)

    if secrets_model is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No configured credentials found.",
        )

    secrets = SecretSchema.model_validate(secrets_model, from_attributes=True)

    # Build range object
    range_schema = RangeSchema.model_validate(range_model)
    range_template = TemplateRangeSchema.model_validate(range_schema.template)
    range_obj = RangeFactory.create_range(
        id=range_schema.id,
        template=range_template,
        region=range_schema.region,
        owner_id=user_id,
        secrets=secrets,
        statefile=range_schema.state_file,
        is_deployed=True
    )

    # Destroy range
    range_obj.synthesize()
    successful_destroy = range_obj.destroy()
    if not successful_destroy:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to destroy range: {range_template.name} ({range_obj.id})!",
        )

    # Delete range from database
    deleted_from_db = await delete_range(db, range_model)
    if not deleted_from_db:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete deployed range entry in database. Range: {range_obj.template.name} ({range_obj.id})",
        )

    return True
