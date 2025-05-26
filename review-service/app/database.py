from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
DB_NAME = os.getenv("MONGO_DB", "shop")

client: AsyncIOMotorClient | None = None

def get_db():
    global client
    if client is None:
        client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


async def init_indexes():
    db = get_db()
    await db.reviews.create_index("product_id")
    await db.reviews.create_index("created_at")