from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from opensearchpy import OpenSearch
from app.config import Settings
from motor.motor_asyncio import AsyncIOMotorClient
import os

DATABASE_URL = Settings.POSTGRES_URL

engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20, future=True)

client: AsyncIOMotorClient | None = None

# фабрика сессий
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Базовый класс моделей"""
    pass


async def init_db():
    """Создание схемы при первом старте"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)




def get_db():
    global client
    if client is None:
        client = AsyncIOMotorClient(Settings.MONGO_URL)
    return client[Settings.MONGO_DB]


async def init_indexes():
    db = get_db()
    await db.reviews.create_index("product_id")
    await db.reviews.create_index("created_at")
