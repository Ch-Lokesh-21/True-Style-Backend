from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------------------------------------------
# MongoDB setup (Motor)
# ---------------------------------------------------------
client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]


async def close_mongo_connection():
    """
    Gracefully close the MongoDB connection.

    Called during application shutdown to ensure that the
    underlying Motor client releases resources cleanly.
    """
    client.close()


# ---------------------------------------------------------
# PostgreSQL setup (SQLAlchemy async engine)
# ---------------------------------------------------------
engine = create_async_engine(
    settings.POSTGRESQL_URI,
    echo=False,
    future=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency: Provides an async SQLAlchemy session for PostgreSQL.

    Usage:
        session: AsyncSession = Depends(get_session)

    Yields:
        AsyncSession - pooled ORM session to be used inside request scope.

    Ensures proper cleanup after the request finishes.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def close_engine():
    """
    Gracefully dispose the SQLAlchemy async engine.

    Called during application shutdown so all pooled
    connections are cleaned up safely.
    """
    await engine.dispose()