"""
Sessions Router (Manual Proxy Alignment)
========================================
This endpoint now mirrors the manual intercept logic to ensure that 
"Out of Session" callbacks (first contact) are handled the same way only manual proxying.
Twilio Sessions are NO LONGER created.
"""

from fastapi import APIRouter, Request, Response, status
from services.airtable_client import (
    create_or_update_client,
    get_ready_pool_number,
    assign_pool_number_to_client,
    update_client_linked_sitter,
    find_sitter_by_twilio_number,
    increment_client_error_count,
    save_message,
    update_message_status,
    log_event
)
from services.twilio_proxy import send_sms
from utils.logger import log_info, log_error
from utils.request_parser import parse_incoming_payload

router = APIRouter()

@router.post("/out-of-session")
async def out_of_session(request: Request):
    """
    Handles the initial contact from a Client to a Sitter.
    REDIRECTS to Manual Proxy Logic.
    """
    payload = await parse_incoming_payload(request, required_fields=[])
    
    From = payload.get("From", "").strip()
    To = payload.get("To", "").strip()
    Body = payload.get("Body", "")
    
    # Normalize
    if From and not From.startswith("+"): From = f"+{From}"
    if To and not To.startswith("+"): To = f"+{To}"

    log_info(f"Out-of-Session Triggered: {From} -> {To}. Executing Manual Proxy Logic.")

    # In "Out of Session", the recipient is always the Sitter's Number (To).
    sitter_recipient = find_sitter_by_twilio_number(To)
    
    if not sitter_recipient:
        log_error(f"Sitter not found for {To} in out-of-session.")
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------------------
    # MANUAL PROXY LOGIC (Same as Intercept)
    # ----------------------------------------------------------------------
    
    # 1. Find or Create Client
    client, _ = create_or_update_client(From)
    client_id = client["id"]
    client_name = client["fields"].get("Name", "Unknown")
    client_pool_num = client["fields"].get("twilio-number")
    
    # 2. Assign Pool Number if missing
    assigned_number = client_pool_num
    if not assigned_number:
        log_info(f"Client {From} has no pool number. Fetching from inventory...")
        pool_record = get_ready_pool_number()
        
        if pool_record:
            new_pool_num = pool_record["fields"].get("phone-number")
            pool_record_id = pool_record["id"]
            
            if assign_pool_number_to_client(client_id, pool_record_id, new_pool_num):
                assigned_number = new_pool_num
                log_info(f"Assigned new Pool Number {assigned_number} to Client {client_id}")
                log_event("NUMBER_ASSIGNED", f"Assigned {assigned_number} to Client {client_name}", f"Client ID: {client_id}")
            else:
                log_error("Failed to assign available pool number.")
                log_event("ASSIGNMENT_ERROR", "Failed to update Client with Pool Number", f"Client ID: {client_id}")
        else:
            log_error("CRITICAL: No Ready pool numbers available!")
            log_event("POOL_EXHAUSTED", "No Ready numbers found in Inventory (OOS)", f"Client: {From}")
            increment_client_error_count(client_id)
            return Response(status_code=status.HTTP_403_FORBIDDEN)
    
    # 3. Link Sitter
    sitter_name = sitter_recipient["fields"].get("Full Name", "Unknown Sitter")
    sitter_real_phone = sitter_recipient["fields"].get("phone-number")
    
    if not sitter_real_phone:
        log_error(f"Sitter {sitter_name} has no real Phone Number for forwarding (OOS).")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Use Record ID for linking
    update_client_linked_sitter(client_id, sitter_recipient["id"])
    
    # 4. Forward Message
    modified_body = f"[{client_name}]: {Body}"
    
    msg_id = save_message("Manual", assigned_number, sitter_real_phone, modified_body)
    
    try:
        # Send FROM Assigned Pool Number TO Sitter's REAL Number
        send_sms(from_number=assigned_number, to_number=sitter_real_phone, body=modified_body)
        log_info(f"Forwarded Client -> Sitter (OOS): {modified_body} to {sitter_real_phone}")
        
        update_message_status(msg_id, "Sent")
        
        # Return 403 to satisfy user requirement / stop Twilio
        return Response(status_code=status.HTTP_403_FORBIDDEN)
        
    except Exception as e:
        log_error(f"Failed to forward Client message (OOS)", str(e))
        log_event("FORWARD_ERROR", f"Failed to forward message from {From} (OOS)", str(e))
        increment_client_error_count(client_id)
        # Status 'Pending', Retry worker will handle
        return Response(status_code=status.HTTP_403_FORBIDDEN)
