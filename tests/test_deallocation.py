
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# Add the project root to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.deallocate_worker import check_and_deallocate

@patch('services.deallocate_worker.get_assigned_clients')
@patch('services.deallocate_worker.find_inventory_record_by_number')
@patch('services.deallocate_worker.deallocate_client')
@patch('services.deallocate_worker.log_event')
def test_deallocation_logic(mock_log, mock_deallocate, mock_find_inv, mock_get_clients):
    print("Testing Deallocation Logic...")

    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(days=15)).isoformat()
    active_time = (now - timedelta(days=5)).isoformat()

    # Mock clients: one expired, one active, one with no date
    mock_get_clients.return_value = [
        {
            "id": "recExpired",
            "fields": {"Name": "Expired User", "twilio-number": "+1expired", "Last Active": expired_time}
        },
        {
            "id": "recActive",
            "fields": {"Name": "Active User", "twilio-number": "+1active", "Last Active": active_time}
        },
        {
            "id": "recNoDate",
            "fields": {"Name": "No Date User", "twilio-number": "+1nodate"}
        }
    ]

    # Mock inventory record finding
    mock_find_inv.side_effect = lambda num: {"id": "recInv_expired"} if num == "+1expired" else None
    
    # Mock deallocation success
    mock_deallocate.return_value = True

    # Run the check
    check_and_deallocate()

    # Assertions
    # 1. Should have called deallocate for exactly ONE client (the expired one)
    assert mock_deallocate.call_count == 1
    mock_deallocate.assert_called_once_with("recExpired", "recInv_expired")
    
    # 2. Should have logged the event
    assert mock_log.call_count == 1
    
    print("SUCCESS: Deallocation logic correctly processed expired vs active records.")

if __name__ == "__main__":
    test_deallocation_logic()
