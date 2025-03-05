import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.cdktf.ranges.range_factory import RangeFactory
from ...core.db.database import async_get_db
from ...crud.crud_range_templates import get_range_template, is_range_template_owner
from ...crud.crud_users import get_secrets
from ...models.user_model import UserModel
from ...schemas.range_schema import DeployRangeBaseSchema, RangeID
from ...schemas.secret_schema import SecretSchema
from ...schemas.template_range_schema import TemplateRangeID, TemplateRangeSchema
from ...schemas.user_schema import UserID

router = APIRouter(prefix="/ranges", tags=["ranges"])


@router.post("/deploy")
async def deploy_range_from_template(
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

    Returns:
    -------
        dict[str, Any]: Deployment status.

    """
    # Check if the user is the template owner
    is_owner = await is_range_template_owner(
        db, TemplateRangeID(id=deploy_range.template_id), user_id=current_user.id
    )
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to deploy range with ID: {deploy_range.template_id}",
        )

    template_range_model = await get_range_template(
        db, TemplateRangeID(id=deploy_range.template_id), user_id=current_user.id
    )
    if not template_range_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range template with ID: {deploy_range.template_id} not found or you don't have access to it!",
        )

    # Create deployed range
    template_range = TemplateRangeSchema.model_validate(
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

    deployed_range_id = uuid.uuid4()
    range_to_deploy = RangeFactory.create_range(
        deployed_range_id=deployed_range_id,
        template_range=template_range,
        region=deploy_range.region,
        owner_id=user_id,
        secrets=secrets,
    )

    if not range_to_deploy.has_secrets():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No credentials found for provider: {template_range.provider}",
        )

    # Deploy range
    range_to_deploy.synthesize()
    range_to_deploy.deploy()

    return RangeID(id=deployed_range_id)
