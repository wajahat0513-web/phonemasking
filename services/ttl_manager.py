"""
TTL Manager Service
===================
This script enforces Time-To-Live (TTL) policies for client sessions.

Key Functionality:
- Checks if a client's session has exceeded the allowed inactivity period (e.g., 14 days).
- Updates the 'Last Active' timestamp for clients upon new activity.
- Handles the expiration process: closing the Twilio session and logging the event.

This ensures that old, unused sessions are cleaned up and do not persist indefinitely.
"""

from datetime import datetime, timedelta, timezone
from services.airtable_client import update_client_session, log_event
from services.twilio_proxy import close_session
from utils.logger import log_info, log_error

TTL_DAYS = 14

def is_ttl_expired(client_record: dict) -> bool:
    """
    Checks if a client's session has expired based on their last activity.
    
    Args:
        client_record (dict): The client's Airtable record containing 'Last Active'.
        
    Returns:
        bool: True if the session is expired (inactive > TTL_DAYS), False otherwise.
    """
    last_active_str = client_record.get("fields", {}).get("Last Active")
    if not last_active_str:
        return False
    
    try:
        # Airtable returns ISO strings with timezones, make comparison aware
        last_active = datetime.fromisoformat(last_active_str.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) - last_active > timedelta(days=TTL_DAYS):
            return True
    except Exception as e:
        log_error("Error parsing Last Active date", str(e))
        return False
        
    return False

def update_last_active(client_id: str, session_sid: str):
    """
    Updates the 'Last Active' timestamp for a client to the current time.
    
    This is called whenever a new message is intercepted, resetting the TTL clock.
    
    Args:
        client_id (str): The Client's Airtable Record ID.
        session_sid (str): The current Session SID.
    """
    try:
        update_client_session(client_id, session_sid)
        log_info(f"Updated Last Active for client {client_id}")
    except Exception as e:
        log_error(f"Failed to update Last Active for client {client_id}", str(e))

def handle_ttl_expiry(client_record: dict):
    """
    Executes the cleanup logic when a session expires.
    
    1. Closes the Twilio Proxy Session.
    2. Logs the expiration event to Airtable.
    
    Args:
        client_record (dict): The client's Airtable record.
    """
    client_id = client_record["id"]
    session_sid = client_record.get("fields", {}).get("Session SID")
    
    log_info(f"TTL Expired for client {client_id}")
    
    if session_sid:
        try:
            close_session(session_sid)
        except Exception as e:
            log_error(f"Failed to close session {session_sid} on TTL expiry", str(e))
    
    log_event("TTL_EXPIRY", f"Client {client_id} expired. Session {session_sid} closed.")
