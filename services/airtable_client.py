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
    Finds a Sitter record checking multiple possible phone columns and formats.
    """
    if not twilio_number:
        return None
        
    # Clean input: keep only digits
    clean_num = "".join(filter(str.isdigit, twilio_number))
    # Get 10-digit version if it's 11 digits starting with 1
    ten_digit = clean_num[-10:] if len(clean_num) >= 10 else clean_num
    
    # Check Twilio Number and Phone Number
    # We use SEARCH on the ten-digit version to be most flexible
    formula = f"OR(" \
              f"SEARCH('{ten_digit}', {{Twilio Number}}), " \
              f"SEARCH('{ten_digit}', {{Phone Number}}), " \
              f"{{Twilio Number}} = '{twilio_number}', " \
              f"{{Phone Number}} = '{twilio_number}'" \
              f")"
    
    try:
        records = sitters_table.all(formula=formula)
        return records[0] if records else None
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Error in find_sitter_by_twilio_number: {str(e)}")
        return None

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
    """
    if not phone_number:
        return None
        
    clean_num = "".join(filter(str.isdigit, phone_number))
    ten_digit = clean_num[-10:] if len(clean_num) >= 10 else clean_num

    # Check primary Phone Number field
    formula = f"OR(" \
              f"SEARCH('{ten_digit}', {{Phone Number}}), " \
              f"{{Phone Number}} = '{phone_number}'" \
              f")"
    
    try:
        records = clients_table.all(formula=formula)
        return records[0] if records else None
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Error in find_client_by_phone: {str(e)}")
        return None

def create_or_update_client(phone_number: str, name: str = "Unknown", **kwargs):
    """
    Find or create a Client record (upsert logic).
    
    Prevents duplicates when client texts before Zap 1 syncs.
    
    Args:
        phone_number (str): E.164 formatted phone number
        name (str): Client name
        **kwargs: Additional fields to update (email, address, etc.)
        
    Returns:
        tuple: (record dict, was_created bool)
    """
    # Search for existing client by phone number
    existing = find_client_by_phone(phone_number)
    
    if existing:
        # Update existing record
        update_fields = {"Name": name, "Last Active": datetime.utcnow().isoformat()}
        update_fields.update(kwargs)
        
        updated = clients_table.update(existing["id"], update_fields)
        from utils.logger import log_info
        log_info(f"Updated existing client: {phone_number}")
        return (updated, False)
    else:
        # Create new record
        create_fields = {
            "Phone Number": phone_number,
            "Name": name,
            "Created At": datetime.utcnow().isoformat()
        }
        create_fields.update(kwargs)
        
        created = clients_table.create(create_fields)
        from utils.logger import log_info
        log_info(f"Created new client: {phone_number}")
        return (created, True)

def create_client(phone_number: str, name: str = "Unknown"):
    """
    Creates a new Client record in Airtable.
    
    DEPRECATED: Use create_or_update_client() instead for better deduplication.
    
    Args:
        phone_number (str): The client's real phone number.
        name (str): Optional name for the client.
        
    Returns:
        dict: The created Airtable record.
    """
    record, _ = create_or_update_client(phone_number, name)
    return record

def update_client_session(client_id: str, session_sid: str, sitter_id: str = None):
    """
    Updates a Client's record with the active Session SID, timestamp, and Sitter link.
    """
    update_fields = {
        "Session SID": session_sid,
        "Last Active": datetime.utcnow().isoformat()
    }
    
    if sitter_id:
        # Airtable linked fields expect an array of record IDs
        update_fields["Linked Sitter"] = [sitter_id]
        
    clients_table.update(client_id, update_fields)

def save_message(session_sid: str, from_number: str, to_number: str, body: str, intercepted: bool = False):
    """
    Logs a message to the Messages table.
    
    Args:
        session_sid (str): The ID of the session the message belongs to.
        from_number (str): The sender's phone number.
        to_number (str): The recipient's phone number.
        body (str): The content of the message.
    """
    record = messages_table.create({
        "Session SID": session_sid,
        "From": from_number,
        "To": to_number,
        "Body": body,
        "Timestamp": datetime.utcnow().isoformat(),
        "Status": "Pending"
    })
    return record.get("id")

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
    Retrieves all unassigned phone numbers from inventory.
    Status field checking removed - now only checks if number is assigned to a sitter.
    
    Returns:
        list: A list of Airtable records for unassigned numbers in inventory.
    """
    try:
        # Get all records from inventory (no Status filter)
        all_numbers = inventory_table.all()
        
        # Filter to only unassigned numbers (no Assigned Sitter)
        # and ensure they have a phone number field
        numbers = []
        for record in all_numbers:
            fields = record.get("fields", {})
            phone = fields.get("PhoneNumber") or fields.get("Phone Number")
            assigned_sitter = fields.get("Assigned Sitter", [])
            
            # Only include records that have a phone number AND are not assigned
            if phone and not assigned_sitter:
                numbers.append(record)
        
        from utils.logger import log_info
        if numbers:
            log_info(f"Found {len(numbers)} unassigned number(s) in inventory")
        else:
            log_info("No unassigned numbers found in inventory table")
        
        return numbers
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Error fetching numbers from inventory: {str(e)}")
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
    Updates a number inventory record to link it to a Sitter.
    Status field update removed - only updates Assigned Sitter field.
    
    Args:
        record_id (str): The Inventory Record ID.
        sitter_id (str): The Sitter's Record ID to link.
    """
    # Trim whitespace from sitter_id to prevent invalid record ID errors
    sitter_id = sitter_id.strip() if sitter_id else sitter_id
    
    if not sitter_id:
        raise ValueError("sitter_id cannot be empty")
    
    # Only update Assigned Sitter field, don't touch Status
    inventory_table.update(record_id, {
        "Assigned Sitter": [sitter_id]
    })

