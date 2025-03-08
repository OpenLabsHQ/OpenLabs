import base64
import uuid
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.config import settings
from ...core.db.database import async_get_db
from ...crud.crud_range_templates import get_range_template, is_range_template_owner
from ...crud.crud_users import get_decrypted_secrets
from ...models.user_model import UserModel
from ...schemas.template_range_schema import TemplateRangeID, TemplateRangeSchema

router = APIRouter(prefix="/ranges", tags=["ranges"])


@router.post("/deploy")
async def deploy_range_from_template(
    range_ids: list[TemplateRangeID],
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    enc_key: str | None = Cookie(None, alias="enc_key"),
) -> dict[str, Any]:
    """Deploy range templates.

    Args:
    ----
        range_ids (list[TemplateRangeID]): List of range template IDs to deploy.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.
        enc_key (str): Encryption key from cookie for decrypting secrets.

    Returns:
    -------
        dict[str, Any]: Deployment status.

    """
    # Import CDKTF dependencies to avoid long import times
    from ...core.cdktf.aws.aws import create_aws_stack, deploy_infrastructure

    # Check if we have the encryption key needed to decrypt secrets
    if not enc_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Encryption key not found. Please try logging in again.",
        )

    # Decode the encryption key
    try:
        master_key = base64.b64decode(enc_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid encryption key. Please try logging in again.",
        ) from e

    ranges: list[TemplateRangeSchema] = []
    for range_id in range_ids:
        # For admin users, skip ownership check to allow deploying any range
        if not current_user.is_admin:
            # Check if the user owns this template
            is_owner = await is_range_template_owner(db, range_id, current_user.id)
            if not is_owner:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You don't have permission to deploy range with ID: {range_id.id}",
                )

        # Set user_id to None for admin to allow accessing any template
        user_id = None if current_user.is_admin else current_user.id

        # Get the template
        range_model = await get_range_template(db, range_id, user_id=user_id)
        if not range_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Range template with ID: {range_id.id} not found!",
            )

        ranges.append(
            TemplateRangeSchema.model_validate(range_model, from_attributes=True)
        )

    # Get the decrypted credentials
    decrypted_secrets = await get_decrypted_secrets(current_user, db, master_key)
    if not decrypted_secrets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt cloud credentials. Please try logging in again.",
        )

    # Check if we have the appropriate credentials based on the provider
    # For now we'll check AWS only since that's what's implemented
    if (
        not decrypted_secrets.aws_access_key
        or not decrypted_secrets.aws_secret_key
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AWS credentials not found or incomplete. Please add your AWS credentials.",
        )

    # Set environment variables for AWS provider
    import os

    os.environ["AWS_ACCESS_KEY_ID"] = decrypted_secrets.aws_access_key
    os.environ["AWS_SECRET_ACCESS_KEY"] = decrypted_secrets.aws_secret_key

    for deploy_range in ranges:
        deployed_range_id = uuid.uuid4()
        stack_name = create_aws_stack(
            deploy_range, settings.CDKTF_DIR, deployed_range_id
        )
        state_file = deploy_infrastructure(settings.CDKTF_DIR, stack_name)

        if not state_file:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to read terraform state file.",
            )
        # deployed_range_obj = DeployedRange(deployed_range_id, range_template, state_file, range_template.provider, account: OpenLabsAccount, cloud_account_id: uuid/int) OpenLabsAccount --> Provider --> Cloud Account ID --> AWS Creds
        # save(db, deployed_range_obj)

    return {"deployed": True}
