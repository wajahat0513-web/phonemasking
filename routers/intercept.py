"""
Intercept Router
================
This script handles the real-time interception and logging of messages within active sessions.

Key Functionality:
- Acts as a webhook listener for Twilio Proxy interactions.
- Logs every message (body, sender, recipient) to Airtable for auditing.
- Updates the 'Last Active' timestamp for Clients to track engagement.
- Checks and enforces Time-To-Live (TTL) policies to expire old sessions.

Endpoints:
- POST /intercept: The webhook endpoint for active session messages.
"""

from fastapi import APIRouter, Request
from services.airtable_client import save_message, find_client_by_phone, find_sitter_by_twilio_number, log_event
from services.ttl_manager import is_ttl_expired, handle_ttl_expiry, update_last_active
from services.twilio_proxy import get_participant, list_participants, add_participant, remove_participant
from utils.logger import log_info, log_error
from utils.request_parser import parse_incoming_payload
import json

router = APIRouter()

@router.post("/intercept")
async def intercept(request: Request):
    # Debug: Log raw request details
    log_info(f"Intercept request headers: {dict(request.headers)}")
    
    payload = await parse_incoming_payload(
        request,
        required_fields=[],
    )

    log_info(f"Raw parsed data: {payload}")

    # ---------------------------------------------------------
    # 1. Strategic Field Extraction
    # ---------------------------------------------------------
    session_sid = payload.get("interactionSessionSid") or payload.get("SessionSid")
    
    # Handle 'interactionData' JSON string
    interaction_data_str = payload.get("interactionData")
    body = payload.get("Body")
    if interaction_data_str and not body:
        try:
            int_data = json.loads(interaction_data_str)
            body = int_data.get("body")
        except:
            pass
    
    from_num = payload.get("From")
    to_num = payload.get("To")
    
    # If From/To missing, use Participant SIDs to fetch data
    inbound_participant_sid = payload.get("inboundParticipantSid")
    if not from_num and inbound_participant_sid and session_sid:
        participant = get_participant(session_sid, inbound_participant_sid)
        if participant:
            from_num = participant.identifier
            to_num = participant.proxy_identifier
            log_info(f"Fetched missing info from Twilio: From={from_num}, To={to_num}")

    # Final validation
    if not all([from_num, to_num, body, session_sid]):
        log_error(f"Intercept 422: Missing critical fields", f"From={from_num}, To={to_num}, Body={body}, Session={session_sid}")
        return {"status": "error", "message": "Missing critical fields"}

    # Normalize
    if not from_num.startswith("+"): from_num = f"+{from_num}"
    if not to_num.startswith("+"): to_num = f"+{to_num}"
    
    log_info(f"Processing intercept: {from_num} -> {to_num} (Session: {session_sid})")

    # ---------------------------------------------------------
    # 2. Sitter Lookup & Participant Sync
    # ---------------------------------------------------------
    # The Sitter is always associated with the 'To' number (the proxy number)
    sitter = find_sitter_by_twilio_number(to_num)
    
    if sitter:
        sitter_airtable_phone = sitter["fields"].get("Phone Number")
        log_info(f"Matched Sitter: {sitter['fields'].get('Full Name')} (DB Phone: {sitter_airtable_phone})")
        
        # SYNC CHECK: Verify if Sitter's phone number in Twilio matches Airtable
        participants = list_participants(session_sid)
        sitter_participant = next((p for p in participants if p.proxy_identifier == to_num and p.identifier != from_num), None)
        
        # Also check if Sitter is the one SENDING (outbound)
        if not sitter_participant and from_num == sitter_airtable_phone:
             sitter_participant = next((p for p in participants if p.identifier == from_num), None)

        if sitter_participant and sitter_airtable_phone:
            # Clean numbers for comparison
            p_phone = "".join(filter(str.isdigit, sitter_participant.identifier))
            db_phone = "".join(filter(str.isdigit, sitter_airtable_phone))
            
            if p_phone != db_phone:
                log_info(f"Sitter phone mismatch detected! Twilio: {p_phone}, Airtable: {db_phone}. Updating...")
                # Remove old sitter participant and add new one
                remove_participant(session_sid, sitter_participant.sid)
                add_participant(session_sid, identifier=sitter_airtable_phone, proxy_identifier=to_num)
                log_info("Successfully updated Sitter phone in Twilio session.")

    # ---------------------------------------------------------
    # 3. Client Tracking & TTL
    # ---------------------------------------------------------
    # If the sender is NOT the sitter, treat them as the client
    client = None
    if not sitter or from_num != sitter["fields"].get("Phone Number"):
        client = find_client_by_phone(from_num)
        if client:
            log_info(f"Matched client: {client['fields'].get('Name', 'Unknown')}")
            update_last_active(client["id"], session_sid)
            if is_ttl_expired(client):
                handle_ttl_expiry(client)

    # ---------------------------------------------------------
    # 4. Save & Prepend
    # ---------------------------------------------------------
    save_message(session_sid, from_num, to_num, body)

    client_name = "Unknown Client"
    if client:
        client_name = client["fields"].get("Name", "Unknown Client")
    elif sitter and from_num == sitter.get("fields", {}).get("Phone Number"):
        # If it's the Sitter talking, we don't necessarily need to prepend
        return {"body": body}
    
    modified_body = f"[{client_name}]: {body}"
    log_info(f"Final response body: {modified_body}")
    
    return {"body": modified_body}
