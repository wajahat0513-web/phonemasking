# Project Requirements
## Pet Sitting - Phone Masking Automation (Twilio + Airtable + Railway)

**Client:** Pure In Home Pet Sitting
**Platform:** Twilio + Zapier + Airtable + Railway + Time To Pet
**Timeline:** TBD
**Start Date:** November 13, 2025
**Due Date:** TBD
**Project Payout:** TBD
**Credentials:** Will Be Provided

### Project Overview
This project delivers a private, scalable communication system for sitters and clients. It leverages Twilio's Proxy Service and a custom Railway middleware server with a 14-day Session TTL to ensure sitters can communicate with multiple clients while their personal phone numbers remain masked. The core technical solution uses the Out-of-Session Callback to automatically create separate, distinct text threads on the sitter's regular phone, solving the threading problem without relying on a real-time API from the Time to Pet platform.

### Messaging Templates (Click Here)

### 1. Build Sequence (Logical Order)
*   **Twilio Setup** - Create subaccount, A2P registration, Proxy Service, and initial number purchasing (Reserved, Pool, Standby).
*   **Airtable Base** - Create four core tables (Sitters, Clients, Numbers, Audit Log) with all required fields, links, and formulas.
*   **Railway Server** - Set up and deploy the three application handlers (Out-of-Session, Intercept, Number Attach Routine).
*   **Airtable Interfaces/Forms** - Build the Pool Utilization Dashboard, Add New Sitter Form, and Sitter Directory.
*   **Zapier Automations** - Create and test the six core automations.

### 2. Core Technical Components

#### A. Twilio Configuration
*   **Number Purchasing (Initial):** Purchase 34 Reserved (sitter) numbers, 20 Pool (proxy) numbers, and 1 Standby Reserved number. All numbers must be local Colorado area codes (303/720).
*   **Proxy Service Setup:**
    *   **Session TTL:** Set Session Time-to-Live (inactivity limit) to 14 days.
    *   **Out-of-Session Callback:** Points to the Railway Server Out-of-Session Handler URL (for auto-session creation).
    *   **Intercept Callback:** Points to the Railway Server Intercept Handler URL (for message prepending).

#### B. Airtable Base (Data Source & Purpose)
The base must contain four tables linked by record IDs, utilizing Lookup and Rollup formulas to facilitate server-side lookups based on the Reserved Number:
*   **Sitters Table:** Sitter profile data and a link to their Reserved Twilio Number.
*   **Clients Table:** Client data and their real phone number in E.164 format. Note on Duplicates: Zap 1 performs an initial Upsert (Update if exists, Insert if new) based on the client's unique Time to Pet ID to prevent duplicates.
*   **Number Inventory Table:** Master list tracking each number’s Lifecycle (Reserved Active, Pool, Standby) and Status (Ready, Pending, Failed).
*   **Audit Log Table:** Store a concise log of all key system events.

#### C. Railway Server (Middleware)
A server instance must host the following three application handlers:
*   **Out-of-Session Handler (Core Logic):** Auto-creates a new Proxy Session when a client texts a sitter's Reserved Number for the first time.
*   **Intercept Handler (Sitter Clarity):** Prepends the client's name (e.g., [Client Name]: Hey...) to messages before they are forwarded to the sitter's real phone.
*   **Attach-Number Routine:** Manages Twilio API calls for purchasing and adding new numbers to the Proxy Service.

#### D. Airtable Interfaces
The build must include three key interfaces:

**1. Add/Remove Sitter Form (Airtable Form)**
*   **Purpose:** The entry point for quickly provisioning a new sitter. Collect essential sitter information to create a new Sitter record and trigger Zap 2 (Reserved Number Assignment).
*   **Required Fields:**
    *   Sitter Name (Text)
    *   Sitter Email (Email)
    *   Sitter Real Phone Number (Phone - must be collected in E.164 format or normalized by Zap 2)
    *   Function - Enables adding or removing

**2. Pool Utilization Dashboard (Airtable Interface)**
*   **Purpose:** Provide administrators with real-time utilization metrics to monitor system health and justify pool purchasing (Zap 4).
*   **Required Fields (Summary/Rollup/Count):**
    *   Total Ready Pool Numbers (Count of Inventory records with Lifecycle=Pool, Status=Ready)
    *   Total Active Proxy Sessions (Value pulled from Twilio API via middleware or a summary field in the Audit Log)
    *   Pool Utilization Rate (Formula field: Active Sessions / Ready Pool Numbers)
    *   Standby Reserved Count (Count of Inventory records with Lifecycle=Standby Reserved)
    *   Pending Pool Numbers (Count of Inventory records with Lifecycle=Pool, Status=Pending)

