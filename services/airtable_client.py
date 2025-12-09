"""
Airtable Client Service
=======================
This script acts as the Data Access Layer (DAL) for the application, handling all interactions with Airtable.

Key Functionality:
- Connects to the Airtable API using credentials from the configuration.
- Provides helper functions to CRUD (Create, Read, Update, Delete) records in various tables:
    - Sitters: Manage sitter information.
    - Clients: Manage client information and session links.
    - Messages: Log all communication history.
    - Number Inventory: Manage the pool of proxy phone numbers.
    - Audit Log: Record system events for debugging and compliance.
"""

from pyairtable import Api
from config import settings
from datetime import datetime

api = Api(settings.AIRTABLE_API_KEY)
base = api.base(settings.AIRTABLE_BASE_ID)

# Table References
sitters_table = base.table(settings.AIRTABLE_SITTERS_TABLE)
clients_table = base.table(settings.AIRTABLE_CLIENTS_TABLE)
messages_table = base.table(settings.AIRTABLE_MESSAGES_TABLE)
inventory_table = base.table(settings.AIRTABLE_NUMBER_INVENTORY_TABLE)
audit_table = base.table(settings.AIRTABLE_AUDIT_LOG_TABLE)

def find_sitter_by_twilio_number(twilio_number: str):
    """
    Finds a Sitter record that is assigned a specific Twilio proxy number.
    
    Args:
        twilio_number (str): The proxy phone number (e.g., +1555...).
        
    Returns:
        dict: The Airtable record for the sitter, or None if not found.
    """
    formula = f"{{Twilio Number}} = '{twilio_number}'"
    records = sitters_table.all(formula=formula)
    return records[0] if records else None

def find_sitter_by_id(sitter_id: str):
    """
    Retrieves a Sitter record by its Airtable Record ID.
    
    Args:
        sitter_id (str): The unique Record ID (e.g., rec...).
        
    Returns:
        dict: The Airtable record, or None if not found/error.
    """
    try:
        return sitters_table.get(sitter_id)
    except Exception:
        return None

def find_client_by_phone(phone_number: str):
    """
    Finds a Client record by their real phone number.
    
    Args:
        phone_number (str): The client's real phone number.
        
    Returns:
        dict: The Airtable record for the client, or None if not found.
    """
    formula = f"{{Phone Number}} = '{phone_number}'"
    records = clients_table.all(formula=formula)
    return records[0] if records else None

def create_client(phone_number: str, name: str = "Unknown"):
    """
    Creates a new Client record in Airtable.
    
    Args:
        phone_number (str): The client's real phone number.
        name (str): Optional name for the client.
        
    Returns:
        dict: The created Airtable record.
    """
    return clients_table.create({
        "Phone Number": phone_number,
        "Name": name,
        "Created At": datetime.utcnow().isoformat()
    })

def update_client_session(client_id: str, session_sid: str):
    """
    Updates a Client's record with the current active Session SID and timestamp.
    
    Args:
        client_id (str): The Airtable Record ID of the client.
        session_sid (str): The Twilio Proxy Session SID.
    """
    clients_table.update(client_id, {
        "Session SID": session_sid,
        "Last Active": datetime.utcnow().isoformat()
    })

def save_message(session_sid: str, from_number: str, to_number: str, body: str):
    """
    Logs a message to the Messages table.
    
    Args:
        session_sid (str): The ID of the session the message belongs to.
        from_number (str): The sender's phone number.
        to_number (str): The recipient's phone number.
        body (str): The content of the message.
    """
    messages_table.create({
        "Session SID": session_sid,
        "From": from_number,
        "To": to_number,
        "Body": body,
        "Timestamp": datetime.utcnow().isoformat()
    })

def log_event(event_type: str, description: str, details: str = ""):
    """
    Logs a system event to the Audit Log table.
    
    Args:
        event_type (str): Category of the event (e.g., SESSION_CREATED).
        description (str): Human-readable description of what happened.
        details (str): Additional technical details or JSON dump.
    """
    # Field name in Airtable API is "Event" (UI shows "A Event" but API uses "Event")
    # The error suggests Railway may have old code using "Event Type" - this is the correct field name
    audit_table.create({
        "Event": event_type,
        "Description": description,
        "Details": details,
        "Timestamp": datetime.utcnow().isoformat()
    })

