import asyncio
from datetime import datetime, timedelta
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.database import async_session
from app.models.user import User
from app.tools.calendar_tool import list_events
from app.tools.task_tool import list_tasks
from app.tools.expense_tool import get_expense_summary
from app.tools.habit_tool import get_habit_status
from app.config import settings
from app.utils.logger import logger

@tool
def solve_life_problem(phone_number: str, problem_description: str) -> str:
    """A specialized reasoning tool for complex, multi-domain daily life challenges.
    Use this when the user is overwhelmed or asks for strategic planning across health, finance, and schedule.
    
    Args:
        phone_number: User's WhatsApp number
        problem_description: The specific challenge the user is facing
    """
    async def _solve():
        try:
            # 1. Gather comprehensive "Life State" data
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            
            # Fetch data using existing tools
            try:
                calendar_data = list_events.invoke({"date": today_str})
                # Attempt to get a weekly view as well
                next_week = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")
                tasks_data = list_tasks.invoke({"phone_number": phone_number})
                finance_data = get_expense_summary.invoke({"phone_number": phone_number, "period": "weekly"})
                habits_data = get_habit_status.invoke({"phone_number": phone_number})
            except Exception as e:
                logger.error(f"Data gathering failed for problem solver: {e}")
                return f"I tried to analyze your situation, but I ran into a technical issue gathering your data: {e}"

            # 2. Reasoning Brain (GPT-4o for high-logic strategy)
            llm = ChatOpenAI(model="gpt-4o", temperature=0.4, api_key=settings.openai_api_key)
            
            reasoning_prompt = f"""
            You are the 'First Principles' Logic Engine of a Personal AI Life Operator. 
            The user is facing a complex life problem and needs a holistic, strategic solution.
            
            --- USER PROBLEM ---
            {problem_description}
            
            --- CURRENT LIFE STATE ---
            📅 CALENDAR (Upcoming):
            {calendar_data}
            
            ✅ PENDING TASKS:
            {tasks_data}
            
            💰 FINANCE (Weekly Summary):
            {finance_data}
            
            🌱 HABIT TRACKER:
            {habits_data}
            
            --- OBJECTIVE ---
            Provide a MASTER STRATEGY to solve the user's problem. 
            1. Apply "First Principles Thinking" to simplify the issue.
            2. Suggest specific adjustments to their Schedule, Tasks, or Spending.
            3. Provide a clear 'Step 1' for the next 24 hours.
            
            TONE: Deeply analytical yet encouraging and calm. No fluff.
            FORMAT: Use WhatsApp-friendly formatting (bolding with single asterisks like *this*, icons). Be concise but thorough.
            - IMPORTANT: NEVER use double asterisks (**).
            """

            response = await llm.ainvoke([
                SystemMessage(content="You are a Master Problem Solver and Strategic Life Consultant."),
                HumanMessage(content=reasoning_prompt)
            ])
            
            return response.content

        except Exception as e:
            logger.error(f"Problem solver failed: {e}")
            return f"❌ Mastery Analysis Failed: {str(e)}"

    # Run the async logic
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.run_coroutine_threadsafe(_solve(), loop).result()
    except Exception:
        return asyncio.run(_solve())
