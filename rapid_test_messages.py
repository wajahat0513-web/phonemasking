"""
Quick test script to send messages through Twilio Proxy
This will trigger the /intercept webhook automatically
"""
from twilio.rest import Client
from config import settings
import time

# Initialize Twilio client
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

# The session we created earlier
SESSION_SID = "KC0ca3c89a59696b02eda0dc2b4144408d"

def send_test_message(message_body):
    """Send a message through the Proxy session"""
    try:
        # Send from the client's number to the sitter
        # This will automatically route through Proxy and trigger /intercept
        message = client.proxy.v1.services(settings.TWILIO_PROXY_SERVICE_SID) \
            .sessions(SESSION_SID) \
            .participants \
            .list()[0] \
            .message_interactions \
            .create(body=message_body)
        
        print(f"✅ Message sent! Interaction SID: {message.sid}")
        print(f"   Body: {message_body}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Sending test messages through Twilio Proxy...")
    print("This will trigger your /intercept webhook\n")
    
    # Send a few test messages
    messages = [
        "Test message #1 - checking intercept",
        "Test message #2 - verifying payload logging",
        "Test message #3 - final check"
    ]
    
    for i, msg in enumerate(messages, 1):
        print(f"\n[{i}/3] Sending...")
        send_test_message(msg)
        time.sleep(2)  # Wait 2 seconds between messages
    
    print("\n✅ Done! Check your Railway logs now.")
