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
def get_daily_briefing(phone_number: str) -> str:
    """Generate a high-end, proactive daily briefing for the user including Calendar, Tasks, Weather, and News.
    
    Args:
        phone_number: The user's WhatsApp number (e.g. 'whatsapp:+91...')
    """
    async def _generate():
        try:
            async with async_session() as session:
                result = await session.execute(select(User).where(User.phone_number == phone_number))
                user = result.scalars().first()
                if not user:
                    return "User not found for briefing."

            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            
            # 1. Fetch Calendar
            try:
                events_str = list_events.invoke({"date": today_str})
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
                finance_str = get_expense_summary.invoke({"phone_number": phone_number, "period": "weekly"})
            except Exception:
                finance_str = "Financial data currently unavailable."
            
            try:
                habit_str = get_habit_status.invoke({"phone_number": phone_number})
            except Exception:
                habit_str = "Habit stats currently unavailable."

            # 4. Fetch Intel (Weather/News)
            try:
                # Default to Surat or user pref if we had it
                intel_str = get_morning_intel.invoke({"location": "Surat"})
            except Exception:
                intel_str = "Weather/News currently unavailable."

            # 4. Generate Premium Response with GPT-4o-mini
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

    # Run the async logic in the current loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If in an async context, we need to handle this carefully.
            # But the orchestrator tool call is usually wrapped.
            # For simplicity in this env:
            return asyncio.run_coroutine_threadsafe(_generate(), loop).result()
    except Exception:
        return asyncio.run(_generate())

# Add a helper for sync thread safety if needed
def _run_briefing_sync(phone_number: str):
    return asyncio.run(get_daily_briefing._run(phone_number))
