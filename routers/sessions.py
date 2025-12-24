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
    find_client_by_twilio_number,
    find_client_by_phone,
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

    # ==============================================================================
    # 1. CHECK IF SITTER IS SENDER (Outbound: Sitter -> Client)
    # ==============================================================================
    sitter_sender = find_sitter_by_twilio_number(From)
    
    if sitter_sender:
        log_info(f"Sender is Sitter {sitter_sender['fields'].get('Full Name')}. Routing to Client...")
        
        client_recipient = find_client_by_twilio_number(To)
        
        if client_recipient:
            client_real_phone = client_recipient["fields"].get("phone-number")
            log_info(f"Found linked Client: {client_recipient['fields'].get('Name')} ({client_real_phone})")
            
            try:
                msg_id = save_message("Manual", To, client_real_phone, Body)
                sitter_entry_point = sitter_sender["fields"].get("twilio-number")
                
                if not sitter_entry_point:
                    log_error(f"Sitter {sitter_sender['fields'].get('Full Name')} missing entry point number.")
                    update_message_status(msg_id, "Failed (Missing Sitter Entry Point)")
                    return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

                send_sms(from_number=sitter_entry_point, to_number=client_real_phone, body=Body)
                update_message_status(msg_id, "Sent")
                log_info(f"Successfully forwarded Sitter -> Client (OOS) using: {sitter_entry_point}")
                return Response(status_code=status.HTTP_200_OK)
            except Exception as e:
                log_error("Failed to forward Sitter reply (OOS)", str(e))
                return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            log_error(f"No Client found assigned to Pool Number {To} (OOS).")
            return Response(status_code=status.HTTP_200_OK)

    # ==============================================================================
    # 2. CHECK IF RECIPIENT IS SITTER (Inbound: Client -> Sitter)
    # ==============================================================================
    sitter_recipient = find_sitter_by_twilio_number(To)
    
    if sitter_recipient:
        log_info(f"Recipient is Sitter {sitter_recipient['fields'].get('Full Name')}. Identifying Client Handset...")
        
        # 1. Find Client explicitly by Handset (From)
        log_info(f"Handset identification: querying for Sender={From}")
        client = find_client_by_phone(From)
        
        if client:
            client_id = client["id"]
            client_name = client["fields"].get("Name", "Unknown")
            client_pool_num = client["fields"].get("twilio-number")
            log_info(f"Existing Client found (OOS): {client_name}. Checking assigned number...")
        else:
            # Not found? Create one to get an ID
            log_info(f"Client {From} not found (OOS). Creating record...")
            client, _ = create_or_update_client(From)
            client_id = client["id"]
            client_name = client["fields"].get("Name", "Unknown")
            client_pool_num = None
            log_info(f"Created new Client record (OOS): {client_id}")
        
        # 2. Assign Pool Number if missing
        assigned_number = client_pool_num
        is_new_assignment = False
        if not assigned_number:
            log_info(f"Client {From} has no pool number. Fetching from inventory...")
            pool_record = get_ready_pool_number()
            
            if pool_record:
                new_pool_num = pool_record["fields"].get("phone-number")
                pool_record_id = pool_record["id"]
                
                if assign_pool_number_to_client(client_id, pool_record_id, new_pool_num):
                    assigned_number = new_pool_num
                    is_new_assignment = True
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

        # LOOP PREVENTION: If Sitter's handset is the SAME as the number they contacted (To), 
        # they already received the message. Do not forward to avoid infinite loop.
        if sitter_real_phone == To:
            log_info(f"Sitter {sitter_name} handset is same as Entry Point {To} (OOS). Skipping forward to avoid loop.")
            return Response(status_code=status.HTTP_403_FORBIDDEN)

        # Use Record ID for linking
        update_client_linked_sitter(client_id, sitter_recipient["id"])
        
        # 4. Forward Message with Prefix (requested by user)
        # Only prepend prefix if this is the first message (new number assignment)
        if is_new_assignment:
            prefix = f"From {client_name} : "
            if not Body.lstrip().startswith(prefix):
                modified_body = f"{prefix}{Body}"
            else:
                modified_body = Body
        else:
            modified_body = Body
        msg_id = save_message("Manual", assigned_number, sitter_real_phone, modified_body)
        
        try:
            send_sms(from_number=assigned_number, to_number=sitter_real_phone, body=modified_body)
            log_info(f"Forwarded Client -> Sitter (OOS): {modified_body} to {sitter_real_phone}")
            update_message_status(msg_id, "Sent")
            return Response(status_code=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            log_error(f"Failed to forward Client message (OOS)", str(e))
            log_event("FORWARD_ERROR", f"Failed to forward message from {From} (OOS)", str(e))
            increment_client_error_count(client_id)
            return Response(status_code=status.HTTP_403_FORBIDDEN)

    log_error(f"Neither Sender nor Recipient is a known Sitter in OOS: {From} -> {To}")
    return Response(status_code=status.HTTP_404_NOT_FOUND)
