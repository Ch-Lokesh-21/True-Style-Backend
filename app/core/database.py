from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

# close the MongoDB connection on application shutdown
async def close_mongo_connection():
    client.close()

engine = create_async_engine(settings.POSTGRESQL_URI, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async def close_engine():
    await engine.dispose()
