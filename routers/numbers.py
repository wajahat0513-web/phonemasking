"""
Numbers Router
==============
This script manages the assignment and rotation of phone numbers for Sitters.

Key Functionality:
- Assigns new phone numbers to Sitters from the available inventory pool.
- Releases old phone numbers back to the pool (Standby status) for future reuse.
- Updates Airtable records to reflect current assignments.
- Logs number rotation events for auditing.

Endpoints:
- POST /attach-number: Manually triggers a number rotation for a specific Sitter.
"""

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
from typing import Optional
from services.number_pool import get_next_available_number, assign_number_to_sitter, move_old_number_to_standby
from services.twilio_proxy import update_proxy_number
from services.airtable_client import find_sitter_by_twilio_number, find_number_assigned_to_sitter, log_event, inventory_table
from utils.logger import log_info, log_error

router = APIRouter()

class AttachNumberRequest(BaseModel):
    sitter_id: str

@router.post("/attach-number")
async def attach_number(
    request: Optional[AttachNumberRequest] = Body(None),
    sitter_id: Optional[str] = Query(None)
):
    """
    Assigns a new phone number to a Sitter and releases their old one.
    
    This endpoint is used for:
    - New Sitter onboarding.
    - Periodic number rotation for privacy/security.
    - Replacing a compromised or spam-flagged number.
    
    Accepts sitter_id either:
    - In JSON body: {"sitter_id": "rec123"}
    - As query parameter: ?sitter_id=rec123
    
    Args:
        request (Optional[AttachNumberRequest]): Request body containing sitter_id (for JSON requests).
        sitter_id (Optional[str]): Query parameter sitter_id (for query string requests).
        
    Returns:
        dict: Success status and the newly assigned phone number.
    """
    # Support both JSON body and query parameter
    if request and request.sitter_id:
        sitter_id = request.sitter_id
    elif sitter_id:
        pass  # Already set from query parameter
    else:
        raise HTTPException(status_code=422, detail="sitter_id is required in request body or query parameter")
    log_info(f"Attaching new number for sitter {sitter_id}")

    # ---------------------------------------------------------
    # 1. Get Next Available Number
    # ---------------------------------------------------------
    # Fetch an 'Available' number from the Number Inventory table.
    new_number_record = get_next_available_number()
    if not new_number_record:
        # Get diagnostic info to help user
        try:
            from services.airtable_client import inventory_table
            all_records = inventory_table.all(max_records=10)
            if not all_records:
                detail = "Number Inventory table is empty. Please add phone numbers to the 'Number Inventory' table in Airtable."
            else:
                # Check what statuses exist
                status_values = [r.get("fields", {}).get("Status", "N/A") for r in all_records]
                unique_statuses = set(status_values)
                detail = f"No numbers with Status='Available' found. Current statuses in table: {unique_statuses}. Please update records to have Status='Available'."
        except Exception:
            detail = "No available numbers in pool. Please check the Number Inventory table in Airtable and ensure records have Status='Available'."
        
        raise HTTPException(status_code=500, detail=detail)
    
    # Try both field name variations: "PhoneNumber" and "Phone Number"
    new_number = new_number_record["fields"].get("PhoneNumber") or new_number_record["fields"].get("Phone Number")
    if not new_number:
        # Log available fields for debugging
        available_fields = list(new_number_record["fields"].keys())
        log_error(f"Phone number field not found. Available fields: {available_fields}")
        raise HTTPException(status_code=500, detail=f"Phone number field not found in record. Available fields: {available_fields}")
    new_number_id = new_number_record["id"]

    # ---------------------------------------------------------
    # 2. Identify Old Number
    # ---------------------------------------------------------
    # Check if the Sitter already has a number assigned.
    old_number_record = find_number_assigned_to_sitter(sitter_id)
    
    # ---------------------------------------------------------
    # 3. Assign New Number
    # ---------------------------------------------------------
    # Update the new number record in Airtable to 'Assigned' status
    # and link it to the Sitter.
    if not assign_number_to_sitter(sitter_id, new_number_id):
        raise HTTPException(status_code=500, detail="Failed to assign number")

    # ---------------------------------------------------------
    # 4. Release Old Number (if any)
    # ---------------------------------------------------------
    # If the Sitter had a previous number, update its status to 'Standby'
    # so it can be cooled off and reused later.
    if old_number_record:
        old_number_id = old_number_record["id"]
        if not move_old_number_to_standby(old_number_id):
            log_error(f"Failed to release old number {old_number_id} for sitter {sitter_id}")
    
    # ---------------------------------------------------------
    # 5. Log Event
    # ---------------------------------------------------------
    log_event("NUMBER_ROTATION", f"Assigned {new_number} to sitter {sitter_id}")
    
    return {"status": "success", "new_number": new_number}

@router.get("/numbers/debug")
async def debug_numbers():
    """
    Diagnostic endpoint to check Number Inventory table status.
    Helps identify field name issues and available numbers.
    """
    try:
        # Get all records (limited to 20 for debugging)
        all_records = inventory_table.all(max_records=20)
        
        # Get available numbers
        from services.airtable_client import get_available_numbers
        available = get_available_numbers()
        
        # Analyze records
        records_info = []
        status_counts = {}
        field_names = set()
        
        for record in all_records:
            fields = record.get("fields", {})
            field_names.update(fields.keys())
            
            # Count status values
            status = fields.get("Status", "N/A")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Get phone number (try both variations)
            phone = fields.get("PhoneNumber") or fields.get("Phone Number", "N/A")
            
            records_info.append({
                "id": record.get("id"),
                "phone": phone,
                "status": status,
                "assigned_sitter": fields.get("Assigned Sitter", [])
            })
        
        return {
            "total_records": len(all_records),
            "available_count": len(available),
            "status_breakdown": status_counts,
            "field_names_found": sorted(list(field_names)),
            "sample_records": records_info[:5],
            "expected_fields": ["PhoneNumber", "Phone Number", "Status", "Assigned Sitter"]
        }
    except Exception as e:
        log_error(f"Debug endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")
