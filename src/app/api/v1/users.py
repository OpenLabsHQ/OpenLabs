from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_users import update_user_password
from ...models.user_model import UserModel
from ...schemas.secret_schema import AWSSecrets, AzureSecrets
from ...schemas.user_schema import PasswordUpdateSchema, UserInfoResponseSchema

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserInfoResponseSchema)
async def get_user_info(
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> UserInfoResponseSchema:
    """Get the current user's information.

    Args:
    ----
        current_user (UserModel): The authenticated user.

    Returns:
    -------
        UserInfoResponse: User's profile information.

    """
    return UserInfoResponseSchema(name=current_user.name, email=current_user.email)


@router.post("/me/password")
async def update_password(
    password_update: PasswordUpdateSchema,
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> dict[str, str]:
    """Update the current user's password.

    Args:
    ----
        password_update (PasswordUpdate): The current and new passwords.
        current_user (UserModel): The authenticated user.
        db (Session): Database connection.

    Returns:
    -------
        dict[str, str]: Success message.

    """
    success = update_user_password(
        db,
        current_user.id,
        password_update.current_password,
        password_update.new_password,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    return {"message": "Password updated successfully"}


@router.get("/me/secrets")
async def get_user_secrets(
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    """Get the current user's cloud provider secrets status.

    Args:
    ----
        current_user (UserModel): The authenticated user.

    Returns:
    -------
        dict: Status of user's cloud provider credentials.

    """
    # Check if the user has secrets
    if not current_user.secrets:
        return {
            "aws": {"has_credentials": False},
            "azure": {"has_credentials": False},
        }

    aws_created_at = None
    if current_user.secrets.aws_created_at:
        aws_created_at = current_user.secrets.aws_created_at.isoformat()

    azure_created_at = None
    if current_user.secrets.azure_created_at:
        azure_created_at = current_user.secrets.azure_created_at.isoformat()

    return {
        "aws": {
            "has_credentials": current_user.secrets.aws_access_key is not None,
            "created_at": aws_created_at,
        },
        "azure": {
            "has_credentials": current_user.secrets.azure_client_id is not None,
            "created_at": azure_created_at,
        },
    }


@router.post("/me/secrets/aws")
async def update_aws_secrets(
    aws_secrets: AWSSecrets,
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> dict[str, str]:
    """Update the current user's AWS secrets.

    Args:
    ----
        aws_secrets (AWSSecrets): The AWS credentials to store.
        current_user (UserModel): The authenticated user.
        db (Session): Database connection.

    Returns:
    -------
        dict[str, str]: Success message.

    """
    secrets = current_user.secrets
    if not secrets:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User secrets record not found",
        )

    # Update the secrets
    secrets.aws_access_key = aws_secrets.aws_access_key
    secrets.aws_secret_key = aws_secrets.aws_secret_key
    secrets.aws_created_at = datetime.now(UTC)
    await db.commit()

    return {"message": "AWS credentials updated successfully"}


@router.post("/me/secrets/azure")
async def update_azure_secrets(
    azure_secrets: AzureSecrets,
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> dict[str, str]:
    """Update the current user's Azure secrets.

    Args:
    ----
        azure_secrets (AzureSecrets): The Azure credentials to store.
        current_user (UserModel): The authenticated user.
        db (Session): Database connection.

    Returns:
    -------
        dict[str, str]: Success message.

    """
    secrets = current_user.secrets
    if not secrets:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User secrets record not found",
        )

    # Update the secrets
    secrets.azure_client_id = azure_secrets.azure_client_id
    secrets.azure_client_secret = azure_secrets.azure_client_secret
    secrets.azure_created_at = datetime.now(UTC)
    await db.commit()

    return {"message": "Azure credentials updated successfully"}
