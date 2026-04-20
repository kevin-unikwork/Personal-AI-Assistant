import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select
from langchain_core.tools import tool
from app.database import async_session
from app.models.daily_checkin import DailyCheckin
from app.models.task import Task
from app.models.user import User
from app.utils.logger import logger


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _validate_scale(name: str, value: int) -> str | None:
    if value < 1 or value > 10:
        return f"{name} must be between 1 and 10."
    return None


def _user_local_date(tz_name: str | None) -> datetime.date:
    try:
        tz = ZoneInfo(tz_name or "Asia/Kolkata")
    except Exception:
        tz = ZoneInfo("Asia/Kolkata")
    return datetime.now(timezone.utc).astimezone(tz).date()


@tool
def log_daily_checkin(
    phone_number: str,
    mood: int,
    energy: int,
    sleep_hours: float = 0.0,
    daily_win: str = "",
    blocker: str = "",
    note: str = "",
) -> str:
    """Save or update today's life check-in (mood, energy, sleep) to build a daily habit loop."""

    async def _log():
        try:
            mood_err = _validate_scale("Mood", mood)
            if mood_err:
                return mood_err
            energy_err = _validate_scale("Energy", energy)
            if energy_err:
                return energy_err

            async with async_session() as session:
                user_res = await session.execute(select(User).where(User.phone_number == phone_number))
                user = user_res.scalars().first()
                if not user:
                    return "User not found."
                today = _user_local_date(user.timezone)

                existing_res = await session.execute(
                    select(DailyCheckin).where(
                        DailyCheckin.user_id == user.id,
                        DailyCheckin.checkin_date == today,
                    )
                )
                row = existing_res.scalars().first()

                if row:
                    row.mood = mood
                    row.energy = energy
                    row.sleep_hours = sleep_hours or None
                    row.daily_win = daily_win or None
                    row.blocker = blocker or None
                    row.note = note or None
                    await session.commit()
                    return "Today's check-in updated. Nice consistency."

                new_row = DailyCheckin(
                    user_id=user.id,
                    checkin_date=today,
                    mood=mood,
                    energy=energy,
                    sleep_hours=sleep_hours or None,
                    daily_win=daily_win or None,
                    blocker=blocker or None,
                    note=note or None,
                )
                session.add(new_row)
                await session.commit()
                return "Check-in saved. Momentum locked for today."
        except Exception as e:
            logger.error(f"Failed to log daily check-in: {e}")
            return f"Failed to save check-in: {e}"

    return _run_async(_log())


@tool
def get_momentum_dashboard(phone_number: str) -> str:
    """Get today's momentum snapshot with score, pending workload, and one concrete next action."""

    async def _dashboard():
        try:
            async with async_session() as session:
                user_res = await session.execute(select(User).where(User.phone_number == phone_number))
                user = user_res.scalars().first()
                if not user:
                    return "User not found."
                today = _user_local_date(user.timezone)

                checkin_res = await session.execute(
                    select(DailyCheckin).where(
                        DailyCheckin.user_id == user.id,
                        DailyCheckin.checkin_date == today,
                    )
                )
                checkin = checkin_res.scalars().first()

                task_res = await session.execute(
                    select(Task).where(Task.user_id == user.id, Task.status == "pending")
                )
                pending_tasks = task_res.scalars().all()
                pending_count = len(pending_tasks)

                if not checkin:
                    return (
                        "No check-in found for today. "
                        "Share: mood(1-10), energy(1-10), sleep hours, your win, and blocker."
                    )

                score = int((checkin.mood * 0.4 + checkin.energy * 0.4 + min((checkin.sleep_hours or 0), 8) * 0.25) * 10)
                score = max(0, min(100, score))

                if pending_count >= 6:
                    next_action = "Pick 1 task and finish it in a 25-minute focus sprint."
                elif (checkin.energy or 0) <= 4:
                    next_action = "Take a short recovery break, then do one low-effort admin task."
                elif checkin.blocker:
                    next_action = f"Remove blocker first: {checkin.blocker}"
                else:
                    next_action = "Start the highest-impact pending task now."

                return (
                    f"Life Momentum Score: {score}/100\n"
                    f"- Mood: {checkin.mood}/10\n"
                    f"- Energy: {checkin.energy}/10\n"
                    f"- Sleep: {checkin.sleep_hours or 0}h\n"
                    f"- Pending tasks: {pending_count}\n"
                    f"- Daily win: {checkin.daily_win or 'Not logged'}\n"
                    f"Next best action: {next_action}"
                )
        except Exception as e:
            logger.error(f"Failed to build momentum dashboard: {e}")
            return f"Failed to build momentum dashboard: {e}"

    return _run_async(_dashboard())
