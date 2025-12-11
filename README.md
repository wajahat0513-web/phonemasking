# Phone Masking Service

A robust, FastAPI-based service designed to handle phone number masking, session management, and communication interception. This service integrates with **Twilio Proxy** for masking and **Airtable** for data persistence and logging.

It allows for secure communication between parties (e.g., Sitters and Clients) without revealing their real phone numbers, managing the lifecycle of these sessions, and logging all interactions.

## Features

*   **Phone Number Masking**: Securely masks real phone numbers using Twilio Proxy services.
*   **Session Management**: Create, manage, and terminate communication sessions between two parties.
*   **Communication Interception**: Handle and log incoming messages or calls via webhooks.
*   **Dynamic Number Allocation**: logic to assign numbers from a pool.
*   **Data Persistence**:  Integrates with Airtable to store and retrieve data about:
    *   Sitters & Clients
    *   Messages
    *   Number Inventory
    *   Audit Logs
*   **Containerized**: Fully Dockerized for easy deployment and testing (Railway compatible).

## Zapier Automations

This project requires **6 Zapier automations** to handle:
- Client synchronization from Time to Pet
- Sitter provisioning and number assignment
- Number verification and attachment
- Automated pool capacity monitoring
- Standby number replenishment
- Message delivery error handling

**📋 Setup Instructions**: See [zapier/ZAP_PROMPTS.README.md](zapier/ZAP_PROMPTS.README.md) for detailed step-by-step Zap configuration guides.

**🔌 API Integration**: See [zapier/ENDPOINTS_REFERENCE.md](zapier/ENDPOINTS_REFERENCE.md) for Railway endpoint documentation and implementation status.

## Tech Stack