def get_available_numbers():
    """
    Retrieves all phone numbers from inventory that are marked as 'Available'.
    Tries multiple variations of the Status field and value to handle different naming conventions.
    
    Returns:
        list: A list of Airtable records for available numbers.
    """
    try:
        # Try exact match first
        formula = "{Status} = 'Available'"
        numbers = inventory_table.all(formula=formula)
        # Filter out any records that don't actually have Status field (safety check)
        numbers = [n for n in numbers if "Status" in n.get("fields", {})]
        
        # If no results, try case-insensitive
        if not numbers:
            formula = "LOWER({Status}) = 'available'"
            numbers = inventory_table.all(formula=formula)
            # Filter out any records that don't actually have Status field
            numbers = [n for n in numbers if "Status" in n.get("fields", {})]
        
        # If still no results, try common alternative status values
        # Some users might use "Standby", "Unassigned", "Free", etc.
        if not numbers:
            alternative_statuses = ["Standby", "standby", "Unassigned", "unassigned", "Free", "free", "Ready", "ready"]
            for alt_status in alternative_statuses:
                formula = f"{{Status}} = '{alt_status}'"
                numbers = inventory_table.all(formula=formula)
                if numbers:
                    # Filter out records that don't have Status field (shouldn't happen, but safety check)
                    numbers = [n for n in numbers if "Status" in n.get("fields", {})]
                    if numbers:
                        from utils.logger import log_info
                        log_info(f"Found {len(numbers)} number(s) with Status='{alt_status}' (using as available)")
                        break
        
        # Log diagnostic info if still no results
        if not numbers:
            # Get all records to diagnose
            all_records = inventory_table.all(max_records=50)
            from utils.logger import log_error
            
            if not all_records:
                log_error("Number Inventory table is empty - no records found")
                return []
            
            # Analyze what we have - check multiple records to find Status field
            status_field_name = None
            status_values = []
            all_field_names = set()
            
            # Collect all field names from all records
            for record in all_records:
                fields = record.get("fields", {})
                all_field_names.update(fields.keys())
            
            # Try to find Status field (case-insensitive) from all field names
            for field_name in all_field_names:
                if field_name.lower() == "status":
                    status_field_name = field_name
                    # Get status values from all records that have this field
                    status_values = [r.get("fields", {}).get(field_name) for r in all_records if field_name in r.get("fields", {})]
                    status_values = [s for s in status_values if s is not None]  # Filter out None values
                    break
            
            if not status_field_name:
                # Check if any records have Status field at all
                records_with_status = [r for r in all_records if any(k.lower() == "status" for k in r.get("fields", {}).keys())]
                if records_with_status:
                    # Some records have Status, some don't
                    log_error(f"Status field exists but not all records have it. Records with Status: {len(records_with_status)}/{len(all_records)}")
                    # Get status values from records that have it
                    for record in records_with_status:
                        for field_name in record.get("fields", {}).keys():
                            if field_name.lower() == "status":
                                status_values.append(record.get("fields", {}).get(field_name))
                                break
                    unique_statuses = set(status_values)
                    log_error(f"Status values found: {unique_statuses}")
                else:
                    log_error(f"Status field not found in any records. Available fields across all records: {sorted(all_field_names)}")
            else:
                unique_statuses = set(status_values)
                log_error(f"Status field found: '{status_field_name}'. Values in table: {unique_statuses}")
                log_error(f"Total records: {len(all_records)}, Records with Status field: {len(status_values)}")
                
                # If we found records but none are "Available", suggest what to check
                available_variants = ["Available", "available", "Ready", "ready", "Standby", "standby"]
                has_available = any(variant in unique_statuses for variant in available_variants)
                
                if not has_available:
                    log_error(f"⚠️ No records with Status='Available' (or Ready/Standby). Current statuses: {unique_statuses}")
                    log_error(f"💡 Tip: Update at least one record to have Status='Available' or 'Ready' to make it assignable")
        
        return numbers
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Error fetching available numbers: {str(e)}")
        import traceback
        log_error(f"Traceback: {traceback.format_exc()}")
        raise

def find_number_assigned_to_sitter(sitter_id: str):
    """
    Finds the number inventory record currently assigned to a specific Sitter.
    
    Args:
        sitter_id (str): The Sitter's Airtable Record ID.
        
    Returns:
        dict: The inventory record, or None if not found.
    """
    # Trim whitespace from sitter_id to prevent invalid record ID errors
    sitter_id = sitter_id.strip() if sitter_id else sitter_id
    
    if not sitter_id:
        return None
    
    formula = f"FIND('{sitter_id}', {{Assigned Sitter}})"
    records = inventory_table.all(formula=formula)
    return records[0] if records else None

def reserve_number(record_id: str, sitter_id: str):
    """
    Updates a number inventory record to mark it as 'Assigned' to a Sitter.
    
    Args:
        record_id (str): The Inventory Record ID.
        sitter_id (str): The Sitter's Record ID to link.
    """
    # Trim whitespace from sitter_id to prevent invalid record ID errors
    sitter_id = sitter_id.strip() if sitter_id else sitter_id
    
    if not sitter_id:
        raise ValueError("sitter_id cannot be empty")
    
    inventory_table.update(record_id, {
        "Status": "Assigned",
        "Assigned Sitter": [sitter_id]
    })

def release_number(record_id: str):
    """
    Updates a number inventory record to mark it as 'Standby' (released).
    
    Args:
        record_id (str): The Inventory Record ID.
    """
    inventory_table.update(record_id, {
        "Status": "Standby",
        "Assigned Sitter": []
    })

def find_active_sessions_for_sitter(sitter_id: str):
    """
    Finds all active client sessions linked to a specific Sitter.
    
    Args:
        sitter_id (str): The Sitter's Record ID.
        
    Returns:
        list: A list of Client records that have an active session with this sitter.
    """
    formula = f"AND(FIND('{sitter_id}', {{Sitter}}), NOT({{Session SID}} = ''))"
    return clients_table.all(formula=formula)
