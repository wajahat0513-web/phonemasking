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
from services.airtable_client import save_message, find_client_by_phone, log_event
from services.ttl_manager import is_ttl_expired, handle_ttl_expiry, update_last_active
from utils.logger import log_info, log_error
from utils.request_parser import parse_incoming_payload

router = APIRouter()

@router.post("/intercept")
async def intercept(request: Request):
    """
    Callback endpoint triggered for every message inside an existing session.
    
    Twilio sends a POST request here whenever a participant sends a message
    through the Proxy service.
    
    Args:
        request (Request): The raw request object (used to extract SessionSid).
        From (str): The phone number of the sender.
        To (str): The phone number of the recipient (Proxy Number).
        Body (str): The content of the text message.
        AccountSid (str): The Twilio Account SID.
        
    Returns:
        dict: Empty dictionary to acknowledge receipt (200 OK).
    """
    # Debug: Log raw request details
    log_info(f"Intercept request headers: {dict(request.headers)}")
    log_info(f"Intercept content-type: {request.headers.get('content-type', 'MISSING')}")
    
    payload = await parse_incoming_payload(
        request,
        required_fields=[], # Make them optional here to log properly if missing
        optional_fields=["From", "To", "Body", "AccountSid", "SessionSid", "interactionBody"],
    )

    # Log the payload for debugging 422s or missing fields
    log_info(f"Intercept payload: {payload}")

    From = payload.get("From")
    To = payload.get("To")
    Body = payload.get("Body") or payload.get("interactionBody")
    account_sid = payload.get("AccountSid")
    session_sid = payload.get("SessionSid")

    # Re-enforce validation manually for better error messages
    if not all([From, To, Body]):
        missing = [k for k in ["From", "To", "Body"] if not payload.get(k)]
        log_error(f"Intercept 422: Missing fields {missing}")
        return {"status": "error", "message": f"Missing fields: {missing}"}

    # Normalize phone numbers to E.164 format (add + if missing)
    if not From.startswith("+"):
        From = f"+{From}"
    if not To.startswith("+"):
        To = f"+{To}"
    
    log_info(f"Intercepted message from {From} to {To} in session {session_sid}")

    # ---------------------------------------------------------
    # 1. Update Client Activity & Check TTL
    # ---------------------------------------------------------
    # Find the client associated with the sender's phone number.
    # Update their 'Last Active' timestamp to keep the session alive.
    # If the session has exceeded the TTL (e.g., 14 days), close it.
    client = find_client_by_phone(From)
    
    if client:
        update_last_active(client["id"], session_sid)
        
        if is_ttl_expired(client):
            handle_ttl_expiry(client)

    # ---------------------------------------------------------
    # 2. Log Message to Airtable
    # ---------------------------------------------------------
    # Save the message details to the 'Messages' table in Airtable.
    # This provides a complete history of the conversation.
    if session_sid:
        save_message(session_sid, From, To, Body)

    # ---------------------------------------------------------
    # 3. Prepend Client Name to Message
    # ---------------------------------------------------------
    # Look up client name and prepend to message for sitter clarity
    client_name = "Unknown Client"
    if client:
        client_name = client["fields"].get("Name", "Unknown Client")
    
    # Prepend client name to message body
    modified_body = f"[{client_name}]: {Body}"
    
    log_info(f"Prepending client name to message: {client_name}")
    
    # Return modified body to Twilio Proxy
    # This instructs Proxy to send the modified message instead of original
    return {"body": modified_body}
