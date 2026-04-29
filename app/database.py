from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

# Create async engine with production-grade stability
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,  # Verifies connection before use
    pool_recycle=300,    # Prevents stale connections
    connect_args={
        "command_timeout": 60,
    }
)

# Async session maker
async_session = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

Base = declarative_base()

async def get_db_session():
    """Dependency to provide database sessions for FastAPI routes."""
    async with async_session() as session:
        yield session
