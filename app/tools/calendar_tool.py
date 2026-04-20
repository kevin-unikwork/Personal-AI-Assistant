from langchain_core.tools import tool
from app.utils.google_auth import get_calendar_service
from app.utils.email_client import send_email_smtp
from app.utils.twilio_client import send_whatsapp_message
from app.config import settings
from app.utils.logger import logger
from datetime import datetime, timedelta
import dateutil.parser
import pytz


def _parse_to_utc_iso(dt_str: str, user_tz: str = "Asia/Kolkata") -> str:
    """Parse a datetime string and convert to UTC ISO 8601 format."""
    try:
        dt = dateutil.parser.parse(dt_str)
        if dt.tzinfo is None:
            local_tz = pytz.timezone(user_tz)
            dt = local_tz.localize(dt)
        dt_utc = dt.astimezone(pytz.UTC)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return dt_str

def _check_conflict(start_utc: str, end_utc: str) -> str | None:
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

def _generate_ics(title: str, start_utc: str, end_utc: str, description: str) -> str:
    """Generate a basic iCalendar (.ics) string."""
    # Convert '2026-04-17T10:00:00Z' to '20260417T100000Z'
    fmt = lambda s: s.replace("-", "").replace(":", "")
    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Personal AI Assistant//EN",
        "BEGIN:VEVENT",
        f"DTSTART:{fmt(start_utc)}",
        f"DTEND:{fmt(end_utc)}",
        f"SUMMARY:{title}",
        f"DESCRIPTION:{description}",
        "STATUS:CONFIRMED",
        "SEQUENCE:0",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    return "\r\n".join(ics)

def _generate_html_body(title: str, start_time: str, description: str, link: str) -> str:
    """Generate a professional HTML email body for meeting invitations."""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
        <h2 style="color: #4285F4;">📅 Meeting Invitation</h2>
        <p>You have been invited to a new meeting scheduled via <b>Kevin's Personal AI Assistant</b>.</p>
        
        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0;">{title}</h3>
            <p><b>Time:</b> {start_time}</p>
            <p><b>Description:</b> {description or 'No description provided.'}</p>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="{link}" style="background-color: #4285F4; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">View in Google Calendar</a>
        </div>
        
        <p style="font-size: 12px; color: #777; margin-top: 40px; text-align: center;">
            Attached is a calendar file (.ics). Open it to add this event to your calendar automatically.
        </p>
    </div>
    """

@tool
def create_event(
    title: str,
    start_datetime: str,
    end_datetime: str = None,
    attendees: list = [],
    attendee_phone: str = None,
    description: str = "",
    timezone: str = "Asia/Kolkata",
    check_conflict: bool = True
) -> str:
    """Create a Google Calendar event with automatic conflict detection.
    
    Args:
        title: Event title/name
        start_datetime: Start time (e.g. '2026-04-17 10:00')
        end_datetime: End time. Default is start + 1 hour.
        attendees: List of attendee email addresses
        attendee_phone: optional WhatsApp number for the attendee (e.g. '+9199094xxxxx')
        description: optional description
        timezone: Timezone e.g. 'Asia/Kolkata'
        check_conflict: Whether to check for available slots first.
    """
    try:
        service = get_calendar_service()
        start_utc = _parse_to_utc_iso(start_datetime, timezone)
        
        if not end_datetime:
            start_dt = dateutil.parser.parse(start_datetime)
            end_dt = start_dt + timedelta(hours=1)
            end_datetime = end_dt.strftime("%Y-%m-%d %H:%M")
        
        end_utc = _parse_to_utc_iso(end_datetime, timezone)

        # Proactive Conflict Detection
        if check_conflict:
            conflict_title = _check_conflict(start_utc, end_utc)
            if conflict_title:
                return f"❌ Scheduling Conflict: You already have '{conflict_title}' at this time. Should I suggest another slot?"

        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_utc, "timeZone": "UTC"},
            "end":   {"dateTime": end_utc,   "timeZone": "UTC"},
        }

        # Smart Fallback for description
        if not description:
            description = f"Meeting regarding: {title}"

        # Try inserting with attendees
        has_attendees = bool(attendees)
        if has_attendees:
            event["attendees"] = [{"email": a} for a in attendees if a]

        try:
            created = service.events().insert(
                calendarId=settings.google_calendar_id,
                body=event,
                sendUpdates="all" if has_attendees else "none"
            ).execute()
            link = created.get("htmlLink", "")
            return f"Event '{title}' created successfully. View it here: {link}"

        except Exception as e:
            # Fallback for Service Accounts (which cannot invite attendees)
            if "forbiddenForServiceAccounts" in str(e) or "403" in str(e):
                logger.warning("Service account cannot invite attendees. Creating event without them and sending manual email.")
                # Remove attendees and retry
                event.pop("attendees", None)
                created = service.events().insert(
                    calendarId=settings.google_calendar_id,
                    body=event
                ).execute()
                
                link = created.get("htmlLink", "")
                
                # Proactive WhatsApp Invitation
                if attendee_phone:
                    try:
                        wa_message = f"📅 *Meeting Invitation*\n\nYou have been invited to: *{title}*\nTime: {start_datetime}\n\nView details: {link}"
                        send_whatsapp_message(attendee_phone, wa_message)
                        logger.info(f"WhatsApp invite sent to {attendee_phone}")
                    except Exception as wa_err:
                        logger.error(f"Failed to send WhatsApp invite: {wa_err}")

                # Send manual professional emails via SMTP
                if has_attendees:
                    html_body = _generate_html_body(title, start_datetime, description, link)
                    plain_body = f"Invitation: {title}\nTime: {start_datetime}\nDescription: {description}\nLink: {link}"
                    ics_content = _generate_ics(title, start_utc, end_utc, description)
                    
                    attachment = {
                        "filename": "invite.ics",
                        "content": ics_content.encode("utf-8"),
                        "subtype": "calendar"
                    }
                    
                    for a in attendees:
                        try:
                            send_email_smtp(a, f"Invitation: {title}", plain_body, html_content=html_body, attachment=attachment)
                        except Exception as email_err:
                            logger.error(f"Failed to send manual invite email to {a}: {email_err}")
                
                return f"Event '{title}' created (professional invites sent via email). View: {link}"
            else:
                raise e

    except Exception as e:
        logger.error(f"Calendar error: {e}")
        return f"Failed to create event: {str(e)}"

# Rest of the file (list_events, etc.) remains unchanged
@tool
def list_events(date: str, timezone: str = "Asia/Kolkata") -> str:
    """List all Google Calendar events for a given date."""
    try:
        service = get_calendar_service()
        local_tz = pytz.timezone(timezone)
        start_of_day = local_tz.localize(datetime.strptime(date, "%Y-%m-%d"))
        end_of_day = start_of_day + timedelta(days=1)

        start_utc = start_of_day.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_utc   = end_of_day.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        events_result = service.events().list(
            calendarId=settings.google_calendar_id,
            timeMin=start_utc,
            timeMax=end_utc,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events: return f"No events found for {date}."

        result = [f"Events for {date}:"]
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            try:
                dt = dateutil.parser.parse(start)
                if dt.tzinfo: dt = dt.astimezone(local_tz)
                start_display = dt.strftime("%I:%M %p")
            except Exception: start_display = start
            result.append(f"• {start_display} — {event.get('summary', 'No title')}")

        return "\n".join(result)

    except Exception as e:
        return f"Failed to list events: {str(e)}"
