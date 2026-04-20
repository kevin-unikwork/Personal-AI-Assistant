from langchain_core.tools import tool
from app.utils.twilio_client import send_whatsapp_message

@tool
def send_whatsapp(to: str, message: str) -> str:
    """Send a proactive WhatsApp message using Twilio.
    'to' should be the target phone number (e.g., '+1234567890').
    Note: Standard WhatsApp business API rules apply, only use this if requested or for critical alerts.
    """
    try:
        sid = send_whatsapp_message(to, message)
        return f"Message sent successfully. SID: {sid}"
    except Exception as e:
        return f"Failed to send message: {str(e)}"
