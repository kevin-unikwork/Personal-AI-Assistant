from fastapi import APIRouter
from app.database import async_session
from sqlalchemy import text

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check route."""
    db_status = "ok"
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
        
    return {"status": "healthy", "database": db_status}