def release_number(record_id: str):
    """
    Releases a number from a Sitter by clearing the Assigned Sitter field.
    Status field update removed - only clears Assigned Sitter.
    
    Args:
        record_id (str): The Inventory Record ID.
    """
    # Only clear Assigned Sitter field, don't touch Status
    inventory_table.update(record_id, {
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
    formula = f"AND(FIND('{sitter_id}', {{Linked Sitter}}), NOT({{Session SID}} = ''))"
    return clients_table.all(formula=formula)

def get_pending_messages(older_than_minutes: int = 5):
    """
    Retrieves messages that have been in 'Pending' status for a specified duration.
    """
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(minutes=older_than_minutes)
    
    # Formula filters for Status='Pending' AND Timestamp before cutoff
    formula = f"AND({{Status}} = 'Pending', IS_BEFORE({{Timestamp}}, '{cutoff.isoformat()}'))"
    return messages_table.all(formula=formula)

def update_message_status(message_id: str, status: str):
    """
    Updates the delivery status of a message.
    """
    try:
        messages_table.update(message_id, {"Status": status})
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Error updating message status: {str(e)}")

def get_ready_pool_number():
    """
    Fetches a number from inventory with Lifecycle='pool' and Status='Ready'.
    """
    try:
        # Formula: AND(Lifecycle='Pool', Status='Ready') -- Capitalized 'Pool' based on user data
        formula = "AND({Lifecycle}='Pool', {Status}='Ready')"
        records = inventory_table.all(formula=formula)
        return records[0] if records else None
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Error fetching ready pool number: {str(e)}")
        return None

def assign_pool_number_to_client(client_id: str, number_record_id: str, number_value: str):
    """
    Assigns a pool number to a client and updates the inventory status.
    """
    try:
        # 1. Update Client with the assigned number (Correct column name: "Twilio Number")
        clients_table.update(client_id, {"Twilio Number": number_value})
        
        # 2. Update Inventory to mark as Assigned (Status='Assigned')
        inventory_table.update(number_record_id, {"Status": "Assigned"})
        return True
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Failed to assign pool number: {str(e)}")
        return False

def update_client_linked_sitter(client_id: str, sitter_record_id: str):
    """
    Updates the Linked Sitter field for a client.
    Note: Link fields require an ARRAY of Record IDs.
    """
    try:
        clients_table.update(client_id, {"Linked Sitter": [sitter_record_id]})
        return True
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Failed to link sitter: {str(e)}")
        return False

def increment_client_error_count(client_id: str):
    """
    Increments the Twilio-Error-Count for a client.
    Handles 'Twilio-Error-Count' as a String/Text field to avoid 422 errors.
    """
    try:
        client = clients_table.get(client_id)
        # Get current value, default to "0" (as string) or 0 (if int logic was used locally)
        raw_val = client["fields"].get("Twilio-Error-Count", "0")
        
        # Safely convert to int
        try:
            current = int(str(raw_val))
        except ValueError:
            current = 0
            
        new_count = current + 1
        
        # Update as STRING because user confirmed it is a Single Line Text column
        clients_table.update(client_id, {"Twilio-Error-Count": str(new_count)})
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Failed to increment error count: {str(e)}")

def find_client_by_twilio_number(twilio_number: str):
    """
    Finds a Client record by their assigned 'twilio-number'. (Used for Sitter -> Client routing)
    """
    if not twilio_number:
        return None
    
    # Formula: {Twilio Number} = 'number'
    formula = f"{{Twilio Number}} = '{twilio_number}'"
    try:
        records = clients_table.all(formula=formula)
        return records[0] if records else None
    except Exception as e:
        from utils.logger import log_error
        log_error(f"Error finding client by pool number: {str(e)}")
        return None
