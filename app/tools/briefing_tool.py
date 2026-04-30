import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.database import async_session
from app.models.task import Task
from app.models.user import User
from app.tools.calendar_tool import list_events
from app.tools.intel_tool import get_morning_intel
from app.tools.expense_tool import get_expense_summary
from app.tools.habit_tool import get_habit_status
from app.config import settings
from app.utils.logger import logger

@tool
async def get_daily_briefing(phone_number: str) -> str:
    """Generate a high-end, proactive daily briefing for the user including Calendar, Tasks, Weather, and News.
    
    Args:
        phone_number: The user's WhatsApp number (e.g. 'whatsapp:+91...')
    """
    try:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.phone_number == phone_number))
            user = result.scalars().first()
            if not user:
                return "User not found for briefing."

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        # 1. Fetch Calendar (Using .ainvoke for async safety)
        try:
            events_str = await list_events.ainvoke({"date": today_str})
        except Exception as e:
            events_str = f"No calendar access: {e}"

        # 2. Fetch Tasks
        async with async_session() as session:
            stmt = select(Task).where(
                Task.user_id == user.id,
                Task.status == "pending"
            ).order_by(Task.due_datetime.asc())
            result = await session.execute(stmt)
            tasks = result.scalars().all()
            task_str = "\n".join([f"- {t.title} (Due: {t.due_datetime})" for t in tasks]) if tasks else "No pending tasks."

        # 3. Fetch Finance & Habits
        try:
            finance_str = await get_expense_summary.ainvoke({"phone_number": phone_number, "period": "weekly"})
        except Exception:
            finance_str = "Financial data currently unavailable."
        
        try:
            habit_str = await get_habit_status.ainvoke({"phone_number": phone_number})
        except Exception:
            habit_str = "Habit stats currently unavailable."

        # 4. Fetch Intel (Weather/News)
        try:
            intel_str = await get_morning_intel.ainvoke({"location": "Surat"})
        except Exception:
            intel_str = "Weather/News currently unavailable."

        # 5. Generate Premium Response with GPT-4o-mini
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, api_key=settings.openai_api_key)
        
        prompt = f"""
        You are the user's high-end Personal Life Operator. Create an elite morning briefing.
        
        USER CONTEXT:
        - Location: Surat
        - Today's Date: {today_str}
        
        INTEL (Weather & news):
        {intel_str}
        
        CALENDAR:
        {events_str}
        
        TASKS:
        {task_str}
        
        FINANCE:
        {finance_str}

        HABITS:
        {habit_str}
        
        TONE: Elite, proactive, warm, and highly professional.
        FORMAT: Use WhatsApp formatting (bolding using single asterisks like *this*, emojis).
        - IMPORTANT: NEVER use double asterisks (**). Always use single asterisks (*) for bold text.
        - Start with a warm greeting.
        - Provide a "Command Center" summary.
        - Include sections for 📅 Schedule, ✅ Tasks, 💰 Finance (Briefly), and 🌱 Growth (Habits).
        - Give one "Pro Tip" for the day based on the calendar/tasks/spending.
        - Keep it under 1000 characters.
        """
        
        response = await llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content="Generate my daily command center briefing.")])
        return response.content

    except Exception as e:
        logger.error(f"Briefing generation failed: {e}")
        return f"Command Center is temporarily offline: {str(e)}"
