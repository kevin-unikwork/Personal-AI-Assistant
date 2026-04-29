import asyncio
from app.database import engine, Base
from app.models.user import User
from app.models.task import Task
from app.models.expense import Expense
from app.models.habit import Habit
from app.models.action_log import ActionLog
from app.models.daily_checkin import DailyCheckin

async def init_db():
    print("🚀 Initializing Supabase Database Structure...")
    try:
        async with engine.begin() as conn:
            # This creates all tables defined in your models
            await conn.run_sync(Base.metadata.create_all)
        print("✅ SUCCESS: All tables (users, tasks, expenses, habits, etc.) created successfully!")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize database: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
