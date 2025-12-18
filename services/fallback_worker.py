import time
import threading
from datetime import datetime, timezone
from services.airtable_client import get_pending_messages, update_message_status
from services.twilio_proxy import send_session_message, list_participants
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
            # Check for messages older than 5 minutes
            pending_messages = get_pending_messages(older_than_minutes=5)
            
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
    body = fields.get("Body")
    
    if not all([session_sid, from_num, body]):
        log_error(f"Cannot retry message {message_id}: Missing fields.")
        update_message_status(message_id, "Retry Aborted (Missing Fields)")
        return

    try:
        # 1. Identify participants to find a valid sender/recipient SID
        # We'll try to find a sender SID that matches the from_num
        participants = list_participants(session_sid)
        sender_p = next((p for p in participants if p.identifier == from_num), None)
        recipient_p = next((p for p in participants if p.identifier != from_num), None)
        
        if not sender_p or not recipient_p:
            log_error(f"Cannot retry message {message_id}: Participants not found in session {session_sid}")
            update_message_status(message_id, "Retry Failed (No Participants)")
            return

        # 2. Re-send via Twilio (Logic: Send TO the recipient)
        # Twilio Message Interactions create(body=body) is called on a participant sid.
        # As per our previous fix, creating on the recipient SID sends it TO them.
        send_session_message(session_sid, recipient_p.sid, body)
        
        # 3. Mark as Sent
        update_message_status(message_id, "Sent (via Fallback)")
        log_info(f"Message {message_id} successfully re-sent via fallback.")
        
    except Exception as e:
        log_error(f"Fallback retry failed for message {message_id}", str(e))
        # Keep it as Pending or mark as Failed? 
        # We'll mark as 'Retry Error' to avoid infinite loops if it's a persistent error
        update_message_status(message_id, "Retry Error")
