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
