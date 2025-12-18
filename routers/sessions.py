"""
Sessions Router
================
This script handles the creation and management of communication sessions between Clients and Sitters.

Key Functionality:
- Handles the initial "Out of Session" contact when a Client texts a Sitter's proxy number.
- Creates a new Client record in Airtable if one doesn't exist.
- Initiates a Twilio Proxy Session to mask real phone numbers.
- Adds both the Client and Sitter as participants to the secure session.
- Logs the session creation event in Airtable for auditing.

Endpoints:
- POST /out-of-session: The entry point for new conversations.
"""

from fastapi import APIRouter, HTTPException, Request
from services.airtable_client import (
    find_sitter_by_twilio_number,
    find_client_by_phone,
    create_or_update_client,
    update_client_session,
    log_event,
)
from services.twilio_proxy import create_session, add_participant
from utils.logger import log_info, log_error, log_success
from utils.request_parser import parse_incoming_payload

router = APIRouter()

@router.post("/out-of-session")
async def out_of_session(request: Request):
    """
    Handles the initial contact from a Client to a Sitter (Out of Session).
    
    This endpoint is triggered by Twilio when a message is sent to a Proxy Number
    that is not currently part of an active session.
    
    Args:
        From (str): The phone number of the sender (Client).
        To (str): The Twilio proxy number the message was sent to (assigned to a Sitter).
        
    Returns:
        dict: Status and Session SID on success.
    """
    payload = await parse_incoming_payload(
        request, required_fields=["From", "To"], optional_fields=[]
    )

    From = payload["From"]
    To = payload["To"]

    # Normalize phone numbers to E.164 format (add + if missing)
    if not From.startswith("+"):
        From = f"+{From}"
    if not To.startswith("+"):
        To = f"+{To}"
    
    log_info(f"Out of session message from {From} to {To}")

    # ---------------------------------------------------------
    # 1. Lookup Sitter by Twilio Number
    # ---------------------------------------------------------
    # We need to identify which Sitter is assigned to the proxy number (To)
    # that received the message.
    sitter = find_sitter_by_twilio_number(To)
    if not sitter:
        log_error(f"Sitter not found for Twilio number {To}")
        return {"status": "error", "message": "Sitter not found"}
    
    sitter_id = sitter["id"]
    sitter_real_phone = sitter["fields"].get("Phone Number")

    # ---------------------------------------------------------
    # 2. Lookup or Create Client Record
    # ---------------------------------------------------------
    # Check if the sender (From) is already a known Client.
    # If not, create a new Client record in Airtable.
    # Uses upsert logic to prevent duplicates if Zap 1 hasn't synced yet.
    client = find_client_by_phone(From)
    if not client:
        client, was_created = create_or_update_client(From)
        if was_created:
            log_info(f"Created new shell client record for {From} (will be updated by Zap 1)")
        else:
            log_info(f"Found existing client record for {From}")
    
    client_id = client["id"]

    # ---------------------------------------------------------
    # 3. Create Twilio Proxy Session
    # ---------------------------------------------------------
    # Initialize a new Proxy Session in Twilio. This session acts as the
    # secure bridge that masks phone numbers between participants.
    try:
        session_sid = create_session(sitter_id, client_id)
    except Exception as e:
        log_error("Failed to create session", str(e))
        raise HTTPException(status_code=500, detail="Failed to create session")

    # ---------------------------------------------------------
    # 4. Add Participants to Session (with Conflict Resolution)
    # ---------------------------------------------------------
    def sync_participants_safe(session_sid, To, From, sitter_real_phone, retry=True):
        try:
            from services.twilio_proxy import list_participants, close_session
            existing_ps = list_participants(session_sid)
            existing_identifiers = [p.identifier for p in existing_ps]

            if sitter_real_phone not in existing_identifiers:
                add_participant(session_sid, identifier=sitter_real_phone, proxy_identifier=To)
            
            if From not in existing_identifiers:
                add_participant(session_sid, identifier=From, proxy_identifier=To)
            
            return True
        except Exception as e:
            err_msg = str(e)
            if "already in use" in err_msg.lower() and "KC" in err_msg and retry:
                import re
                match = re.search(r'(KC[a-f0-9]{32})', err_msg)
                if match:
                    conflicting_sid = match.group(1)
                    log_info(f"Detected stuck session {conflicting_sid}. Cleaning up before retry...")
                    close_session(conflicting_sid)
                    # Retry once
                    return sync_participants_safe(session_sid, To, From, sitter_real_phone, retry=False)
            
            log_error("Final Participant Sync Failure", err_msg)
            return False

    if not sync_participants_safe(session_sid, To, From, sitter_real_phone):
        raise HTTPException(status_code=500, detail="Failed to sync participants even after cleanup retry.")

    # ---------------------------------------------------------
    # 5. Finalize: Update Client Record & Log Success
    # ---------------------------------------------------------
    # ONLY update Airtable after we are 100% sure Twilio is ready.
    # This prevents out-of-sync session IDs in your database.
    update_client_session(client_id, session_sid, sitter_id=sitter_id)

    log_event("SESSION_CREATED", f"Session {session_sid} created for Sitter {sitter_id} and Client {client_id}")
    log_success("Session created successfully", f"Session: {session_sid}, Client: {From}, Sitter: {sitter_real_phone}")

    return {"status": "success", "session_sid": session_sid}
