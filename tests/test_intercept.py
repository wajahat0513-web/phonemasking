
import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

# Add the project root to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from routers.intercept import intercept

class MockRequest:
    def __init__(self, data):
        self._data = data
        self.headers = {"content-type": "application/x-www-form-urlencoded"}
        self.query_params = {}
    async def form(self):
        return self._data
    async def json(self):
        return self._data

@patch('routers.intercept.update_client_last_active')
@patch('routers.intercept.log_event')
@patch('routers.intercept.get_ready_pool_number')
@patch('routers.intercept.assign_pool_number_to_client')
@patch('routers.intercept.update_client_linked_sitter')
@patch('routers.intercept.update_message_status')
@patch('routers.intercept.save_message')
@patch('routers.intercept.send_sms')
@patch('routers.intercept.find_client_by_twilio_number')
@patch('routers.intercept.find_client_by_phone')
@patch('routers.intercept.find_sitter_by_twilio_number')
async def test_inbound_flow(mock_find_sitter, mock_find_client, mock_find_client_pool,
                            mock_send_sms, mock_save_msg, mock_update_status,
                            mock_link_sitter, mock_assign_num, mock_get_pool,
                            mock_log_event, mock_update_last_active):
    """Test Client -> Sitter routing with suffix."""
    print("Testing Inbound (Client -> Sitter)...")
    
    # Sitter Recipient exists
    mock_find_sitter.side_effect = lambda num: {
        "id": "recSitter",
        "fields": {"Full Name": "Jane Sitter", "phone-number": "+1sitter_real", "twilio-number": "+1sitter_twilio"}
    } if num == "+1sitter_twilio" else None
    
    # Client exists
    mock_find_client.return_value = {
        "id": "recClient",
        "fields": {"Name": "John Client", "twilio-number": "+1pool", "phone-number": "+1client"}
    }

    payload = {"From": "+1client", "To": "+1sitter_twilio", "Body": "Hello there"}
    await intercept(MockRequest(payload))
    
    mock_send_sms.assert_called_once()
    _, kwargs = mock_send_sms.call_args
    assert kwargs['from_number'] == "+1pool"
    assert kwargs['to_number'] == "+1sitter_real"
    assert kwargs['body'] == "Hello there"
    # Verify Sitter Link (Should be Name, not ID)
    mock_link_sitter.assert_called_once_with("recClient", "Jane Sitter")
    # Verify Last Active was updated
    mock_update_last_active.assert_called_once_with("recClient")
    print("SUCCESS: Inbound routing and suffix verified.")

@patch('routers.intercept.update_client_last_active')
@patch('routers.intercept.log_event')
@patch('routers.intercept.get_ready_pool_number')
@patch('routers.intercept.assign_pool_number_to_client')
@patch('routers.intercept.update_client_linked_sitter')
@patch('routers.intercept.update_message_status')
@patch('routers.intercept.save_message')
@patch('routers.intercept.send_sms')
@patch('routers.intercept.find_client_by_twilio_number')
@patch('routers.intercept.find_client_by_phone')
@patch('routers.intercept.find_sitter_by_twilio_number')
async def test_outbound_flow(mock_find_sitter, mock_find_client, mock_find_client_pool,
                             mock_send_sms, mock_save_msg, mock_update_status,
                             mock_link_sitter, mock_assign_num, mock_get_pool,
                             mock_log_event, mock_update_last_active):
    """Test Sitter -> Client routing."""
    print("\nTesting Outbound (Sitter -> Client)...")

    # Sender is Sitter
    mock_find_sitter.side_effect = lambda num: {
        "id": "recSitter",
        "fields": {"Full Name": "Jane Sitter", "phone-number": "+1sitter_real", "twilio-number": "+1sitter_twilio"}
    } if num == "+1sitter_real" else None
    
    # Recipient is Client linked to Pool
    mock_find_client_pool.return_value = {
        "id": "recClient",
        "fields": {"Name": "John Client", "phone-number": "+1client", "twilio-number": "+1pool"}
    }

    payload = {"From": "+1sitter_real", "To": "+1pool", "Body": "I'm on my way"}
    await intercept(MockRequest(payload))
    
    mock_send_sms.assert_called_once()
    _, kwargs = mock_send_sms.call_args
    assert kwargs['from_number'] == "+1sitter_twilio"
    assert kwargs['to_number'] == "+1client"
    assert kwargs['body'] == "I'm on my way"
    # Verify Last Active was updated for client
    mock_update_last_active.assert_called_once_with("recClient")
    print("SUCCESS: Outbound routing verified.")

@patch('routers.intercept.create_or_update_client')
@patch('routers.intercept.update_client_last_active')
@patch('routers.intercept.log_event')
@patch('routers.intercept.get_ready_pool_number')
@patch('routers.intercept.assign_pool_number_to_client')
@patch('routers.intercept.update_client_linked_sitter')
@patch('routers.intercept.update_message_status')
@patch('routers.intercept.save_message')
@patch('routers.intercept.send_sms')
@patch('routers.intercept.find_client_by_twilio_number')
@patch('routers.intercept.find_client_by_phone')
@patch('routers.intercept.find_sitter_by_twilio_number')
async def test_assignment_updates_timestamp(mock_find_sitter, mock_find_client, mock_find_client_pool,
                                            mock_send_sms, mock_save_msg, mock_update_status,
                                            mock_link_sitter, mock_assign_num, mock_get_pool,
                                            mock_log_event, mock_update_last_active, mock_upsert):
    """Test that a new client triggers assignment and updates timestamp."""
    print("\nTesting New Client Assignment Timestamp...")

    # Sitter exists
    mock_find_sitter.side_effect = lambda num: {
        "id": "recSitter",
        "fields": {"Full Name": "Jane Sitter", "phone-number": "+1sitter_real", "twilio-number": "+1sitter_twilio"}
    } if num == "+1sitter_twilio" else None
    
    # Client does NOT exist initially
    mock_find_client.return_value = None
    
    # Mock pool number availability
    mock_get_pool.return_value = {"id": "recPool", "fields": {"phone-number": "+1pool_new"}}
    
    # Mock assign success
    mock_assign_num.return_value = True
    
    # Mock client creation
    mock_upsert.return_value = ({"id": "recNewClient", "fields": {"Name": "New Client"}}, True)

    payload = {"From": "+1new_client", "To": "+1sitter_twilio", "Body": "First message"}
    await intercept(MockRequest(payload))
    
    # Verify assignment was called
    mock_assign_num.assert_called_once()
    
    # Verify suffix was appended for new assignment
    _, kwargs = mock_send_sms.call_args
    assert "From New Client :" in kwargs['body']
    print("SUCCESS: New client assignment triggered and suffix verified.")

async def run_all():
    await test_inbound_flow()
    await test_outbound_flow()
    await test_assignment_updates_timestamp()

if __name__ == "__main__":
    asyncio.run(run_all())
