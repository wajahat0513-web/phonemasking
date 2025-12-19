from twilio.rest import Client
import os
from config import settings

def send_test_sms(to_number, body):
    # Use credentials from settings
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    client = Client(account_sid, auth_token)
    
    # Use one of the known working numbers
    from_number = "+18046046355"
    
    try:
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        print(f"Message sent! SID: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return None

if __name__ == "__main__":
    send_test_sms("+13399701013", "This is a test message from your Pet Sitting Masking Service. It's working!")
