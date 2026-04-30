import uuid
from datetime import datetime, timedelta
from sqlalchemy import select
from langchain_core.tools import tool
from app.database import async_session
from app.models.habit import Habit
from app.models.user import User
from app.utils.logger import logger

@tool
async def track_habit(phone_number: str, name: str) -> str:
    """Mark a daily habit (e.g., 'Gym', 'Meditation') as completed for today.
    
    Args:
        phone_number: User's WhatsApp number
        name: Habit name
    """
    try:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.phone_number == phone_number))
            user = result.scalars().first()
            if not user:
                return "User not found."

            # Find existing habit for this user
            stmt = select(Habit).where(Habit.user_id == user.id, Habit.name == name)
            res = await session.execute(stmt)
            habit = res.scalars().first()

            today = datetime.utcnow().date()
            if not habit:
                habit = Habit(id=uuid.uuid4(), user_id=user.id, name=name, streak=1, last_completed=datetime.utcnow())
                session.add(habit)
                msg = f"🌟 *New Habit Started!* \n\nGreat job starting '{name}'. Your streak begins now: *1 day*."
            else:
                last_date = habit.last_completed.date() if habit.last_completed else None
                if last_date == today:
                    return f"You've already completed '{name}' today! Keep the momentum for tomorrow."
                
                if last_date == today - timedelta(days=1):
                    habit.streak += 1
                    msg = f"🔥 *Keep it up!* \n\nYour streak for '{name}' is now *{habit.streak} days*."
                else:
                    habit.streak = 1
                    msg = f"🔄 *Streak Reset.* \n\nDon't worry, every day is a new start. Your streak for '{name}' is back to *1 day*."
                
                habit.last_completed = datetime.utcnow()
            
            await session.commit()
            return msg
    except Exception as e:
        logger.error(f"Failed to track habit: {e}")
        return f"Failed to track habit: {e}"

@tool
async def get_habit_status(phone_number: str) -> str:
    """Get a summary of all your habit streaks and current status."""
    try:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.phone_number == phone_number))
            user = result.scalars().first()
            if not user:
                return "User not found."

            stmt = select(Habit).where(Habit.user_id == user.id)
            res = await session.execute(stmt)
            habits = res.scalars().all()

            if not habits:
                return "No habits being tracked yet. Start one by saying 'Finished my Gym session'!"

            summary = ["🌱 *Habit Mastery Dashboard*"]
            today = datetime.utcnow().date()
            for h in habits:
                status = "✅ Done" if h.last_completed and h.last_completed.date() == today else "⏳ Pending"
                summary.append(f"- *{h.name}*: {status} | 🔥 Streak: *{h.streak}*")
            
            return "\n".join(summary)
    except Exception as e:
        logger.error(f"Failed to get habit status: {e}")
        return f"Failed to get habit status: {e}"
