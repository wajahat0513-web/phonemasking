# Railway API Endpoints Reference

This document provides detailed specifications for all Railway API endpoints used by the Zapier automations.

## Base URL

```
https://your-railway-app.railway.app
```

Replace `your-railway-app` with your actual Railway deployment URL.

## Authentication

Currently, all endpoints are **public** (no authentication required). This is acceptable for MVP but should be secured in production with:
- API key authentication
- IP whitelisting (Zapier IP ranges)
- Rate limiting

---

## Endpoint Status Summary

| Endpoint | Status | Used By | Implementation File |
|----------|--------|---------|---------------------|
| `POST /out-of-session` | ✅ Implemented | Twilio Proxy | [routers/sessions.py](../routers/sessions.py) |
| `POST /intercept` | ✅ Implemented | Twilio Proxy | [routers/intercept.py](../routers/intercept.py) |
| `POST /attach-number` | ✅ Implemented | Zaps 2, 3 | [routers/numbers.py](../routers/numbers.py) |
| `POST /numbers/purchase` | ✅ Implemented | Zaps 2, 4, 5 | [routers/numbers.py](../routers/numbers.py) |
| `POST /inventory/check-and-replenish` | ⚠️ Optional | Zap 4 | Use `/numbers/purchase` instead |
| `POST /numbers/standby-replenish` | ⚠️ Optional | Zap 5 | Use `/numbers/purchase` instead |
| `GET /sessions/active-count` | ⚠️ Optional | Zap 4 | Use Airtable query instead |

**Legend**:
- ✅ Implemented and working
- ⚠️ Optional (alternative solution available)

---

## Implemented Endpoints

### POST /out-of-session

**Purpose**: Auto-create Proxy sessions when clients text sitters for the first time

**Used By**: Twilio Proxy (automatic callback)

**Implementation**: [routers/sessions.py](../routers/sessions.py)

**Request**:
```http
POST /out-of-session
Content-Type: application/x-www-form-urlencoded

UniqueName=session_sitter_recXXX_client_recYYY
ParticipantLabel=+13035551234
ProxyIdentifier=+17205559999
```

**Response** (Success):
```json
{
  "success": true,
  "session_sid": "KCxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "message": "Session created successfully"
}
```

**Notes**:
- Triggered automatically by Twilio when a client texts a sitter's reserved number
- Creates client record if not exists (race condition with Zap 1)
- Creates Proxy session with 14-day TTL
- Logs event to Airtable Audit Log

---

### POST /intercept

**Purpose**: Prepend client name to messages before forwarding to sitter

**Used By**: Twilio Proxy (automatic callback)

**Implementation**: [routers/intercept.py](../routers/intercept.py)

**Current Status**: ⚠️ Logs messages but does NOT modify message body

**Request**:
```http
POST /intercept
Content-Type: application/x-www-form-urlencoded

InteractionSid=KIxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
InteractionAccountSid=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
InteractionServiceSid=KSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
InteractionSessionSid=KCxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
InteractionType=Message
InteractionData={"body":"Hello from client","from":"+13035551234"}
```

**Response** (Current - No Modification)**:
```json
{}
```

**Response (Required - With Prepend)**:
```json
{
  "body": "[Client Name]: Hello from client"
}
```

**Implementation Gap**:
- Currently only logs the message to Airtable
- Needs to return modified body with `[Client Name]:` prefix
- See [ISSUE_ANALYSIS.md](../ISSUE_ANALYSIS.md) #2 for details

---

### POST /attach-number

**Purpose**: Attach a phone number to the Twilio Proxy Service and assign to sitter

**Used By**: Zaps 2, 3

**Implementation**: [routers/numbers.py](../routers/numbers.py)

**Request**:
```http
POST /attach-number
Content-Type: application/json

{
  "sitter_id": "recXXXXXXXXXXXXXX",
  "phone_number": "+13035551234"
}
```

**Request Fields**:
- `sitter_id` (optional): Airtable record ID of sitter
  - If provided: Assigns number to sitter in Airtable
  - If empty: Only attaches to Proxy (for pool/standby numbers)
- `phone_number` (optional): Phone number to attach
  - If provided: Uses this number
  - If empty: Looks up number from sitter's record

