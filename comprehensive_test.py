"""
Comprehensive test using real credentials from .env
This will:
1. Connect to Airtable to get real sitter/client data
2. Send a message through Twilio Proxy
3. Trigger the /intercept webhook
"""

from config import settings
from services.airtable_client import sitters_table, clients_table
from services.twilio_proxy import client
import json

print("=" * 60)
print("COMPREHENSIVE SYSTEM TEST")
print("=" * 60)

# Step 1: Check Airtable Connection
print("\n[1/4] Connecting to Airtable...")
try:
    sitters = sitters_table.all(max_records=5)
    clients = clients_table.all(max_records=5)
    
    print(f"✅ Found {len(sitters)} sitters")
    print(f"✅ Found {len(clients)} clients")
    
    if sitters:
        print(f"\nSample Sitter:")
        sitter = sitters[0]['fields']
        print(f"  Name: {sitter.get('Full Name', sitter.get('Name', 'N/A'))}")
        print(f"  Twilio Number: {sitter.get('Twilio Number', 'N/A')}")
        print(f"  Phone Number: {sitter.get('Phone Number', 'N/A')}")
    
    if clients:
        print(f"\nSample Client:")
        client_data = clients[0]['fields']
        print(f"  Name: {client_data.get('Name', 'N/A')}")
        print(f"  Phone: {client_data.get('Phone Number', 'N/A')}")
        
except Exception as e:
    print(f"❌ Airtable connection failed: {e}")
    exit(1)

# Step 2: Check Twilio Connection
print("\n[2/4] Connecting to Twilio...")
try:
    account = client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
    print(f"✅ Connected to Twilio account: {account.friendly_name}")
except Exception as e:
    print(f"❌ Twilio connection failed: {e}")
    exit(1)

# Step 3: List Proxy Sessions
print("\n[3/4] Checking Proxy Sessions...")
try:
    sessions = client.proxy.v1.services(settings.TWILIO_PROXY_SERVICE_SID).sessions.list(limit=5)
    print(f"✅ Found {len(sessions)} active sessions")
    
    if sessions:
        latest_session = sessions[0]
        print(f"\nLatest Session:")
        print(f"  SID: {latest_session.sid}")
        print(f"  Status: {latest_session.status}")
        print(f"  Created: {latest_session.date_created}")
        
        # Step 4: Send test message through this session
        print("\n[4/4] Sending test message through Proxy...")
        try:
            participants = client.proxy.v1.services(settings.TWILIO_PROXY_SERVICE_SID) \
                .sessions(latest_session.sid) \
                .participants \
                .list()
            
            if participants:
                print(f"  Found {len(participants)} participants")
                
                # Send message as first participant
                participant_sid = participants[0].sid
                
                interaction = client.proxy.v1.services(settings.TWILIO_PROXY_SERVICE_SID) \
                    .sessions(latest_session.sid) \
                    .participants(participant_sid) \
                    .message_interactions \
                    .create(body="🚀 AUTOMATED TEST: This should trigger /intercept with full logging!")
                
                print(f"✅ Message sent!")
                print(f"  Interaction SID: {interaction.sid}")
                print(f"  Body: {interaction.outbound_message_body}")
                print(f"\n⏳ Check Railway logs NOW for intercept webhook!")
                print(f"   Look for: 'Intercept request headers' and 'Intercept payload'")
                
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
    else:
        print("⚠️  No active sessions found")
        print("   Create a session first by texting the proxy number")
        
except Exception as e:
    print(f"❌ Proxy session check failed: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
