from langchain_core.tools import tool
from datetime import datetime, timedelta
import dateutil.parser
import pytz
from app.utils.google_auth import get_calendar_service
from app.tools.calendar_tool import create_event, _parse_to_utc_iso
from app.config import settings
from app.utils.logger import logger

def check_conflict(start_utc: str, end_utc: str, timezone: str = "Asia/Kolkata") -> str | None:
    """Check if the given time slot overlaps with any existing calendar events.
    Returns the title of the conflicting event if any, else None.
    """
    try:
        service = get_calendar_service()
        events_result = service.events().list(
            calendarId=settings.google_calendar_id,
            timeMin=start_utc,
            timeMax=end_utc,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if events:
            return events[0].get("summary", "Untitled Event")
        return None
    except Exception as e:
        logger.error(f"Conflict check failed: {e}")
        return None

@tool
def book_appointment(
    title: str,
    start_datetime: str,
    guest_email: str = None,
    guest_phone: str = None,
    duration_minutes: int = 30,
    description: str = "",
    timezone: str = "Asia/Kolkata"
) -> str:
    """Check availability and book a professional appointment.
    
    Args:
        title: Appointment title
        start_datetime: Requested time (e.g. '2026-04-17 14:00')
        guest_email: Email of the guest
        guest_phone: WhatsApp number of the guest
        duration_minutes: How long the appointment lasts
        description: Agenda/Description
        timezone: Timezone
    """
    try:
        start_utc = _parse_to_utc_iso(start_datetime, timezone)
        
        # Calculate end time
        start_dt = dateutil.parser.parse(start_datetime)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        end_datetime_str = end_dt.strftime("%Y-%m-%d %H:%M")
        end_utc = _parse_to_utc_iso(end_datetime_str, timezone)

        # 1. Check for Conflicts
        conflict_title = check_conflict(start_utc, end_utc, timezone)
        if conflict_title:
            return f"❌ Booking Conflict: You already have '{conflict_title}' scheduled during this time. Please suggest another slot."

        # 2. Proceed with Booking
        # We reuse the create_event tool logic
        attendees = [guest_email] if guest_email else []
        result = create_event.invoke({
            "title": f"Appointment: {title}",
            "start_datetime": start_datetime,
            "end_datetime": end_datetime_str,
            "attendees": attendees,
            "attendee_phone": guest_phone,
            "description": description or f"Appointment booked via Personal AI Assistant. Goal: {title}",
            "timezone": timezone
        })

        return f"✅ Appointment Booked Successfully!\n{result}"

    except Exception as e:
        logger.error(f"Appointment booking failed: {e}")
        return f"Failed to book appointment: {str(e)}"
