
import os
import sys
import asyncio
import time
from datetime import datetime, timedelta, timezone

# Add the project root to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.airtable_client import (
    get_assigned_clients,
    find_inventory_record_by_number,
    deallocate_client,
    log_event
)
from utils.logger import log_info, log_error

def check_and_deallocate():
    """
    Checks all assigned clients and deallocates numbers older than 14 days.
    """
    log_info("Running Automated Deallocation Check...")
    
    clients = get_assigned_clients()
    if not clients:
        log_info("No assigned clients found. Skipping check.")
        return

    now = datetime.now(timezone.utc)
    expiration_threshold = timedelta(days=14)
    deallocated_count = 0

    for client in clients:
        fields = client.get("fields", {})
        client_id = client.get("id")
        client_name = fields.get("Name", "Unknown")
        pool_number = fields.get("twilio-number")
        last_active_str = fields.get("Last Active")

        if not last_active_str:
            # "dont cater to empty values" as per user request
            continue

        try:
            # Parse ISO timestamp. PyAirtable typically returns UTC.
            # Replace 'Z' with +00:00 for fromisoformat compatibility in some python versions if needed
            dt_str = last_active_str.replace("Z", "+00:00")
            last_active_dt = datetime.fromisoformat(dt_str)
            
            # Ensure it's timezone-aware if the ISO string didn't have offset
            if last_active_dt.tzinfo is None:
                last_active_dt = last_active_dt.replace(tzinfo=timezone.utc)

            age = now - last_active_dt

            if age > expiration_threshold:
                log_info(f"Client {client_name} ({client_id}) exceeds 14 days. Expiration age: {age.days} days.")
                
                # Find the inventory record for the number to release it
                inventory_record = find_inventory_record_by_number(pool_number)
                
                if inventory_record:
                    if deallocate_client(client_id, inventory_record["id"]):
                        log_info(f"Successfully deallocated {pool_number} from {client_name}")
                        log_event("NUMBER_DEALLOCATED", f"Auto-deallocated {pool_number} from {client_name}", f"Age: {age.days} days")
                        deallocated_count += 1
                    else:
                        log_error(f"Failed to deallocate {pool_number} from {client_name}")
                else:
                    log_error(f"Could not find inventory record for {pool_number}. Manual cleanup may be required.")
        
        except Exception as e:
            log_error(f"Error processing deallocation for client {client_id}", str(e))

    log_info(f"Check complete. Deallocated {deallocated_count} numbers.")

async def async_run_worker():
    """ Runs the check every hour asynchronously. """
    log_info("Deallocation Background Worker Started. Checking every hour.")
    while True:
        try:
            check_and_deallocate()
        except Exception as e:
            log_error("Deallocation Worker encountered an error", str(e))
        
        # Sleep for 1 hour
        await asyncio.sleep(3600)

def run_worker():
    """ Runs the check every hour (Synchronous version). """
    log_info("Deallocation Worker Started (Sync). Checking every hour.")
    while True:
        try:
            check_and_deallocate()
        except Exception as e:
            log_error("Deallocation Worker encountered a fatal error", str(e))
        
        # Sleep for 1 hour
        log_info("Sleeping for 1 hour...")
        time.sleep(3600)

if __name__ == "__main__":
    # If run with --once, it just runs one check and exits (good for cron)
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        check_and_deallocate()
    else:
        run_worker()
