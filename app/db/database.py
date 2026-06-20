from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sqlalchemy import text

from app.core.config import settings
from app.db.models import Base

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Create database tables."""
    if not settings.USE_POSTGRES:
        return
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose database connections."""
    if not settings.USE_POSTGRES:
        return
    await engine.dispose()


async def check_db_health() -> bool:
    """Verify PostgreSQL connectivity."""
    if not settings.USE_POSTGRES:
        return True
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True
