import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.secret_model import SecretModel

from ..schemas.secret_schema import SecretSchema

logger = logging.getLogger(__name__)


async def get_user_secrets(db: AsyncSession, user_id: int) -> SecretSchema | None:
    """Get user provider secrets.

    Args:
    ----
        db (Session): Database connection.
        user_id (int): ID of the user requesting data.

    Returns:
    -------
        Optional[SecretSchema]: User provider secrets if it exists in the database.

    """
    stmt = select(SecretModel).where(SecretModel.user_id == user_id)
    result = await db.execute(stmt)

    if not result:
        logger.info(
            "Failed to fetch secrets for user: %s. Not found in database!", user_id
        )
        return None

    secrets = result.scalars().first()

    return SecretSchema.model_validate(secrets)


async def upsert_user_secrets(
    db: AsyncSession, secrets: SecretSchema, user_id: int
) -> None:
    """Update user provider secrets.

    Args:
    ----
        db (Session): Database connection.
        user_id (int): ID of the user requesting data.
        secrets (SecretSchema): User secrets record containing new secrets to add to database

    Returns:
    -------
        None

    """
    db_object_to_merge = SecretModel(user_id=user_id, **secrets.model_dump())
    # 2. Merge the instance into the session.
    #    SQLAlchemy checks if a record with this primary key exists.
    #    - If yes, it copies the new data onto the existing record.
    #    - If no, it stages a new record for insertion.
    await db.merge(db_object_to_merge)
    # 3. Commit the transaction to save the changes.
    #    This will execute either an UPDATE or INSERT statement.
    await db.commit()
