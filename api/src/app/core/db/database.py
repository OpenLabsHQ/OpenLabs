import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from ..config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase, MappedAsDataclass):
    """Declarative base class for all ORM models."""

    pass


DATABASE_URI = settings.POSTGRES_URI
DATABASE_PREFIX = settings.POSTGRES_ASYNC_PREFIX
DATABASE_URL = f"{DATABASE_PREFIX}{DATABASE_URI}"

async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)

local_session = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session with proper transaction handling.

    Commits on success, rolls back on any exception.
    """
    async with local_session() as db:
        try:
            yield db
            await db.commit()
            logger.debug("Transaction commited to database.")
        except Exception as e:
            logger.debug(
                "Execution failed during database session. Rolling back transaction. Error: %s",
                e,
            )
            await db.rollback()
            raise e


async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to yield a database session."""
    async with get_db_session_context() as db_session:
        yield db_session
