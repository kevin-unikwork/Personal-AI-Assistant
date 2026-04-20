import os
import httpx
import tempfile
import asyncio
from openai import OpenAI
from app.config import settings
from app.utils.logger import logger

# Initialize OpenAI client
client = OpenAI(api_key=settings.openai_api_key)

async def transcribe_voice_note(media_url: str) -> str:
    """Download a voice note from Twilio and transcribe it using OpenAI Whisper.
    
    Args:
        media_url: The public/authenticated URL of the media file from Twilio.
    """
    # Use system temp directory to avoid triggering uvicorn reloader
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # 1. Download the media from Twilio (Streaming for large files)
        logger.info(f"Downloading voice note from Twilio (Large File Support): {media_url}")
        
        # Increase timeout to 60s for large files
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as http_client:
            async with http_client.stream(
                "GET", 
                media_url, 
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                follow_redirects=True
            ) as response:
                if response.status_code != 200:
                    logger.error(f"Failed to download media: {response.status_code}")
                    return ""
                
                with open(tmp_path, "wb") as f:
                    async for chunk in response.iter_bytes():
                        f.write(chunk)

        # Confirm file exists and is not empty
        file_size = os.path.getsize(tmp_path)
        logger.info(f"Downloaded audio file size: {file_size / 1024:.2f} KB")
        
        if file_size > 25 * 1024 * 1024:  # OpenAI limit is 25MB
            return "Your voice note is too large for analysis (Max 25MB). Please try sending a shorter message."

        # 2. Transcribe using OpenAI Whisper (Run in thread)
        logger.info("Transcribing voice note with Whisper...")
        
        def _transcribe():
            with open(tmp_path, "rb") as audio_file:
                return client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    response_format="text"
                )
        
        transcript = await asyncio.to_thread(_transcribe)
        
        logger.info(f"Transcription complete: {transcript}")
        return str(transcript).strip()

    except Exception as e:
        logger.error(f"Voice transcription failed: {e}")
        return ""
    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
