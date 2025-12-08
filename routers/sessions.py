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

from fastapi import APIRouter, Form, HTTPException
from services.airtable_client import (
    find_sitter_by_twilio_number, 
    find_client_by_phone, 
    create_client, 
    update_client_session, 
    log_event
)
from services.twilio_proxy import create_session, add_participant
from utils.logger import log_info, log_error, log_success

router = APIRouter()

@router.post("/out-of-session")
async def out_of_session(
    From: str = Form(...),
    To: str = Form(...)
):
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
    # Normalize phone numbers to E.164 format (add + if missing)
    if not From.startswith('+'):
        From = f"+{From}"
    if not To.startswith('+'):
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
    client = find_client_by_phone(From)
    if not client:
        client = create_client(From)
        log_info(f"Created new client record for {From}")
    
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
    # 4. Add Participants to Session
    # ---------------------------------------------------------
    # Add the Sitter and the Client to the session.
    # - Sitter: Identified by their real phone number, communicating via the Proxy Number (To).
    # - Client: Identified by their real phone number (From), communicating via the Proxy Number (To).
    try:
        # Add participants WITHOUT specifying proxy_identifier
        # Twilio will automatically assign a proxy number from the pool
        add_participant(session_sid, identifier=sitter_real_phone)
        add_participant(session_sid, identifier=From)
    except Exception as e:
        log_error("Failed to add participants", str(e))
        raise HTTPException(status_code=500, detail="Failed to add participants")

    # ---------------------------------------------------------
    # 5. Update Client Record
    # ---------------------------------------------------------
    # Store the new Session SID and update the Last Active timestamp
    # in the Client's Airtable record.
    update_client_session(client_id, session_sid)

    # ---------------------------------------------------------
    # 6. Log Event
    # ---------------------------------------------------------
    # Log the successful creation of the session to the Audit Log.
    log_event("SESSION_CREATED", f"Session {session_sid} created for Sitter {sitter_id} and Client {client_id}")
    log_success("Session created successfully", f"Session: {session_sid}, Client: {From}, Sitter: {sitter_real_phone}")

    return {"status": "success", "session_sid": session_sid}
