import logging
from services.airtable_client import log_event

# Configure logging with better format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("phone_masking")

def log_info(message: str, details: str = ""):
    full_message = f"{message}" + (f" → {details}" if details else "")
    logger.info(full_message)
    try:
        log_event("INFO", message, details)
    except Exception as e:
        logger.error(f"Failed to log to Airtable: {e}")

def log_error(message: str, details: str = ""):
    full_message = f"❌ {message}" + (f" → {details}" if details else "")
    logger.error(full_message)
    try:
        log_event("ERROR", message, details)
    except Exception as e:
        logger.error(f"Failed to log to Airtable: {e}")

def log_success(message: str, details: str = ""):
    """Log successful operations with a success indicator."""
    full_message = f"✅ {message}" + (f" → {details}" if details else "")
    logger.info(full_message)
    try:
        log_event("SUCCESS", message, details)
    except Exception as e:
        logger.error(f"Failed to log to Airtable: {e}")