*   **Language**: Python 3.13+
*   **Framework**: FastAPI
*   **Server**: Uvicorn
*   **Integrations**:
    *   [Twilio](https://www.twilio.com/) (Proxy, Messaging)
    *   [Airtable](https://airtable.com/) (Database/Logging)
*   **Containerization**: Docker

## Project Structure

```
d:\phonemasking\
├── main.py                 # Application entry point
├── config.py               # Configuration and Environment variables
├── routers/                # API Route definitions
│   ├── sessions.py         # Session management endpoints
│   ├── intercept.py        # Webhook interception endpoints
│   └── numbers.py          # Phone number management endpoints
├── services/               # Business logic and Integrations
│   ├── airtable_client.py  # Airtable API interactions
│   ├── twilio_proxy.py     # Twilio Proxy API interactions
│   └── ...
├── utils/                  # Utility functions (logging, etc.)
├── zapier/                 # Zapier automation documentation
│   ├── ZAP_PROMPTS.README.md      # Master guide for all Zaps
│   ├── ENDPOINTS_REFERENCE.md     # Railway API endpoint specs
│   ├── zap_1_client_sync.md       # Client sync automation
│   ├── zap_2_sitter_provisioning.md # Sitter provisioning
│   ├── zap_3_number_verification.md # Number verification
│   ├── zap_4_pool_monitor.md      # Pool capacity monitor
│   ├── zap_5_standby_keeper.md    # Standby replenishment
│   └── zap_6_delivery_alerts.md   # Delivery error handling
├── Dockerfile              # Docker build configuration
├── DOCKER_TEST.md          # Comprehensive Docker testing guide
└── requirements.txt        # Python dependencies
```

## Prerequisites

Before running the application, ensure you have the following:

1.  **Python 3.13+** installed.
2.  **Docker** (optional, for containerized running).
3.  **Twilio Account**: With a Proxy Service and Messaging Service set up.
4.  **Airtable Base**: tailored with the necessary tables (`Sitters`, `Clients`, `Messages`, `Number Inventory`, `Audit Log`).

## Configuration

Create a `.env` file in the root directory. You can use `.env.example` as a template.

**Required Environment Variables:**

```env
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PROXY_SERVICE_SID=your_proxy_service_sid
TWILIO_MESSAGING_SERVICE_SID=your_messaging_service_sid

AIRTABLE_BASE_ID=your_airtable_base_id
AIRTABLE_API_KEY=your_airtable_api_key
```

**Optional/Default Configuration (Table Names):**
*   `AIRTABLE_SITTERS_TABLE` (default: "Sitters")
*   `AIRTABLE_CLIENTS_TABLE` (default: "Clients")
*   `AIRTABLE_MESSAGES_TABLE` (default: "Messages")
*   `AIRTABLE_NUMBER_INVENTORY_TABLE` (default: "Number Inventory")
*   `AIRTABLE_AUDIT_LOG_TABLE` (default: "Audit Log")

## Installation & Local Development

1.  **Clone the repository** (if applicable) or navigate to the project directory.

2.  **Create a virtual environment**:
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # Linux/Mac
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application**:
    ```bash
    python main.py
    # OR directly with uvicorn
    uvicorn main:app --reload --host 0.0.0.0 --port 8080
    ```

5.  **Access the API**:
    *   API Root: `http://localhost:8080/`
    *   **Interactive Documentation (Swagger UI)**: `http://localhost:8080/docs`

## Docker Support

This application is ready to run in Docker.

1.  **Build the image**:
    ```bash
    docker build -t phonemasking:latest .
    ```

## Airtable Schema

The application relies on the following Airtable structure. Ensure your Base matches this schema:

### 1. Sitters
*   **Primary Field**: `Full Name` (Single line text)
*   **Fields**:
    *   `Status` (Single select: Active, Inactive, Reserved Active)
    *   `Phone Number` (Single line text)
    *   `Twilio Number` (Phone number)
    *   `Date Added` (Date)
    *   `Messages` (Linked to [Messages])
    *   `Label` (Single line text)
    *   `Number Inventory` (Linked to [Number Inventory])
    *   `Clients` (Linked to [Clients])
    *   `Created via Form` (Single select: Yes, No)
    *   `Provisioning Status` (Single select: Pending, Active, Inactive, Error)
    *   `Sitter Phone (E.164)` (Phone number)
    *   `Sitter Phone (raw)` (Single line text)
*   **Description**: Primary table for managing pet sitters with phone masking capabilities.

### 2. Clients
*   **Primary Field**: `Name` (Single line text)
*   **Fields**:
    *   `Phone Number` (Single line text)
    *   `Linked Sitter` (Linked to [Sitters])
    *   `Last Active` (Date)
    *   `Session SID` (Single line text)
    *   `Created At` (Date)
    *   `Email` (Single line text)
    *   `Created (Airtable)` (Date - Formula)
    *   `Twilio Error Count` (Number - Integer)
    *   `Client Phone (raw)` (Phone number)
    *   `Client Phone (E.164)` (Phone number)
    *   `Preferred Contact Method` (Single select: SMS, Email, Phone Call)
*   **Description**: Manages client information and their connections to sitters.

### 3. Number Inventory
*   **Primary Field**: `PhoneNumber` (Phone number)
*   **Fields**:
    *   `Assigned Sitter` (Linked to [Sitters])
    *   `Status` (Single select: Available, Assigned, Standby Reserved, Reserved Active, Pending, Ready, Failed)
    *   `Purchase Date` (Date)
    *   `Twilio SID` (Single line text)
    *   `Created At` (Date - Formula)
    *   `Updated At` (Date - Formula)
    *   `Lifecycle` (Single select: Reserved, Standby Reserved, Pool, Standby)
    *   `Attach Status` (Single select: Pending, Ready, Failed)
    *   `Verification Status` (Single select: Not Sent, Sent, Verified, Failed)
    *   `Purpose` (Single select: Sitter Assignment, Pool Expansion, Standby Replenishment)
*   **Description**: Tracks phone number inventory and assignment status for the masking system.

### 4. Audit Log
*   **Primary Field**: `Event` (Single line text)
*   **Fields**:
    *   `Description` (Long text)
    *   `Timestamp` (Date)
    *   `Related Sitter` (Single line text)
    *   `Related Client` (Single line text)
    *   `Details` (Long text)
    *   `Category` (Single select: Provisioning, Messaging, Error, System, Pool, Standby, Client Sync, Delivery Error)
    *   `Severity` (Single select: Info, Warning, Critical, Error)
*   **Description**: System audit trail for tracking events and troubleshooting.

### 5. Messages
*   **Primary Field**: `From` (Phone number)
*   **Fields**:
    *   `To` (Phone number)
    *   `Body` (Long text)
    *   `Sender Type` (Single select: client, sitter)
    *   `Proxy Number` (Phone number)
    *   `Timestamp` (Date)
    *   `Sitter` (Linked to [Sitters])
    *   `Client` (Single line text)
    *   `Session SID` (Single line text)
    *   `Status` (Single select: received, sent, delivered, failed, undelivered, pending)
    *   `Twilio Status` (Single select: queued, sent, delivered, failed, undelivered)
    *   `Twilio Error Code` (Single line text)
*   **Description**: Message log for tracking communications between clients and sitters through proxy numbers.

2.  **Run the container**:
    ```bash
    docker run -p 8080:8080 --env-file .env phonemasking:latest
    ```

For detailed Docker testing instructions, including troubleshooting and validation steps, please refer to [DOCKER_TEST.md](./DOCKER_TEST.md).

## Deployment

The project is configured for deployment on platforms like **Railway** (see `railway.json`).
Ensure functionality matches the environment variables set in your deployment platform.
