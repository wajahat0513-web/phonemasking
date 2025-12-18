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

from fastapi import APIRouter, Request, Response, status
from services.airtable_client import save_message, find_client_by_phone, find_sitter_by_twilio_number, log_event
from services.ttl_manager import is_ttl_expired, handle_ttl_expiry, update_last_active
from services.twilio_proxy import get_participant, list_participants, add_participant, remove_participant, send_session_message
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
    sitter_airtable_phone = None
    
    if sitter:
        sitter_airtable_phone = sitter["fields"].get("Phone Number")
        log_info(f"Matched Sitter: {sitter['fields'].get('Full Name')} (DB Phone: {sitter_airtable_phone})")
        
        # SYNC CHECK: Verify if Sitter's phone number in Twilio matches Airtable
        participants = list_participants(session_sid)
        
        # 1. Is there ANY participant already using the sitter's CURRENT phone number?
        current_sitter_p = next((p for p in participants if p.identifier == sitter_airtable_phone), None)
        
        # 2. If the current sitter isn't in the session, but we identified the sitter by context, 
        # we check for an "outdated" sitter participant (someone using the proxy but with a different number)
        if not current_sitter_p:
            # The 'Outdated' sitter is the one who IS NOT the sender and IS NOT using the client's number
            outdated_sitter_p = next((p for p in participants if p.identifier != from_num), None)
            
            if outdated_sitter_p:
                log_info(f"Sitter phone mismatch detected! Old participant: {outdated_sitter_p.identifier}, New Airtable: {sitter_airtable_phone}. Syncing...")
                # Remove old sitter and add new one
                remove_participant(session_sid, outdated_sitter_p.sid)
                try:
                    add_participant(session_sid, identifier=sitter_airtable_phone, proxy_identifier=to_num)
                    log_info("Successfully updated Sitter phone in Twilio session.")
                except Exception as sync_err:
                    log_error("Failed to re-add sitter during sync", str(sync_err))
            else:
                # Session might be empty or missing sitter, add them
                log_info(f"Sitter missing from session, adding {sitter_airtable_phone}")
                add_participant(session_sid, identifier=sitter_airtable_phone, proxy_identifier=to_num)

    # ---------------------------------------------------------
    # 3. Client Tracking & TTL
    # ---------------------------------------------------------
    # If the sender is NOT the sitter, treat them as the client
    client = None
    if not sitter or from_num != sitter["fields"].get("Phone Number"):
        client = find_client_by_phone(from_num)
        if client:
            log_info(f"Matched client: {client['fields'].get('Name', 'Unknown')}")
            
            # TTL CHECK: If expired, we "revive" it because they messaged.
            # We reset the timer by updating last active.
            if is_ttl_expired(client):
                log_info(f"Session technically expired (>14 days), but reviving due to new message from {from_num}")
                log_event("SESSION_REVIVED", f"Client {client.get('id')} messaged after expiry. Resetting TTL.")
            
            # Pass sitter["id"] to ensure the 'Linked Sitter' field is maintained
            update_last_active(client["id"], session_sid, sitter_id=sitter.get("id") if sitter else None)

    # ---------------------------------------------------------
    # 4. Save & Prepend (Block & Re-send Strategy)
    # ---------------------------------------------------------
    save_message(session_sid, from_num, to_num, body)

    # LOOP PREVENTION: 
    # If the body already has our prepend marker, it means this is the intercept for 
    # the manual message we just sent. We return 200 OK to allow it to be logged/active,
    # but we don't want to modify it or re-trigger another send.
    if body.startswith("[") and "]:" in body:
        log_info(f"Intercept triggered for our own modified message: '{body}'. Allowing through.")
        # Returning an empty dict or status OK is safer than re-prepending
        return {"status": "ok"}

    client_name = "Unknown Client"
    if client:
        client_name = client["fields"].get("Name", "Unknown Client")
    
    # Check if the sender is the sitter
    is_sitter_sending = False
    if sitter and from_num == sitter.get("fields", {}).get("Phone Number"):
        is_sitter_sending = True

    if is_sitter_sending:
        log_info("Message is from Sitter, allowing through normally.")
        return {"body": body}
    
    # If we are here, it's a message from a client (or unknown) that needs name prepending.
    modified_body = f"[{client_name}]: {body}"
    log_info(f"Triggering Block & Re-send for Client message. Modified: {modified_body}")
    
    # Find participants to ensure we have the right Client SID for re-sending
    # Manually send the message through proxy session
    # We identify the recipient (Sitter) participant
    participants = list_participants(session_sid)
    
    # Log all for debug
    log_info(f"Verifying participants for re-send in session {session_sid}...")
    recipient_p = None
    for p in participants:
        log_info(f" - Participant: SID={p.sid}, Phone={p.identifier}, Proxy={p.proxy_identifier}")
        # The recipient is whoever is NOT the sender (from_num)
        if p.identifier != from_num:
            recipient_p = p

    if recipient_p:
        log_info(f"Targeting recipient {recipient_p.identifier} (SID: {recipient_p.sid}) for modified message.")
        # IMPORTANT: In Twilio Proxy, creating a MessageInteraction on a participant resource 
        # sends the message TO that participant.
        send_session_message(session_sid, recipient_p.sid, modified_body)
        log_info("Manual message sent via API. Returning 403 to block the original raw message.")
        return Response(status_code=status.HTTP_403_FORBIDDEN)
    else:
        log_error("CRITICAL: Could not identify a recipient participant. Falling back to 200.")
        return {"body": modified_body}
