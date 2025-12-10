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
from utils.logger import log_info
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
    payload = await parse_incoming_payload(
        request,
        required_fields=["From", "To", "Body"],
        optional_fields=["AccountSid", "SessionSid"],
    )

    From = payload["From"]
    To = payload["To"]
    Body = payload["Body"]
    account_sid = payload.get("AccountSid")
    session_sid = payload.get("SessionSid")

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

    return {}
