from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
import os

DATABASE_URL = os.getenv("DB_URL", "postgresql+asyncpg://shop:shop@localhost:5432/shop")

engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20, future=True)

# фабрика сессий
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Базовый класс моделей"""
    pass


async def init_db():
    """Создание схемы при первом старте"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)