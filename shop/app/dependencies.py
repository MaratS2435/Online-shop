from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session, get_db


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def reviews_collection():
    db = get_db()
    yield db.reviews
