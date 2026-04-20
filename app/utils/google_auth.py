import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.config import settings

# Scopes needed for Calendar Service Account
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """
    Builds and returns the Google Calendar API service using a Service Account.
    
    Service accounts are much easier to set up but have one limitation:
    They cannot 'invite attendees' (send emails) without domain-wide delegation.
    
    We handle this by sending a manual notification email via SMTP in 
    the calendar_tool if an invite is needed.
    """
    json_path = settings.google_service_account_json
    if not os.path.exists(json_path):
        raise FileNotFoundError(
            f"Google service account file not found: {json_path}\n"
            "Please ensure you've placed your .json key file in the project folder "
            "and updated GOOGLE_SERVICE_ACCOUNT_JSON in .env"
        )
    
    creds = service_account.Credentials.from_service_account_file(
        json_path, scopes=CALENDAR_SCOPES
    )
    return build('calendar', 'v3', credentials=creds)

# get_gmail_service is removed as we now use SMTP/IMAP via email_client.py
