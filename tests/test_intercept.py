
import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

# Add the project root to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dependencies before importing the router
with patch('services.airtable_client.find_sitter_by_twilio_number') as mock_find_sitter, \
     patch('services.airtable_client.find_client_by_phone') as mock_find_client, \
     patch('services.airtable_client.find_client_by_twilio_number') as mock_find_client_pool, \
     patch('services.twilio_proxy.send_sms') as mock_send_sms, \
     patch('services.airtable_client.save_message') as mock_save_msg, \
     patch('services.airtable_client.update_message_status') as mock_update_status, \
     patch('services.airtable_client.update_client_linked_sitter') as mock_link_sitter, \
     patch('services.airtable_client.assign_pool_number_to_client') as mock_assign_num, \
     patch('services.airtable_client.get_ready_pool_number') as mock_get_pool, \
     patch('services.airtable_client.log_event') as mock_log_event:

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

    async def test_inbound_flow():
        """Test Client -> Sitter routing with suffix."""
        print("Testing Inbound (Client -> Sitter)...")
        
        mock_find_sitter.reset_mock()
        mock_find_client.reset_mock()
        mock_send_sms.reset_mock()
        
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
        assert kwargs['body'] == "Hello there - [John Client]"
        # Verify Sitter Link (Should be Name, not ID)
        mock_link_sitter.assert_called_once_with("recClient", "Jane Sitter")
        print("SUCCESS: Inbound routing and suffix verified.")

    async def test_outbound_flow():
        """Test Sitter -> Client routing."""
        print("\nTesting Outbound (Sitter -> Client)...")
        
        mock_find_sitter.reset_mock()
        mock_find_client_pool.reset_mock()
        mock_send_sms.reset_mock()

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
        print("SUCCESS: Outbound routing verified.")

    async def test_assignment_updates_timestamp():
        """Test that a new client triggers assignment and updates timestamp."""
        print("\nTesting New Client Assignment Timestamp...")
        
        mock_find_sitter.reset_mock()
        mock_find_client.reset_mock()
        mock_assign_num.reset_mock()
        mock_get_pool.reset_mock()

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

        payload = {"From": "+1new_client", "To": "+1sitter_twilio", "Body": "First message"}
        
        with patch('routers.intercept.create_or_update_client') as mock_upsert:
            mock_upsert.return_value = ({"id": "recNewClient", "fields": {"Name": "New Client"}}, True)
            await intercept(MockRequest(payload))
        
        # Verify assignment was called
        mock_assign_num.assert_called_once()
        print("SUCCESS: New client assignment triggered.")

    async def run_all():
        await test_inbound_flow()
        await test_outbound_flow()
        await test_assignment_updates_timestamp()

    if __name__ == "__main__":
        asyncio.run(run_all())
