import smtplib
import imaplib
import time
from email.message import EmailMessage
from app.config import settings
from app.utils.logger import logger

def send_email_smtp(to: str, subject: str, body: str, html_content: str = None, attachment: dict = None):
    """
    Send an email using Gmail SMTP and an App Password.
    
    Args:
        to: Recipient email
        subject: Subject line
        body: Plain text body
        html_content: Optional HTML body
        attachment: Optional dict with keys: 'filename', 'content' (bytes), 'mimetype'
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.google_email
    msg["To"] = to
    msg.set_content(body)

    if html_content:
        msg.add_alternative(html_content, subtype="html")

    if attachment:
        msg.add_attachment(
            attachment['content'],
            maintype='application',
            subtype=attachment.get('subtype', 'octet-stream'),
            filename=attachment['filename']
        )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.google_email, settings.google_temp_password)
            server.send_message(msg)
        
        logger.info(f"Email sent via SMTP to {to}")
        return True
    except Exception as e:
        logger.error(f"SMTP send failed: {e}")
        raise e

def save_draft_imap(to: str, subject: str, body: str, html_content: str = None):
    """Save an email to the Gmail 'Drafts' folder using IMAP."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.google_email
    msg["To"] = to
    msg.set_content(body)

    if html_content:
        msg.add_alternative(html_content, subtype="html")

    try:
        with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
            imap.login(settings.google_email, settings.google_temp_password)
            try:
                imap.select('"[Gmail]/Drafts"')
            except Exception:
                imap.select("Drafts")

            imap.append('"[Gmail]/Drafts"', None, imaplib.Internaldate2tuple(time.time()), msg.as_bytes())
        
        logger.info(f"Draft saved via IMAP for {to}")
        return True
    except Exception as e:
        logger.error(f"IMAP draft save failed: {e}")
        raise e
