import sys
from loguru import logger
from app.config import settings

def setup_logger():
    """Confingure Loguru to output structured JSON."""
    logger.remove()
    
    log_format = "{message}" if settings.log_level == "DEBUG" else "{message}"
    
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.log_level,
        serialize=True, # JSON structured output
        # Keep disabled for compatibility with restricted Windows sandboxes/test envs.
        enqueue=False,
    )

setup_logger()
# Re-export logger for ease of use
__all__ = ["logger"]
