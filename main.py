import contextlib
from fastapi import FastAPI
from app.api import webhook, health
from app.scheduler.jobs import scheduler, setup_scheduler
from app.database import engine, Base
import app.models  # noqa: F401 - ensure model metadata is registered before create_all
from app.utils.logger import logger

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup scheduler
    setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started.")

    # Create tables if they don't exist (useful for dev without alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler stopped.")

app = FastAPI(
    title="Personal AI Life Operator",
    description="WhatsApp-first autonomous AI assistant for daily life management.",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(webhook.router)
app.include_router(health.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
