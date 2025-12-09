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
    audit_table.create({
        "Event": event_type,
        "Description": description,
        "Details": details,
        "Timestamp": datetime.utcnow().isoformat()
    })

def get_available_numbers():
    """
    Retrieves all phone numbers from inventory that are marked as 'Available'.
    
    Returns:
        list: A list of Airtable records for available numbers.
    """
    formula = "{Status} = 'Available'"
    return inventory_table.all(formula=formula)

def find_number_assigned_to_sitter(sitter_id: str):
    """
    Finds the number inventory record currently assigned to a specific Sitter.
    
    Args:
        sitter_id (str): The Sitter's Airtable Record ID.
        
    Returns:
        dict: The inventory record, or None if not found.
    """
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