**3. Sitter Directory (Lookup) Interface (Airtable Interface)**
*   **Purpose:** Allow staff to easily look up the contact information associated with a sitter's profile.
*   **Required Fields (Displayed/Lookup):**
    *   Sitter Name
    *   Sitter Real Phone Number (Direct contact for the sitter)
    *   Sitter Reserved (Masked) Number (The number clients use to text the sitter)
    *   Reserved Number Status (Current status: Ready, Pending, or Failed)

### 3. Zapier Automations (6 Required Zaps)

**Zap 1 – Client Sync**
*   **Trigger:** Time to Pet Webhook when a client record is Created or Updated.
*   **Action/Logic:** Find or Create (Upsert) a row in the Airtable Clients table based on the unique Time to Pet ID. Normalize the phone number to E.164 format.
*   **Filter/Paths:** Only proceed if the phone number is provided and valid.

**Zap 2 – Add New Sitter (Reserved Number Assignment)**
*   **Trigger:** New record submitted in the Add New Sitter Form (Airtable Form).
*   **Action/Logic:**
    *   **Path A (Standby Available):** Assign the existing Standby number to the new Sitter, update its Status to Reserved Active, and send the appropriate owner email. Then, order one new Reserved number (Status=Pending) to replenish the Standby.
    *   **Path B (No Standby):** Order one new Reserved number (Status=Pending) and send the appropriate owner email.
    *   **Path C:** Remove linking of number to sitter and it becomes standby.

**Zap 3 – Number Attach Verification**
*   **Trigger:** New/Updated record in Number Inventory where Status = Pending.
*   **Action/Logic:** Call the Railway Attach-Number Routine to add the number to the Twilio Proxy Service. Send a test SMS. If successful, update Number Inventory Status = Ready and if this number was associated with a Sitter (Path B in Zap 2), send the appropriate owner email.

**Zap 4 – Pool Capacity Monitor**
*   **Trigger:** Schedule runs every 48 hours.
*   **Action/Logic:** Computes Pool Utilization rate. If Utilization $\geq 0.87$, and no cool-down period (72 hours) or pending pool numbers exist, purchase exactly one new local Pool Number via the Railway Attach-Number Routine and create a Number Inventory row (Status=Pending, Lifecycle=Pool).

**Zap 5 – Standby Keeper**
*   **Trigger:** Schedule runs every 48 hours.
*   **Action/Logic:** If CountOfStandbyReservedNumbers == 0, purchase 1 new number via Railway Attach-Number Routine and create Number Inventory row (Status=Pending, Lifecycle=Standby Reserved).

**Zap 6 – Delivery/Error Alerts (System Status Callback)**
*   **Trigger:** Twilio Status Callback when a message delivery status is failed or undelivered.
*   **Action/Logic:** Uses Paths based on the Twilio Error Code.
    *   **Path: Temporary Failure (30002–30005, 5xx):** Delay for 10 minutes and perform one auto-retry.
    *   **Path: Permanent Failure (All Others):** Log the error and send a simple SMS Alert to the Sitter.
    *   **Path: Systemic Issue:** If more than 5 permanent failures in a 24-hour period, send an Owner Summary Alert email to the administrator.

### 4. Testing & Deliverables

#### A. Testing Plan
The plan must include a dedicated test for every single automation (Zap 1-6) and the core Proxy logic.
*   **Test 1: Sitter Provisioning (Zaps 2 & 3):** Test Path A (Standby used) and Path B (Standby empty). Verify the correct email template is sent to the owner.
*   **Test 2: Proxy Session (Core Logic):** A client texts a sitter’s Reserved Number for the first time. Verify a new Proxy Session is created, the sitter receives the message with the [Client Name]: prefix, and the sitter’s reply routes successfully.
*   **Test 3: Error Handling (Zap 6):** Simulate failure codes to verify: one auto-retry occurs for temporary failures, and the Sitter SMS alert is sent for permanent errors (e.g., 30007).
*   **Test 4: Pool Auto-Scaling (Zap 4 & 3):** Manually simulate high utilization (or adjust threshold for testing) and verify that Zap #4 triggers the purchase of exactly one new Pool number and Zap #3 successfully sets its status to Ready.
*   **Test 5: Standby Pool (Zap 5):** Manually delete the Standby Reserved Number and verify Zap #5 purchases and provisions a new one within 48 hours.

#### B. Deliverables
*   Twilio Messaging Service + Proxy Service (14-day TTL) built and configured.
*   Airtable Base and all three Interfaces/Forms built.
*   Railway Handlers deployed.
*   Zap 1–6 built and tested.
*   Dedicated SOP for each of the six Zaps.
*   One System Workflow Diagram (end-to-end visual).
