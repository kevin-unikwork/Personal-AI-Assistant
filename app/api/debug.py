from fastapi import APIRouter
from app.scheduler.jobs import send_daily_briefing
from app.utils.logger import logger

router = APIRouter(prefix="/debug", tags=["Debug"])

@router.get("/trigger-briefing")
async def trigger_briefing():
    """Manually trigger the daily morning briefing for all users (testing)."""
    logger.info("Manual briefing trigger initiated via debug endpoint.")
    try:
        from app.database import async_session
        from app.models.user import User
        from sqlalchemy import select
        
        async with async_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            if not users:
                return {"status": "error", "message": "No users found in database."}
                
            for user in users:
                await send_daily_briefing(user.id)
                
        return {"status": "success", "message": f"Daily briefing triggered for {len(users)} users. Check WhatsApp!"}
    except Exception as e:
        logger.error(f"Manual briefing trigger failed: {e}")
        return {"status": "error", "message": str(e)}
