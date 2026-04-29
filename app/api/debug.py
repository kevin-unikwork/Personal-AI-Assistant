from fastapi import APIRouter
from app.scheduler.jobs import send_daily_briefing
from app.utils.logger import logger

router = APIRouter(prefix="/debug", tags=["Debug"])

@router.get("/trigger-briefing")
async def trigger_briefing():
    """Manually trigger the daily morning briefing for testing."""
    logger.info("Manual briefing trigger initiated via debug endpoint.")
    try:
        await send_daily_briefing()
        return {"status": "success", "message": "Daily briefing task has been triggered. Check your WhatsApp!"}
    except Exception as e:
        logger.error(f"Manual briefing trigger failed: {e}")
        return {"status": "error", "message": str(e)}
