from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PROXY_SERVICE_SID: str
    TWILIO_MESSAGING_SERVICE_SID: str
    AIRTABLE_BASE_ID: str
    AIRTABLE_API_KEY: str
    
    # Table Names
    AIRTABLE_SITTERS_TABLE: str = "Sitters"
    AIRTABLE_CLIENTS_TABLE: str = "Clients"
    AIRTABLE_MESSAGES_TABLE: str = "Messages"
    AIRTABLE_NUMBER_INVENTORY_TABLE: str = "Number Inventory"
    AIRTABLE_AUDIT_LOG_TABLE: str = "Audit Log"

    class Config:
        env_file = ".env"

settings = Settings()
