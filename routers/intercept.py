"""
Intercept Router (Manual Proxy)
===============================
This script handles the manual interception and routing of messages, bypassing Twilio Proxy Sessions.

Key Functionality:
- INBOUND (Client -> Sitter):
  1. Intercepts message to Sitter's Number.
  2. Checks/Assigns a 'Pool Number' to the Client from Inventory.
  3. Links Sitter to Client in Airtable.
  4. Manually forwards SMS from Pool Number to Sitter with [Client Name] prefix.
  5. Returns 403 to Twilio to block default routing.

- OUTBOUND (Sitter -> Client):
  1. Intercepts message from Sitter.
  2. Identifies Client based on the Pool Number texted (To).
  3. Manually forwards SMS from Pool Number to Client's Real Number.
"""

from fastapi import APIRouter, Request, Response, status
from services.airtable_client import (
    find_sitter_by_twilio_number,
    find_client_by_phone,
    create_or_update_client,
    get_ready_pool_number,
    assign_pool_number_to_client,
    update_client_linked_sitter,
    find_client_by_twilio_number,
    increment_client_error_count,
    save_message,
    update_message_status,
    log_event
)
from services.twilio_proxy import send_sms
from utils.logger import log_info, log_error
from utils.request_parser import parse_incoming_payload

router = APIRouter()

@router.post("/intercept")
async def intercept(request: Request):
    payload = await parse_incoming_payload(request, required_fields=[])
    
    From = payload.get("From", "").strip()
    To = payload.get("To", "").strip()
    Body = payload.get("Body", "")
    
    # Normalize
    if From and not From.startswith("+"): From = f"+{From}"
    if To and not To.startswith("+"): To = f"+{To}"

    log_info(f"Intercept Triggered: {From} -> {To} | Body: {Body}")

    # ==============================================================================
    # 1. CHECK IF SITTER IS SENDER (Outbound: Sitter -> Client)
    # ==============================================================================
    # If the sender is a Sitter, they are replying to a Pool Number (To).
    # We need to find which Client is assigned that Pool Number.
    
    # Check if 'From' matches a known Sitter
    # (Checking if sender is a Sitter requires looking up by their real phone)
    sitter_sender = find_sitter_by_twilio_number(From)
    
    if sitter_sender:
        log_info(f"Sender is Sitter {sitter_sender['fields'].get('Full Name')}. Routing to Client...")
        
        # The 'To' number is the Pool Number they texted.
        # Find which client has this pool number assigned.
        client_recipient = find_client_by_twilio_number(To)
        
        if client_recipient:
            client_real_phone = client_recipient["fields"].get("Phone Number")
            log_info(f"Found linked Client: {client_recipient['fields'].get('Name')} ({client_real_phone})")
            
            try:
                # Save message for audit/retry (Outbound Sitter->Client)
                msg_id = save_message("Manual", To, client_real_phone, Body)
                
                # Forward: From Pool Number (To) -> Client Real Phone
                send_sms(from_number=To, to_number=client_real_phone, body=Body)
                
                update_message_status(msg_id, "Sent")
                log_info("Successfully forwarded Sitter -> Client")
                return Response(status_code=status.HTTP_200_OK)
            except Exception as e:
                log_error("Failed to forward Sitter reply", str(e))
                # Leave status as Pending for retry? Or Sitter needs immediate feedback?
                # For now let worker retry if we leave it Pending (default save status)
                return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            log_error(f"No Client found assigned to Pool Number {To}. Sitter reply orphan.")
            # Optional: Reply to Sitter saying "Orphaned session"
            return Response(status_code=status.HTTP_200_OK)

    # ==============================================================================
    # 2. CHECK IF RECIPIENT IS SITTER (Inbound: Client -> Sitter)
    # ==============================================================================
    # The 'To' number is the Sitter's real Twilio number (or Reserved Number).
    
    sitter_recipient = find_sitter_by_twilio_number(To)
    
    if sitter_recipient:
        log_info(f"Recipient is Sitter {sitter_recipient['fields'].get('Full Name')}. Processing Client message...")
        
        # 2a. Find or Create Client
        client, _ = create_or_update_client(From)
        client_id = client["id"]
        client_name = client["fields"].get("Name", "Unknown")
        client_pool_num = client["fields"].get("twilio-number")
        
        # 2b. Assign Pool Number if missing
        assigned_number = client_pool_num
        if not assigned_number:
            log_info(f"Client {From} has no pool number. Fetching from inventory...")
            pool_record = get_ready_pool_number()
            
            if pool_record:
                new_pool_num = pool_record["fields"].get("PhoneNumber") or pool_record["fields"].get("Phone Number")
                pool_record_id = pool_record["id"]
                
                if assign_pool_number_to_client(client_id, pool_record_id, new_pool_num):
                    assigned_number = new_pool_num
                    log_info(f"Assigned new Pool Number {assigned_number} to Client {client_id}")
                else:
                    log_error("Failed to assign available pool number.")
            else:
                log_error("CRITICAL: No Ready pool numbers available in Inventory!")
                # Fallback? We can't forward without a masked number.
                # Increment error count so worker might retry later if pool fills up?
                increment_client_error_count(client_id)
                return Response(status_code=status.HTTP_403_FORBIDDEN)
        
        # 2c. Link Sitter
        sitter_name = sitter_recipient["fields"].get("Full Name", "Unknown Sitter")
        sitter_real_phone = sitter_recipient["fields"].get("Phone Number")
        
        if not sitter_real_phone:
            log_error(f"Sitter {sitter_name} has no real Phone Number for forwarding.")
            return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        update_client_linked_sitter(client_id, sitter_name)
        
        # 2d. Forward Message
        modified_body = f"[{client_name}]: {Body}"
        
        # Save message for audit/retry (Inbound Client->Sitter)
        # We save the *Forwarded* version so retry worker just executes it blindly
        msg_id = save_message("Manual", assigned_number, sitter_real_phone, modified_body)
        
        try:
            # Send FROM Assigned Pool Number TO Sitter's REAL Number
            send_sms(from_number=assigned_number, to_number=sitter_real_phone, body=modified_body)
            log_info(f"Forwarded Client -> Sitter: {modified_body} to {sitter_real_phone}")
            
            update_message_status(msg_id, "Sent")
            
            # Return 403 to stop Twilio from processing further
            return Response(status_code=status.HTTP_403_FORBIDDEN)
            
        except Exception as e:
            log_error(f"Failed to forward Client message", str(e))
            increment_client_error_count(client_id)
            # Message Status stays 'Pending' (from save_message default), so Worker will retry
            return Response(status_code=status.HTTP_403_FORBIDDEN)

    # Fallback if neither Sitter nor Client logic matched
    log_info("Intercept: Message did not match Sitter routing rules.")
    return {"status": "ignored"}
