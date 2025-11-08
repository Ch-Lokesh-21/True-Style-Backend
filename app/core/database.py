from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

# close the MongoDB connection on application shutdown
async def close_mongo_connection():
    client.close()
