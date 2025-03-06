import base64
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.config import settings
from ...core.db.database import async_get_db
from ...crud.crud_users import get_user_by_id, update_user_password
from ...models.secret_model import SecretModel
from ...models.user_model import UserModel
from ...schemas.secret_schema import AWSSecrets, AzureSecrets
from ...schemas.user_schema import PasswordUpdateSchema, UserID, UserInfoResponseSchema
from ...utils.crypto import (
    decrypt_private_key,
    decrypt_with_private_key,
    encrypt_with_public_key,
    generate_master_key,
)

router = APIRouter(prefix="/users", tags=["users"])


async def get_decrypted_secrets(
    user: UserModel,
    db: AsyncSession,
    enc_key: str | None
) -> dict[str, Any]:
    """Get decrypted secrets for the user.
    
    Args:
    ----
        user (UserModel): The user whose secrets to decrypt
        db (AsyncSession): Database connection
        enc_key (str | None): Base64-encoded encryption key from cookie
        
    Returns:
    -------
        dict: Decrypted secrets or None if decryption fails

    """
    if not enc_key or not user.encrypted_private_key:
        return None

    # Fetch the user's secrets from the database
    stmt = select(SecretModel).where(SecretModel.user_id == user.id)
    result = await db.execute(stmt)
    secrets = result.scalars().first()

    if not secrets:
        return None

    try:
        # Decode the encryption key
        master_key = base64.b64decode(enc_key)

        # Decrypt the private key
        private_key_b64 = decrypt_private_key(user.encrypted_private_key, master_key)

        # Prepare containers for decrypted secrets
        aws_secrets = None
        azure_secrets = None

        # Decrypt AWS secrets if they exist
        if secrets.aws_access_key and secrets.aws_secret_key:
            encrypted_aws = {
                "aws_access_key": secrets.aws_access_key,
                "aws_secret_key": secrets.aws_secret_key,
            }
            aws_secrets = decrypt_with_private_key(encrypted_aws, private_key_b64)

        # Decrypt Azure secrets if they exist
        if (secrets.azure_client_id and secrets.azure_client_secret and
            secrets.azure_tenant_id and secrets.azure_subscription_id):
            encrypted_azure = {
                "azure_client_id": secrets.azure_client_id,
                "azure_client_secret": secrets.azure_client_secret,
                "azure_tenant_id": secrets.azure_tenant_id,
                "azure_subscription_id": secrets.azure_subscription_id,
            }
            azure_secrets = decrypt_with_private_key(encrypted_azure, private_key_b64)

        return {
            "aws": aws_secrets,
            "azure": azure_secrets
        }
    except Exception:
        # If decryption fails, return None
        return None


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
    return UserInfoResponseSchema(
        name=current_user.name, email=current_user.email, admin=current_user.is_admin
    )


@router.post("/me/password")
async def update_password(
    password_update: PasswordUpdateSchema,
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> JSONResponse:
    """Update the current user's password.

    Args:
    ----
        password_update (PasswordUpdate): The current and new passwords.
        current_user (UserModel): The authenticated user.
        db (Session): Database connection.

    Returns:
    -------
        JSONResponse: Success message with updated cookie.

    """
    success = await update_user_password(
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

    # Get the updated user to access the new salt
    updated_user = await get_user_by_id(db, UserID(id=current_user.id))
    if not updated_user or not updated_user.key_salt:
        # This should not happen, but handle the case anyway
        return JSONResponse(content={"message": "Password updated successfully"})

    # Generate a new master key with the new password and updated salt
    master_key, _ = generate_master_key(password_update.new_password, updated_user.key_salt)
    master_key_b64 = base64.b64encode(master_key).decode("utf-8")

    # Set expiry time to match the authentication token
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # Create the response with updated cookie
    response = JSONResponse(content={"message": "Password updated successfully"})

    # Set the new encryption key cookie
    response.set_cookie(
        key="enc_key",
        value=master_key_b64,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=expire_seconds,
        path="/",
    )

    return response


@router.get("/me/secrets")
async def get_user_secrets(
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> dict[str, Any]:
    """Get the current user's cloud provider secrets status.

    Args:
    ----
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        dict: Status of user's cloud provider credentials.

    """
    stmt = select(SecretModel).where(SecretModel.user_id == current_user.id)
    result = await db.execute(stmt)
    secrets = result.scalars().first()
    # Check if the user has secrets
    if not secrets:
        return {
            "aws": {"has_credentials": False},
            "azure": {"has_credentials": False},
        }

    aws_created_at = None
    if secrets.aws_created_at:
        aws_created_at = secrets.aws_created_at.isoformat()

    azure_created_at = None
    if secrets.azure_created_at:
        azure_created_at = secrets.azure_created_at.isoformat()

    return {
        "aws": {
            "has_credentials": secrets.aws_access_key is not None,
            "created_at": aws_created_at,
        },
        "azure": {
            "has_credentials": (
                secrets.azure_client_id is not None
                and secrets.azure_client_secret is not None
                and secrets.azure_tenant_id is not None
                and secrets.azure_subscription_id is not None
            ),
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
    # Fetch secrets explicitly from the database
    stmt = select(SecretModel).where(SecretModel.user_id == current_user.id)
    result = await db.execute(stmt)
    secrets = result.scalars().first()
    if not secrets:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User secrets record not found",
        )

    # Encrypt the AWS credentials using the user's public key
    if not current_user.public_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User encryption keys not set up. Please register a new account.",
        )

    # Convert to dictionary for encryption
    aws_data = {
        "aws_access_key": aws_secrets.aws_access_key,
        "aws_secret_key": aws_secrets.aws_secret_key,
    }

    # Encrypt with the user's public key
    encrypted_data = encrypt_with_public_key(aws_data, current_user.public_key)

    # Update the secrets with encrypted values
    secrets.aws_access_key = encrypted_data["aws_access_key"]
    secrets.aws_secret_key = encrypted_data["aws_secret_key"]
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
    # Fetch secrets explicitly from the database
    stmt = select(SecretModel).where(SecretModel.user_id == current_user.id)
    result = await db.execute(stmt)
    secrets = result.scalars().first()
    if not secrets:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User secrets record not found",
        )

    # Encrypt the Azure credentials using the user's public key
    if not current_user.public_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User encryption keys not set up. Please register a new account.",
        )

    # Convert to dictionary for encryption
    azure_data = {
        "azure_client_id": azure_secrets.azure_client_id,
        "azure_client_secret": azure_secrets.azure_client_secret,
        "azure_tenant_id": azure_secrets.azure_tenant_id,
        "azure_subscription_id": azure_secrets.azure_subscription_id,
    }

    # Encrypt with the user's public key
    encrypted_data = encrypt_with_public_key(azure_data, current_user.public_key)

    # Update the secrets with encrypted values
    secrets.azure_client_id = encrypted_data["azure_client_id"]
    secrets.azure_client_secret = encrypted_data["azure_client_secret"]
    secrets.azure_tenant_id = encrypted_data["azure_tenant_id"]
    secrets.azure_subscription_id = encrypted_data["azure_subscription_id"]
    secrets.azure_created_at = datetime.now(UTC)
    await db.commit()

    return {"message": "Azure credentials updated successfully"}
