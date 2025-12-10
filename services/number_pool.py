"""
Number Pool Service
===================
This script manages the lifecycle and assignment of proxy phone numbers.

Key Functionality:
- Retrieves available numbers from the inventory.
- Assigns numbers to Sitters.
- Releases numbers back to the pool (Standby) when they are no longer needed.
- (Future) Can implement logic to refresh pool status or handle number purchasing.

This service ensures that phone numbers are efficiently rotated and reused.
"""

from services.airtable_client import get_available_numbers, reserve_number, release_number, log_event
from utils.logger import log_info, log_error

def get_next_available_number():
    """
    Fetches the first available number from the inventory.
    
    Returns:
        dict: The Airtable record for the available number, or None if the pool is empty.
    """
    numbers = get_available_numbers()
    if not numbers:
        log_error("No available numbers in pool")
        return None
    return numbers[0]

def assign_number_to_sitter(sitter_id: str, number_record_id: str, raise_on_error: bool = False):
    """
    Links a specific number from the inventory to a Sitter.
    
    Args:
        sitter_id (str): The Sitter's Airtable Record ID.
        number_record_id (str): The Inventory Record ID of the number to assign.
        
    Returns:
        bool: True if successful, False otherwise (or raises if raise_on_error=True).
    """
    try:
        reserve_number(number_record_id, sitter_id)
        log_info(f"Assigned number {number_record_id} to sitter {sitter_id}")
        return True
    except Exception as e:
        log_error(f"Failed to assign number {number_record_id} to sitter {sitter_id}", str(e))
        if raise_on_error:
            raise
        return False

def move_old_number_to_standby(number_record_id: str):
    """
    Releases a number from a Sitter, making it 'Standby' for future use.
    
    Args:
        number_record_id (str): The Inventory Record ID to release.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        release_number(number_record_id)
        log_info(f"Released number {number_record_id} to standby")
        return True
    except Exception as e:
        log_error(f"Failed to release number {number_record_id}", str(e))
        return False

def refresh_pool_status():
    """
    Placeholder for future logic to audit or refresh the number pool.
    e.g., Checking Twilio for new numbers or syncing status.
    """
    pass