**Response** (Success):
```json
{
  "success": true,
  "message": "Number attached successfully",
  "phone_number": "+13035551234",
  "proxy_phone_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Response** (Error):
```json
{
  "success": false,
  "error": "Number already attached to Proxy",
  "details": "..."
}
```

**Notes**:
- Supports both JSON and form-encoded payloads (Zapier compatibility)
- Does NOT purchase numbers (only attaches existing ones)
- Updates Airtable Number Inventory with Proxy Phone SID
- Logs event to Audit Log

---

## Endpoints To Be Implemented

### POST /numbers/purchase

**Purpose**: Purchase a new phone number from Twilio and add to inventory

**Used By**: Zaps 2, 4, 5

**Priority**: 🚨 High (required for Zaps 2, 4, 5 to function)

**Request**:
```http
POST /numbers/purchase
Content-Type: application/json

{
  "lifecycle": "pool",
  "area_code": "303",
  "sitter_id": "recXXXXXXXXXXXXXX"
}
```

**Request Fields**:
- `lifecycle` (required): `"pool"`, `"reserved"`, or `"standby"`
- `area_code` (required): `"303"` or `"720"` (Colorado area codes)
- `sitter_id` (optional): Only for `lifecycle="reserved"`, links to sitter

**Response** (Success):
```json
{
  "success": true,
  "phone_number": "+13035551234",
  "number_inventory_id": "recXXXXXXXXXXXXXX",
  "status": "pending",
  "twilio_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Response** (Error):
```json
{
  "success": false,
  "error": "No available numbers in area code 303",
  "details": "..."
}
```

**Implementation Requirements**:
1. Use Twilio API to search for available local numbers
   - `client.available_phone_numbers('US').local.list(area_code=303)`
2. Purchase the first available number
   - `client.incoming_phone_numbers.create(phone_number=number)`
3. Create Airtable Number Inventory record
   - Fields: Phone Number, Lifecycle, Status=Pending, Purchased At
4. Link to sitter if `sitter_id` provided
5. Return phone number and Airtable record ID
6. DO NOT attach to Proxy (Zap 3 handles that)

**Related Code**:
- New function in `services/twilio_proxy.py`: `search_and_purchase_number(area_code)`
- New endpoint in `routers/numbers.py`: `POST /numbers/purchase`
- See [ISSUE_ANALYSIS.md](../ISSUE_ANALYSIS.md) #1 for details

---

### POST /inventory/check-and-replenish

**Purpose**: Check pool utilization and purchase if needed (all-in-one endpoint for Zap 4)

**Used By**: Zap 4

**Priority**: 🟡 Medium (nice-to-have, Zap 4 can use `/numbers/purchase` instead)

**Request**:
```http
POST /inventory/check-and-replenish
Content-Type: application/json

{
  "threshold": 0.87,
  "cooldown_hours": 72
}
```

**Request Fields**:
- `threshold` (optional): Utilization threshold, default 0.87
- `cooldown_hours` (optional): Minimum hours between purchases, default 72

**Response** (Purchase Made):
```json
{
  "success": true,
  "action": "purchased",
  "utilization_rate": 0.90,
  "ready_pool_count": 10,
  "active_sessions": 9,
  "phone_number": "+13035551234",
  "number_inventory_id": "recXXXXXXXXXXXXXX"
}
```

**Response** (No Purchase Needed):
```json
{
  "success": true,
  "action": "none",
  "utilization_rate": 0.50,
  "ready_pool_count": 20,
  "active_sessions": 10,
  "reason": "Utilization below threshold"
}
```

**Implementation Requirements**:
1. Count ready pool numbers from Airtable
2. Count active sessions (from Twilio Proxy or Airtable)
3. Calculate utilization rate
4. Check cooldown period (last pool purchase timestamp)
5. If threshold met and cooldown expired: call `/numbers/purchase`
6. Return utilization metrics and purchase result

**Alternative**: Zap 4 can perform these checks itself and call `/numbers/purchase` directly

---

### POST /numbers/standby-replenish

**Purpose**: Purchase one standby reserved number (simplified endpoint for Zap 5)

**Used By**: Zap 5

**Priority**: 🟡 Medium (nice-to-have, Zap 5 can use `/numbers/purchase` instead)

**Request**:
```http
POST /numbers/standby-replenish
Content-Type: application/json

{
  "area_code": "303"
}
```

**Response** (Success):
```json
{
  "success": true,
  "phone_number": "+13035551234",
  "number_inventory_id": "recXXXXXXXXXXXXXX",
  "status": "pending"
}
```

**Implementation Requirements**:
1. Call `/numbers/purchase` with `lifecycle="standby"`
2. Return result

**Alternative**: Zap 5 can call `/numbers/purchase` directly with `lifecycle="standby"`

---

### GET /sessions/active-count

**Purpose**: Get count of active Proxy sessions (for Zap 4 utilization calculation)

**Used By**: Zap 4

**Priority**: 🟢 Low (Zap 4 can count from Airtable Audit Log instead)

**Request**:
```http
GET /sessions/active-count
```

**Response**:
```json
{
  "active_sessions": 15,
  "total_sessions": 42,
  "timestamp": "2025-12-11T21:00:00Z"
}
```

**Implementation Requirements**:
1. Query Twilio Proxy API for active sessions
   - `proxy_service.sessions.list(status='open')`
2. Count results
3. Return count

**Alternative**: Zap 4 can count active sessions from Airtable Audit Log using filter formula

---

## Common Error Responses

All endpoints should return consistent error responses:

**400 Bad Request** (Invalid input):
```json
{
  "success": false,
  "error": "Missing required field: area_code",
  "details": "..."
}
```

**422 Unprocessable Entity** (Validation error):
```json
{
  "success": false,
  "error": "Invalid phone number format",
  "details": "Phone number must be in E.164 format (+1XXXXXXXXXX)"
}
```

**500 Internal Server Error** (Server error):
```json
{
  "success": false,
  "error": "Twilio API error",
  "details": "Account balance too low to purchase number"
}
```

---

## Request Format Notes

### Zapier Compatibility

The Railway server supports multiple request formats for Zapier compatibility:

**JSON** (preferred):
```http
Content-Type: application/json

{"sitter_id": "recXXX", "phone_number": "+13035551234"}
```

**Form-Encoded**:
```http
Content-Type: application/x-www-form-urlencoded

sitter_id=recXXX&phone_number=%2B13035551234
```

**Query Parameters**:
```http
POST /attach-number?sitter_id=recXXX&phone_number=%2B13035551234
```

The `utils/request_parser.py` module handles all three formats automatically.

### Field Name Normalization

Zapier sometimes sends field names with spaces or different casing. The server normalizes these:

- `"Sitter ID"` → `"sitter_id"`
- `"Phone Number"` → `"phone_number"`
- `"AreaCode"` → `"area_code"`

See `routers/numbers.py` line 73 for implementation.

---

## Testing Endpoints

### Using curl

**Test /attach-number**:
```bash
curl -X POST https://your-railway-app.railway.app/attach-number \
  -H "Content-Type: application/json" \
  -d '{"sitter_id":"recXXXXXXXXXXXXXX","phone_number":"+13035551234"}'
```

**Test /numbers/purchase** (when implemented):
```bash
curl -X POST https://your-railway-app.railway.app/numbers/purchase \
  -H "Content-Type: application/json" \
  -d '{"lifecycle":"pool","area_code":"303"}'
```

### Using Zapier Test Mode

1. In Zapier, add "Webhooks by Zapier" action
2. Select "POST"
3. Enter endpoint URL
4. Set payload type to "JSON"
5. Enter request body
6. Click "Test & Continue"
7. Verify response matches expected schema

---

## Rate Limits

**Current**: No rate limits implemented

**Recommended** (for production):
- 100 requests per minute per IP
- 1000 requests per hour per IP
- Implement using FastAPI middleware or Railway rate limiting

---

## Monitoring

**Logs**: Railway automatically captures stdout/stderr

**Recommended Logging**:
- Log all endpoint calls with timestamp, payload, response
- Log Twilio API calls and responses
- Log Airtable updates
- Use structured logging (JSON format)

**Example Log Entry**:
```json
{
  "timestamp": "2025-12-11T21:00:00Z",
  "endpoint": "/attach-number",
  "method": "POST",
  "payload": {"sitter_id": "recXXX"},
  "response": {"success": true},
  "duration_ms": 234
}
```

---

## Security Recommendations

1. **API Key Authentication**: Add `X-API-Key` header requirement
2. **IP Whitelisting**: Only allow Zapier and Twilio IPs
3. **Rate Limiting**: Prevent abuse
4. **Input Validation**: Strict validation of all inputs
5. **HTTPS Only**: Enforce HTTPS (Railway does this by default)
6. **Secrets Management**: Use Railway environment variables for sensitive data

---

## Related Documentation

- [PROJECT_REQUIREMENTS.md](../PROJECT_REQUIREMENTS.md): Overall project requirements
- [ISSUE_ANALYSIS.md](../ISSUE_ANALYSIS.md): Known gaps and implementation needs
- [ZAP_PROMPTS.README.md](ZAP_PROMPTS.README.md): Zapier automation overview
- [extras/COMPLETE_TEST_GUIDE.md](../extras/COMPLETE_TEST_GUIDE.md): Testing procedures
