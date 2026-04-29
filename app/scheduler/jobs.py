from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import async_session
from app.models.daily_checkin import DailyCheckin
from app.models.task import Task
from app.models.user import User
from app.utils.twilio_client import send_whatsapp_message
from app.utils.logger import logger

scheduler = AsyncIOScheduler()


def _safe_zoneinfo(tz_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or "Asia/Kolkata")
    except Exception:
        return ZoneInfo("Asia/Kolkata")


def _format_due_for_user(dt_utc_naive: datetime, user_timezone: str) -> str:
    tz = _safe_zoneinfo(user_timezone)
    local_dt = dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(tz)
    return local_dt.strftime("%Y-%m-%d %I:%M %p")


async def send_daily_briefing(user_id: str):
    """Proactive Daily Briefing summary of the day."""
    try:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            if not user:
                return

        from app.tools.briefing_tool import get_daily_briefing
        briefing_text = await get_daily_briefing.ainvoke({"phone_number": user.phone_number})

        send_whatsapp_message(user.phone_number, briefing_text)
        logger.info(f"Proactive briefing sent to {user.phone_number}")

    except Exception as e:
        logger.error(f"Failed to send proactive briefing: {e}")


async def check_reminders():
    """Universal Reminder Checker with recurrence logic."""
    try:
        from app.config import settings
        lead_minutes = max(0, int(settings.reminder_lead_minutes))
        async with async_session() as session:
            now = datetime.utcnow()
            stmt = select(Task, User).join(User).where(
                Task.status == "pending",
                Task.due_datetime <= now + timedelta(minutes=lead_minutes)
            ) 
            result = await session.execute(stmt)
            rows = result.all()

            for task, user in rows:
                try:
                    local_due = _format_due_for_user(task.due_datetime, user.timezone)
                    message_text = (
                        f"PRIORITY REMINDER\n\n"
                        f"{task.title}\n"
                        f"{task.description or ''}\n\n"
                        f"Target Time: {local_due} ({user.timezone})"
                    )

                    send_whatsapp_message(user.phone_number, message_text)

                    if task.repeat and task.repeat.lower() != "none":
                        if task.repeat.lower() == "hourly":
                            task.due_datetime = task.due_datetime + timedelta(hours=1)
                        elif task.repeat.lower() == "daily":
                            task.due_datetime = task.due_datetime + timedelta(days=1)
                        elif task.repeat.lower() == "weekly":
                            task.due_datetime = task.due_datetime + timedelta(weeks=1)

                        task.status = "pending"
                        logger.info(f"Recurring task {task.id} moved to next occurrence: {task.due_datetime}")
                    else:
                        task.status = "reminded"
                        logger.info(f"One-time reminder sent for task {task.id}")

                    await session.commit()
                except Exception as task_err:
                    await session.rollback()
                    logger.error(f"Reminder delivery failed for task {task.id}: {task_err}")

    except Exception as e:
        logger.error(f"Reminder check failed: {e}")


async def send_evening_checkin_nudges():
    """Ask users for a quick daily check-in if they have not logged one yet."""
    try:
        async with async_session() as session:
            users_result = await session.execute(select(User))
            users = users_result.scalars().all()

            for user in users:
                user_today = datetime.now(timezone.utc).astimezone(_safe_zoneinfo(user.timezone)).date()
                checkin_result = await session.execute(
                    select(DailyCheckin).where(
                        DailyCheckin.user_id == user.id,
                        DailyCheckin.checkin_date == user_today,
                    )
                )
                already_checked_in = checkin_result.scalars().first() is not None
                if already_checked_in:
                    continue

                msg = (
                    "Quick daily check-in?\n"
                    "Reply like: mood 7, energy 6, sleep 7, win <text>, blocker <text>."
                )
                send_whatsapp_message(user.phone_number, msg)
                logger.info(f"Evening check-in nudge sent to {user.phone_number}")
    except Exception as e:
        logger.error(f"Evening check-in nudges failed: {e}")


# Scheduling Jobs
def setup_scheduler():
    from app.config import settings

    scheduler.add_job(check_reminders, 'interval', minutes=5, id="check_reminders", replace_existing=True)

    async def global_daily_briefing():
        async with async_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            for user in users:
                await send_daily_briefing(user.id)

    scheduler.add_job(
        global_daily_briefing,
        'cron',
        id="global_daily_briefing",
        replace_existing=True,
        hour=settings.daily_briefing_hour,
        minute=settings.daily_briefing_minute
    )

    scheduler.add_job(
        send_evening_checkin_nudges,
        'cron',
        id="send_evening_checkin_nudges",
        replace_existing=True,
        hour=settings.evening_checkin_hour,
        minute=settings.evening_checkin_minute
    )
