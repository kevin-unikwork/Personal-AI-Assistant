from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from dotenv import load_dotenv

# Ensure environment variables are loaded globally for underlying packages like LangChain
load_dotenv()

class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables and .env file.
    """
    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API Key")

    # Search
    tavily_api_key: str = Field(None, description="Tavily API Key")

    # Twilio
    twilio_account_sid: str = Field(..., description="Twilio Account SID")
    twilio_auth_token: str = Field(..., description="Twilio Auth Token")
    twilio_whatsapp_from: str = Field(..., description="Twilio WhatsApp Sender Phone Number")
    twilio_whatsapp_quick_reply_content_sid: str | None = Field(
        default=None,
        description="Optional Twilio Content SID for quick reply WhatsApp template",
    )
    twilio_whatsapp_list_picker_content_sid: str | None = Field(
        default=None,
        description="Optional Twilio Content SID for list picker WhatsApp template",
    )
    twilio_whatsapp_list_picker_option_slots: int = Field(
        default=3,
        description="Number of option placeholders configured in the list picker template",
    )
    twilio_whatsapp_list_picker_variable_keys: str | None = Field(
        default=None,
        description="Optional comma-separated list template variable keys (e.g. prompt,opt1,opt2,opt3)",
    )
    twilio_whatsapp_list_picker_button_variable_key: str | None = Field(
        default=None,
        description="Optional variable key used by template for list button text (e.g. 11)",
    )
    twilio_whatsapp_list_picker_button_text: str = Field(
        default="Choose",
        description="Text to inject for list picker button variable when configured",
    )
    twilio_log_content_variables: bool = Field(
        default=False,
        description="Enable temporary debug logs for Twilio content_variables payloads",
    )

    # Gmail/Email (SMTP/IMAP)
    google_email: str = Field(..., description="Your Gmail address", alias="GOOGLE_EMAIL")
    google_temp_password: str = Field(..., description="Your 16-character Gmail App Password", alias="GOOGLE_TEMP_PASSWORD")

    # Google APIs (Service Account for Calendar)
    google_service_account_json: str = Field(..., description="Path to Google Service Account JSON")
    google_calendar_id: str = Field(default="primary", description="Google Calendar ID")

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./personal_ai.db", description="Async SQLAlchemy Database URL")

    # App core
    secret_key: str = Field(..., description="Secure random string")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Application Logging Level")

    # Scheduler
    daily_briefing_hour: int = Field(default=7, description="Hour for daily briefing")
    daily_briefing_minute: int = Field(default=30, description="Minute for daily briefing")
    evening_checkin_hour: int = Field(default=21, description="Hour for evening check-in reminder")
    evening_checkin_minute: int = Field(default=0, description="Minute for evening check-in reminder")
    reminder_lead_minutes: int = Field(default=0, description="How many minutes before due time reminders should be sent")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        """Allow friendly env values like 'release' and 'dev'."""
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "n", "off", "release", "prod", "production"}:
                return False
        return value

# Instantiate a global settings object to be used throughout the app
settings = Settings()
