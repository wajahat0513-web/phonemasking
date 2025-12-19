import time
import threading
from datetime import datetime, timezone
from services.airtable_client import get_pending_messages, update_message_status
from services.twilio_proxy import send_session_message, list_participants, send_sms
from utils.logger import log_info, log_error

def start_fallback_worker():
    """Starts the fallback worker in a background thread."""
    worker_thread = threading.Thread(target=_run_worker, daemon=True)
    worker_thread.start()
    log_info("Fallback Worker started in background.")

def _run_worker():
    """Main loop for the fallback worker."""
    while True:
        try:
            # Check for messages older than 2 minutes (User defined threshold)
            pending_messages = get_pending_messages(older_than_minutes=2)
            
            if pending_messages:
                log_info(f"Fallback Worker found {len(pending_messages)} pending message(s) for retry.")
                
                for record in pending_messages:
                    _retry_message(record)
                    
        except Exception as e:
            log_error("Fallback Worker encountered an error", str(e))
            
        # Poll every 60 seconds
        time.sleep(60)

def _retry_message(record):
    """Attempts to re-send a single message."""
    fields = record.get("fields", {})
    message_id = record.get("id")
    session_sid = fields.get("Session SID")
    from_num = fields.get("From")
    to_num = fields.get("To") # We need 'To' now for manual sending
    body = fields.get("Body")
    
    if not all([session_sid, from_num, body]):
        log_error(f"Cannot retry message {message_id}: Missing fields.")
        update_message_status(message_id, "Retry Aborted (Missing Fields)")
        return

    try:
        # MANUAL PROXY RETRY
        if session_sid == "Manual":
            if not to_num:
                 log_error(f"Cannot retry Manual message {message_id}: Missing 'To' field.")
                 update_message_status(message_id, "Retry Failed (Missing To)")
                 return
                 
            log_info(f"Retrying Manual Message {message_id}: {from_num} -> {to_num}")
            send_sms(from_number=from_num, to_number=to_num, body=body)
            
            update_message_status(message_id, "Sent (via Fallback)")
            log_info(f"Message {message_id} successfully re-sent via fallback.")
            return

        # LEGACY/STANDARD PROXY RETRY (If session_sid is actual SID)
        # 1. Identify participants to find a valid sender/recipient SID
        participants = list_participants(session_sid)
        recipient_p = next((p for p in participants if p.identifier != from_num), None)
        
        if not recipient_p:
            log_error(f"Cannot retry message {message_id}: Participants not found in session {session_sid}")
            update_message_status(message_id, "Retry Failed (No Participants)")
            return

        # 2. Re-send via Twilio Proxy
        send_session_message(session_sid, recipient_p.sid, body)
        
        # 3. Mark as Sent
        update_message_status(message_id, "Sent (via Fallback)")
        log_info(f"Message {message_id} successfully re-sent via fallback.")
        
    except Exception as e:
        log_error(f"Fallback retry failed for message {message_id}", str(e))
        update_message_status(message_id, "Retry Error")
