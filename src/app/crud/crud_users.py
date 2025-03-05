from datetime import UTC, datetime

from bcrypt import gensalt, hashpw
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import load_only

from ..models.secret_model import SecretModel
from ..models.user_model import UserModel
from ..schemas.secret_schema import SecretSchema
from ..schemas.user_schema import (
    UserCreateBaseSchema,
    UserCreateSchema,
    UserID,
)


async def create_secret(
    db: AsyncSession, secret: SecretSchema, user_id: UserID
) -> SecretModel:
    """Create a new secret.

    Args:
    ----
        db (AsyncSession): Database connection.
        secret (SecretSchema): Secret data.
        user_id (UserID): ID of the user who owns this secret.

    Returns:
    -------
        SecretModel: The created secret.

    """
    secret_dict = secret.model_dump()
    secret_dict["user_id"] = user_id.id

    secret_obj = SecretModel(**secret_dict)
    db.add(secret_obj)

    return secret_obj


async def get_secrets(db: AsyncSession, user_id: UserID) -> SecretModel | None:
    """Get a user's cloud secrets.

    Args:
    ----
        db (AsyncSession): Database connection.
        user_id (UserID): User who owns secrets.

    Returns:
    -------
        SecretModel: The user's secret.

    """
    mapped_secret_model = inspect(SecretModel)
    main_columns = [
        getattr(SecretModel, attr.key) for attr in mapped_secret_model.column_attrs
    ]

    stmt = (
        select(SecretModel)
        .where(SecretModel.user_id == user_id.id)
        .options(load_only(*main_columns))
    )

    result = await db.execute(stmt)

    return result.scalars().first()


async def get_user(db: AsyncSession, email: str) -> UserModel | None:
    """Get a user by email.

    Args:
    ----
        db (Session): Database connection.
        email (str): User email.

    Returns:
    -------
        User: The user.

    """
    mapped_user_model = inspect(UserModel)
    main_columns = [
        getattr(UserModel, attr.key) for attr in mapped_user_model.column_attrs
    ]

    stmt = (
        select(UserModel)
        .where(UserModel.email == email)
        .options(load_only(*main_columns))
    )

    result = await db.execute(stmt)

    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: UserID) -> UserModel | None:
    """Get a user by ID.

    Args:
    ----
        db (Session): Database connection.
        user_id (UserID): User ID.

    Returns:
    -------
        User: The user.

    """
    mapped_user_model = inspect(UserModel)
    main_columns = [
        getattr(UserModel, attr.key) for attr in mapped_user_model.column_attrs
    ]

    stmt = (
        select(UserModel)
        .where(UserModel.id == user_id.id)
        .options(load_only(*main_columns))
    )

    result = await db.execute(stmt)

    return result.scalars().first()


async def create_user(
    db: AsyncSession, openlabs_user: UserCreateBaseSchema
) -> UserModel:
    """Create and add a new OpenLabsUser to the database.

    Args:
    ----
        db (Session): Database connection.
        openlabs_user (UserBaseSchema): Dictionary containing User data.

    Returns:
    -------
        User: The newly created user.

    """
    openlabs_user = UserCreateSchema(**openlabs_user.model_dump())
    user_dict = openlabs_user.model_dump(exclude={"secrets"})

    # Here, we populate fields to match the database model
    del user_dict["password"]

    hash_salt = gensalt()
    hashed_password = hashpw(openlabs_user.password.encode(), hash_salt)

    user_dict["hashed_password"] = hashed_password.decode()

    user_dict["created_at"] = datetime.now(UTC)
    user_dict["last_active"] = datetime.now(UTC)

    user_dict["is_admin"] = False

    user_obj = UserModel(**user_dict)
    db.add(user_obj)

    user_id = UserID(id=user_obj.id)

    empty_secret = SecretSchema()

    secrets_object = await create_secret(db, empty_secret, user_id)

    db.add(secrets_object)

    await db.commit()

    return user_obj
