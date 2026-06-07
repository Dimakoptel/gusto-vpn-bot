from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import core_settings

engine = create_async_engine(
    core_settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=30
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

# Redis client (async)
redis_client = None

try:
    import redis.asyncio as redis
    redis_client = redis.from_url(
        core_settings.REDIS_URL,
        decode_responses=True
    )
except Exception:
    pass  # Redis optional for development

async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
