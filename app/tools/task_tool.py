from datetime import datetime, timezone
import asyncio
import re
import dateutil.parser
import dateutil.relativedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from langchain_core.tools import tool
from app.database import async_session
from app.models.task import Task
from app.models.user import User
from app.utils.logger import logger


def _run_async(coro):
    """Run async coroutine safely from sync context (inside asyncio.to_thread)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _get_user_zoneinfo(tz_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or "Asia/Kolkata")
    except Exception:
        return ZoneInfo("Asia/Kolkata")


def _normalize_to_utc_naive(dt_str: str, user_timezone: str) -> datetime:
    """Parse user datetime and normalize to UTC-naive for DB storage."""
    parsed = dateutil.parser.parse(dt_str)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_get_user_zoneinfo(user_timezone))
    utc_dt = parsed.astimezone(timezone.utc)
    return utc_dt.replace(tzinfo=None)


def _format_utc_naive_for_user(dt_utc_naive: datetime | None, user_timezone: str) -> str:
    if not dt_utc_naive:
        return "No due date"
    local_dt = dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(_get_user_zoneinfo(user_timezone))
    return local_dt.strftime("%Y-%m-%d %I:%M %p")


def _has_explicit_date(dt_str: str) -> bool:
    """Detect whether user included a date component vs only time text."""
    patterns = [
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",
        r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b",
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b",
        r"\b(today|tomorrow)\b",
    ]
    text = dt_str.lower()
    return any(re.search(p, text) for p in patterns)


@tool
def create_reminder(phone_number: str, title: str, due_datetime: str, repeat: str = "none") -> str:
    """Create a reminder/task for the user. repeat options: none, daily, weekly, hourly."""

    async def _create():
        try:
            async with async_session() as session:
                result = await session.execute(select(User).where(User.phone_number == phone_number))
                user = result.scalars().first()
                if not user:
                    return "User not found to associate this task."

                parsed_due_utc = _normalize_to_utc_naive(due_datetime, user.timezone)
                now_utc_naive = datetime.utcnow()
                if parsed_due_utc <= now_utc_naive and not _has_explicit_date(due_datetime):
                    # Example: "11 AM" at evening should map to next day 11 AM, not immediate reminder.
                    parsed_due_utc = parsed_due_utc + dateutil.relativedelta.relativedelta(days=1)

                due_display = _format_utc_naive_for_user(parsed_due_utc, user.timezone)

                new_task = Task(
                    user_id=user.id,
                    title=title,
                    due_datetime=parsed_due_utc,
                    repeat=repeat,
                    status="pending"
                )
                session.add(new_task)
                await session.commit()
                await session.refresh(new_task)

                logger.info("Created reminder", extra={"task_id": new_task.id, "title": title})
                return (
                    f"Reminder set for '{title}'.\n"
                    f"Due: {due_display} ({user.timezone})\n"
                    f"Reference: {new_task.id}"
                )
        except Exception as e:
            logger.error("Failed to create reminder", extra={"error": str(e)})
            return f"Failed to create reminder: {str(e)}"

    return _run_async(_create())


@tool
def assign_task(phone_number: str, assignee_phone: str, title: str, assignee_email: str = None, due_datetime: str = None, description: str = "") -> str:
    """Assign a task to someone else and notify them via WhatsApp (with Email fallback)."""
    from app.utils.twilio_client import send_whatsapp_message
    from app.utils.email_client import send_email_smtp

    async def _assign():
        try:
            async with async_session() as session:
                result = await session.execute(select(User).where(User.phone_number == phone_number))
                user = result.scalars().first()
                if not user:
                    return "User not found."

                parsed_due = _normalize_to_utc_naive(due_datetime, user.timezone) if due_datetime else None

                new_task = Task(
                    user_id=user.id,
                    title=title,
                    description=description,
                    due_datetime=parsed_due,
                    assigned_to=assignee_phone,
                    assigned_by=phone_number,
                    status="pending"
                )
                session.add(new_task)
                await session.commit()

                msg = (
                    f"TASK PRIORITY NOTIFICATION\n\n"
                    f"A new task has been assigned to you.\n\n"
                    f"Title: {title}\n"
                    f"Deadline: {due_datetime or 'No specific deadline'}\n"
                    f"Assigner: {phone_number}\n\n"
                    f"Details:\n{description or 'No extra details provided.'}"
                )

                try:
                    send_whatsapp_message(assignee_phone, msg)
                    return f"Task assigned to {assignee_phone} successfully via WhatsApp."
                except Exception as wa_e:
                    logger.warning(f"WhatsApp failed: {wa_e}. Attempting email fallback...")

                    if assignee_email:
                        try:
                            email_subject = f"Task Assignment: {title}"
                            email_body = f"""
                            <h2>Task Assignment Notification</h2>
                            <p>A new task has been delegated to you.</p>
                            <hr>
                            <p><b>Task:</b> {title}</p>
                            <p><b>Deadline:</b> {due_datetime or 'Flexible'}</p>
                            <p><b>Assigned By:</b> {phone_number}</p>
                            <p><b>Details:</b> {description or 'View details in your dashboard.'}</p>
                            <br>
                            <p><i>Note: your WhatsApp number may need to opt-in to the assistant sandbox to receive mobile alerts.</i></p>
                            """
                            send_email_smtp(assignee_email, email_subject, email_body, html_content=email_body)
                            return f"WhatsApp failed, but task was delivered to {assignee_email} via email."
                        except Exception as email_err:
                            return f"Task saved, but both WhatsApp and email delivery failed. WhatsApp error: {wa_e}, Email error: {email_err}"

                    return f"Task saved, but WhatsApp delivery failed ({wa_e}). No email provided for fallback."

        except Exception as e:
            logger.error(f"Task assignment failed: {e}")
            return f"Failed to assign task: {str(e)}"

    return _run_async(_assign())


@tool
def list_tasks(phone_number: str, status: str = "pending") -> str:
    """List tasks filtered by status: pending, completed, overdue, all."""

    async def _list():
        try:
            async with async_session() as session:
                result = await session.execute(select(User).where(User.phone_number == phone_number))
                user = result.scalars().first()
                if not user:
                    return "User not found."

                stmt = select(Task).where(Task.user_id == user.id)
                if status == "overdue":
                    stmt = stmt.where(Task.status == "pending", Task.due_datetime < datetime.utcnow())
                elif status != "all":
                    stmt = stmt.where(Task.status == status)

                stmt = stmt.order_by(Task.due_datetime.asc())
                result = await session.execute(stmt)
                tasks = result.scalars().all()

                if not tasks:
                    return f"No tasks found with status '{status}'."

                task_list = [f"Tasks ({status}):"]
                for t in tasks:
                    due = _format_utc_naive_for_user(t.due_datetime, user.timezone)
                    task_list.append(f"- ID {t.id} | {t.title} | Due: {due} | Repeat: {t.repeat}")
                return "\n".join(task_list)
        except Exception as e:
            logger.error("Failed to list tasks", extra={"error": str(e)})
            return f"Failed to list tasks: {str(e)}"

    return _run_async(_list())


@tool
def complete_task(task_id: int) -> str:
    """Mark a task as completed by its ID."""

    async def _complete():
        try:
            async with async_session() as session:
                result = await session.execute(select(Task).where(Task.id == task_id))
                task = result.scalars().first()
                if not task:
                    return f"Task ID {task_id} not found."

                task.status = "completed"
                task.completed_at = datetime.utcnow()
                await session.commit()

                logger.info("Task marked completed", extra={"task_id": task_id})
                return f"Task ID {task_id} successfully marked as completed."
        except Exception as e:
            logger.error("Failed to complete task", extra={"error": str(e)})
            return f"Failed to complete task: {str(e)}"

    return _run_async(_complete())
