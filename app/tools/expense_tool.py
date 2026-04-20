import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, func
from langchain_core.tools import tool
from app.database import async_session
from app.models.expense import Expense
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

@tool
def log_expense(phone_number: str, amount: float, category: str = "General", description: str = "") -> str:
    """Log a daily expense to track your spending.
    
    Args:
        phone_number: User's WhatsApp number
        amount: Amount spent (e.g. 500)
        category: Category (e.g. 'Food', 'Travel', 'Medical')
        description: optional details
    """
    async def _log():
        try:
            async with async_session() as session:
                result = await session.execute(select(User).where(User.phone_number == phone_number))
                user = result.scalars().first()
                if not user:
                    return "User not found to log expense."

                new_expense = Expense(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    amount=amount,
                    category=category,
                    description=description
                )
                session.add(new_expense)
                await session.commit()
                
                return f"💸 *Expense Logged Successfully*\n\n✅ {category}: ₹{amount}\n📝 {description or 'No details'}\n\nYour weekly summary is being updated."
        except Exception as e:
            logger.error(f"Failed to log expense: {e}")
            return f"Failed to log expense: {e}"

    return _run_async(_log())

@tool
def get_expense_summary(phone_number: str, period: str = "weekly") -> str:
    """Retrieve a summary of your spending for a specific period (daily, weekly, monthly)."""
    async def _summary():
        try:
            async with async_session() as session:
                result = await session.execute(select(User).where(User.phone_number == phone_number))
                user = result.scalars().first()
                if not user:
                    return "User not found."

                days = 7 if period == "weekly" else 30 if period == "monthly" else 1
                since = datetime.utcnow() - timedelta(days=days)

                stmt = select(Expense.category, func.sum(Expense.amount)).where(
                    Expense.user_id == user.id,
                    Expense.created_at >= since
                ).group_by(Expense.category)
                
                res = await session.execute(stmt)
                categories = res.all()

                if not categories:
                    return f"No expenses found for the last {period}."

                summary_list = [f"📊 *Financial Summary ({period.capitalize()})*"]
                total = 0
                for cat, amt in categories:
                    summary_list.append(f"- {cat}: ₹{amt:.2f}")
                    total += amt
                
                summary_list.append(f"\n💰 *Total Spending*: ₹{total:.2f}")
                return "\n".join(summary_list)
        except Exception as e:
            logger.error(f"Failed to get expense summary: {e}")
            return f"Failed to get financial summary: {e}"

    return _run_async(_summary())
