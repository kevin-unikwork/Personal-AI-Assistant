from email.message import EmailMessage
from langchain_core.tools import tool
from app.utils.email_client import send_email_smtp, save_draft_imap
from app.utils.logger import logger
from app.config import settings

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email using SMTP and a Gmail App Password.
    
    Args:
        to: Recipient email address
        subject: Email subject line  
        body: Email body text
    
    Returns:
        Confirmation message or error.
    
    IMPORTANT: Always get user confirmation before calling this tool.
    """
    try:
        send_email_smtp(to, subject, body)
        logger.info(f"Email sent to {to}", extra={"subject": subject})
        return f"Email successfully sent to {to} with subject '{subject}'."

    except Exception as e:
        logger.error("Failed to send email via SMTP", extra={"error": str(e)})
        return f"Failed to send email: {str(e)}"


@tool
def draft_email(to: str, subject: str, body: str) -> str:
    """Save an email as a Gmail draft (does NOT send immediately — safer option).
    
    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body text
    
    Returns:
        Confirmation that draft was saved.
    """
    try:
        save_draft_imap(to, subject, body)
        logger.info(f"Email draft created for {to}", extra={"subject": subject})
        return f"Email draft saved for {to} with subject '{subject}'. You can review and send it from your Gmail Drafts folder."

    except Exception as e:
        logger.error("Failed to draft email via IMAP", extra={"error": str(e)})
        return f"Failed to create draft: {str(e)}"
