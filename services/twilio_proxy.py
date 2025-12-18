"""
Twilio Proxy Service
====================
This script handles all direct interactions with the Twilio Proxy API.

Key Functionality:
- Creates and manages Proxy Sessions (conversations).
- Adds participants (Client and Sitter) to sessions.
- Handles session termination (closing).
- Manages proxy phone number assignments within sessions.

The Twilio Proxy service is responsible for the core logic of masking phone numbers,
ensuring that neither party sees the other's real contact information.
"""

from twilio.rest import Client
from config import settings
from utils.logger import log_info, log_error

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
service_sid = settings.TWILIO_PROXY_SERVICE_SID

def create_session(sitter_id: str, client_id: str):
    """
    Creates a new Proxy Session in Twilio.
    
    A session represents a conversation thread between two participants.
    
    Args:
        sitter_id (str): Unique identifier for the sitter (used for naming).
        client_id (str): Unique identifier for the client (used for naming).
        
    Returns:
        str: The unique Session SID (e.g., KC...).
    """
    import time
    timestamp = int(time.time())
    unique_name = f"{sitter_id}_{client_id}_{timestamp}"
    try:
        session = client.proxy.v1.services(service_sid).sessions.create(
            unique_name=unique_name,
            ttl=1209600  # 14 days
        )
        log_info("Created Twilio Session", f"SID: {session.sid}")
        return session.sid
    except Exception as e:
        log_error("Failed to create Twilio Session", str(e))
        raise e

def add_participant(session_sid: str, identifier: str, proxy_identifier: str = None):
    """
    Adds a participant (user) to an existing Proxy Session.
    
    Args:
        session_sid (str): The Session SID to join.
        identifier (str): The real phone number of the participant.
        proxy_identifier (str, optional): The specific proxy number they should see/use.
                                          If None, Twilio picks one from the pool.
                                          
    Returns:
        str: The Participant SID (e.g., KP...).
    """
    try:
        kwargs = {"identifier": identifier}
        if proxy_identifier:
            kwargs["proxy_identifier"] = proxy_identifier
            
        participant = client.proxy.v1.services(service_sid).sessions(session_sid).participants.create(
            **kwargs
        )
        log_info("Added Participant", f"SID: {participant.sid}, Identifier: {identifier}")
        return participant.sid
    except Exception as e:
        log_error("Failed to add participant", str(e))
        raise e

def get_participant(session_sid: str, participant_sid: str):
    """
    Retrieves a participant's details from a session.
    """
    try:
        participant = client.proxy.v1.services(service_sid) \
            .sessions(session_sid) \
            .participants(participant_sid) \
            .fetch()
        return participant
    except Exception as e:
        log_error(f"Failed to fetch participant {participant_sid}", str(e))
        return None

def list_participants(session_sid: str):
    """
    Lists all participants in a session.
    """
    try:
        participants = client.proxy.v1.services(service_sid) \
            .sessions(session_sid) \
            .participants \
            .list()
        return participants
    except Exception as e:
        log_error(f"Failed to list participants for session {session_sid}", str(e))
        return []

def remove_participant(session_sid: str, participant_sid: str):
    """
    Removes a participant from a session.
    """
    try:
        client.proxy.v1.services(service_sid) \
            .sessions(session_sid) \
            .participants(participant_sid) \
            .delete()
        log_info(f"Removed participant {participant_sid} from session {session_sid}")
        return True
    except Exception as e:
        log_error(f"Failed to remove participant {participant_sid}", str(e))
        return False

def send_session_message(session_sid: str, participant_sid: str, body: str):
    """
    Sends a message through a Proxy session as a specific participant.
    """
    try:
        interaction = client.proxy.v1.services(service_sid) \
            .sessions(session_sid) \
            .participants(participant_sid) \
            .message_interactions \
            .create(body=body)
        log_info(f"Sent session message via Proxy → SID: {interaction.sid}")
        return interaction.sid
    except Exception as e:
        log_error(f"Failed to send session message through Proxy", str(e))
        return None

def close_session(session_sid: str):
    """
    Terminates a Proxy Session.
    
    Once closed, participants can no longer message each other using the
    assigned proxy numbers for this specific conversation.
    
    Args:
        session_sid (str): The Session SID to close.
    """
    try:
        client.proxy.v1.services(service_sid).sessions(session_sid).update(status="closed")
        log_info("Closed Twilio Session", f"SID: {session_sid}")
    except Exception as e:
        log_error("Failed to close session", str(e))
        raise e

def update_proxy_number(session_sid: str, participant_sid: str, new_number: str):
    """
    Updates the proxy number assigned to a participant in a session.
    
    Note: Twilio Proxy participants are immutable regarding their proxy number.
    To "update" it, we typically have to remove and re-add the participant,
    or close and recreate the session. This function is a placeholder for that logic.
    
    Args:
        session_sid (str): The Session SID.
        participant_sid (str): The Participant SID.
        new_number (str): The new proxy number to assign.
    """
    try:
        # Logic to swap participant would go here
        # client.proxy.v1.services(service_sid).sessions(session_sid).participants(participant_sid).delete()
        pass
    except Exception as e:
        log_error("Failed to update proxy number", str(e))
        raise e

def log_message_to_twilio():
    pass

def search_and_purchase_number(area_code: str, number_type: str = "local"):
    """
    Search for and purchase a phone number from Twilio.
    
    Args:
        area_code (str): Area code to search (e.g., "303", "720")
        number_type (str): Type of number ("local", "toll-free")
        
    Returns:
        dict: {
            "phone_number": "+13035551234",
            "sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "capabilities": {"sms": True, "voice": True}
        }
        
    Raises:
        Exception: If no numbers available or purchase fails
    """
    try:
        # Search for available numbers
        log_info(f"Searching for available numbers in area code {area_code}")
        available_numbers = client.available_phone_numbers('US').local.list(
            area_code=area_code,
            sms_enabled=True,
            voice_enabled=True,
            limit=10
        )
        
        if not available_numbers:
            raise Exception(f"No available numbers in area code {area_code}")
        
        # Purchase the first available number
        number_to_purchase = available_numbers[0].phone_number
        log_info(f"Purchasing number: {number_to_purchase}")
        
        purchased_number = client.incoming_phone_numbers.create(
            phone_number=number_to_purchase
        )
        
        log_info("Purchased Twilio Number", f"Number: {purchased_number.phone_number}, SID: {purchased_number.sid}")
        
        return {
            "phone_number": purchased_number.phone_number,
            "sid": purchased_number.sid,
            "capabilities": {
                "sms": purchased_number.capabilities.get('sms', False),
                "voice": purchased_number.capabilities.get('voice', False)
            }
        }
    except Exception as e:
        log_error("Failed to purchase number", str(e))
        raise e

def add_number_to_proxy_service(phone_number: str):
    """
    Add a purchased phone number to the Twilio Proxy Service.
    
    Args:
        phone_number (str): E.164 formatted phone number
        
    Returns:
        str: Proxy Phone SID (PNxxxxxxxx...)
        
    Raises:
        Exception: If number already in proxy or add fails
    """
    try:
        log_info(f"Adding number {phone_number} to Proxy Service")
        proxy_phone = client.proxy.v1.services(service_sid).phone_numbers.create(
            phone_number=phone_number
        )
        
        log_info("Added number to Proxy Service", f"Number: {phone_number}, Proxy SID: {proxy_phone.sid}")
        
        return proxy_phone.sid
    except Exception as e:
        log_error("Failed to add number to Proxy", str(e))
        raise e
