from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

import socket

# Create async engine with production-grade stability and IPv4 forcing
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "command_timeout": 60,
        "ssl": "require",  # Mandatory for Supabase direct connections in the cloud
        "server_settings": {
            "tcp_user_timeout": "60000",
        }
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
