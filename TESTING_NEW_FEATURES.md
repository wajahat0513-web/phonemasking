# Testing Guide: New Implementation

## Overview

This guide covers testing for the newly implemented features:
- Number purchasing from Twilio
- Message prepending in intercept
- Client deduplication

## Prerequisites

1. **Python Environment Setup**:
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate (Windows)
   .venv\Scripts\activate
   
   # Activate (Linux/Mac)
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Ensure `.env` file has all required credentials:
   ```env
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PROXY_SERVICE_SID=your_proxy_service_sid
   AIRTABLE_BASE_ID=your_base_id
   AIRTABLE_API_KEY=your_api_key
   ```

---

## Test 1: Server Startup

**Purpose**: Verify all code changes compile and server starts without errors

**Steps**:
```bash
# Start the server
python main.py
```

**Expected Output**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

**Validation**:
- ✅ No import errors
- ✅ No syntax errors
- ✅ Server starts on port 8080
- ✅ Access http://localhost:8080/docs shows Swagger UI

---

## Test 2: Number Purchasing Endpoint

**Purpose**: Test the new `/numbers/purchase` endpoint

### Test 2a: Purchase Pool Number

**Request**:
```bash
curl -X POST http://localhost:8080/numbers/purchase \
  -H "Content-Type: application/json" \
  -d '{
    "lifecycle": "pool",
    "area_code": "303"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "phone_number": "+13035551234",
  "number_inventory_id": "recXXXXXXXXXXXXXX",
  "status": "pending",
  "twilio_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Validation**:
- ✅ Number purchased from Twilio (check Twilio Console)
- ✅ Airtable Number Inventory record created
- ✅ Lifecycle = "Pool"
- ✅ Status = "Pending"
- ✅ Twilio SID populated
- ✅ Audit Log entry created

### Test 2b: Purchase Reserved Number with Sitter

**Request**:
```bash
curl -X POST http://localhost:8080/numbers/purchase \
  -H "Content-Type: application/json" \
  -d '{
    "lifecycle": "reserved",
    "area_code": "303",
    "sitter_id": "recYOUR_SITTER_ID"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "phone_number": "+13035559999",
  "number_inventory_id": "recXXXXXXXXXXXXXX",
  "status": "pending",
  "twilio_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Validation**:
- ✅ Number purchased from Twilio
- ✅ Airtable record created with Lifecycle = "Reserved Active"
- ✅ Assigned Sitter field linked to sitter
- ✅ Audit Log entry created

### Test 2c: Purchase Standby Number

**Request**:
```bash
curl -X POST http://localhost:8080/numbers/purchase \
  -H "Content-Type: application/json" \
  -d '{
    "lifecycle": "standby",
    "area_code": "720"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "phone_number": "+17205551234",
  "number_inventory_id": "recXXXXXXXXXXXXXX",
  "status": "pending",
  "twilio_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Validation**:
- ✅ Number purchased from Twilio
- ✅ Lifecycle = "Standby Reserved"
- ✅ No sitter assigned

### Test 2d: Error Handling - Invalid Lifecycle

**Request**:
```bash
curl -X POST http://localhost:8080/numbers/purchase \
  -H "Content-Type: application/json" \
  -d '{
    "lifecycle": "invalid",
    "area_code": "303"
  }'
```

**Expected Response**:
```json
{
  "detail": [
    {
      "type": "value_error",
      "msg": "Value error, lifecycle must be one of ['pool', 'reserved', 'standby']"
    }
  ]
}
```

**Validation**:
- ✅ Returns 422 Unprocessable Entity
- ✅ Clear error message

---

## Test 3: Attach Number with Proxy Integration

**Purpose**: Test updated `/attach-number` endpoint now adds numbers to Proxy

**Setup**:
1. Create a number in Airtable Number Inventory (manually or via Test 2)
2. Have a sitter record ready

**Request**:
```bash
curl -X POST http://localhost:8080/attach-number \
  -H "Content-Type: application/json" \
  -d '{
    "sitter_id": "recYOUR_SITTER_ID"
  }'
```

**Expected Response**:
```json
{
  "status": "success",
  "new_number": "+13035551234"
}
```

**Validation**:
- ✅ Number assigned to sitter in Airtable
- ✅ Number added to Twilio Proxy Service (check Twilio Console → Proxy → Phone Numbers)
- ✅ Airtable Number Inventory updated with:
  - Proxy Phone SID populated
  - Attach Status = "Ready"
- ✅ Audit Log entry created

---

## Test 4: Message Prepending (Intercept)

**Purpose**: Test that client names are prepended to messages

**Setup**:
1. Create a test client in Airtable with Name = "John Doe"
2. Create an active Proxy session

**Simulate Intercept Webhook**:
```bash
curl -X POST http://localhost:8080/intercept \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=+13035551234&To=+17205559999&Body=Hello, can you watch my dog?&SessionSid=KCxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Expected Response**:
```json
{
  "body": "[John Doe]: Hello, can you watch my dog?"
}
```

**Validation**:
- ✅ Response includes modified body
- ✅ Client name prepended correctly
- ✅ Message logged to Airtable Messages table
- ✅ Server logs show "Prepending client name to message: John Doe"

### Test 4b: Unknown Client

**Request** (with phone not in Airtable):
```bash
curl -X POST http://localhost:8080/intercept \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=+19999999999&To=+17205559999&Body=Test message&SessionSid=KCxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Expected Response**:
```json
{
  "body": "[Unknown Client]: Test message"
}
```

**Validation**:
- ✅ Fallback to "Unknown Client" works
- ✅ No errors when client not found

---

## Test 5: Client Deduplication

**Purpose**: Test that `create_or_update_client` prevents duplicates

### Test 5a: First Contact (Create)

**Simulate Out-of-Session Webhook**:
```bash
curl -X POST http://localhost:8080/out-of-session \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=+13035559999&To=+17205551234"
```

**Expected Response**:
```json
{
  "status": "success",
  "session_sid": "KCxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Validation**:
- ✅ New client record created in Airtable
- ✅ Server logs show "Created new shell client record"
- ✅ Proxy session created
- ✅ Only ONE client record exists for this phone

### Test 5b: Second Contact (Update, Not Duplicate)

**Request** (same phone number):
```bash
curl -X POST http://localhost:8080/out-of-session \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=+13035559999&To=+17205551234"
```

**Validation**:
- ✅ No new client record created
- ✅ Existing client record updated (Last Active timestamp)
- ✅ Server logs show "Found existing client record"
- ✅ Still only ONE client record for this phone

### Test 5c: Zap 1 Sync After Shell Creation

**Scenario**: Client texts first (creates shell), then Zap 1 runs

**Steps**:
1. Out-of-session creates shell client (Test 5a)
2. Manually update client record via Airtable API (simulating Zap 1):
   ```bash
   # This would be done by Zap 1 in production
   # Manually verify in Airtable that updating the same phone number
   # doesn't create a duplicate
   ```

**Validation**:
- ✅ Only one client record exists
- ✅ Record has full details from Zap 1 (not just phone)

---

## Test 6: End-to-End Sitter Provisioning

**Purpose**: Test complete flow from purchase to attachment

**Steps**:

1. **Purchase Reserved Number**:
   ```bash
   curl -X POST http://localhost:8080/numbers/purchase \
     -H "Content-Type: application/json" \
     -d '{"lifecycle":"reserved","area_code":"303","sitter_id":"recYOUR_SITTER_ID"}'
   ```
   
   Note the `number_inventory_id` from response.

2. **Verify Pending Status**:
   - Check Airtable Number Inventory
   - Status should be "Pending"

3. **Attach to Proxy** (simulating Zap 3):
   ```bash
   curl -X POST http://localhost:8080/attach-number \
     -H "Content-Type: application/json" \
     -d '{"sitter_id":"recYOUR_SITTER_ID"}'
   ```

4. **Verify Ready Status**:
   - Check Airtable Number Inventory
   - Status should be "Ready"
   - Proxy Phone SID should be populated
   - Attach Status should be "Ready"

5. **Verify in Twilio**:
   - Go to Twilio Console → Proxy → Phone Numbers
   - Verify number appears in list

**Validation**:
- ✅ Complete flow works end-to-end
- ✅ Number purchased → pending → attached → ready
- ✅ All Airtable fields updated correctly
- ✅ Number usable in Proxy sessions

---

## Test 7: Error Scenarios

### Test 7a: No Available Numbers

**Setup**: Temporarily exhaust Twilio numbers (or use invalid area code)

**Request**:
```bash
curl -X POST http://localhost:8080/numbers/purchase \
  -H "Content-Type: application/json" \
  -d '{"lifecycle":"pool","area_code":"999"}'
```

**Expected Response**:
```json
{
  "success": false,
  "error": "No available numbers in area code 999",
  "details": "Check Twilio account balance and number availability"
}
```

**Validation**:
- ✅ Graceful error handling
- ✅ Clear error message
- ✅ No partial Airtable records created

### Test 7b: Low Twilio Balance

**Expected Behavior**: If Twilio account balance is too low, purchase fails with clear error

---

## Test 8: Zapier Integration Testing

Once local tests pass, test with actual Zapier:

### Zap 2: Sitter Provisioning

**Test Path B** (No Standby):
1. Delete all standby numbers from Airtable
2. Submit "Add New Sitter" form
3. Verify Zap calls `/numbers/purchase` with `lifecycle=reserved`
4. Verify number purchased and assigned

### Zap 4: Pool Monitor

**Test**:
1. Manually set pool utilization to 90%
2. Wait for Zap 4 to run (or trigger manually)
3. Verify Zap calls `/numbers/purchase` with `lifecycle=pool`
4. Verify pool number purchased

### Zap 5: Standby Keeper

**Test**:
1. Delete standby number
2. Wait for Zap 5 to run
3. Verify Zap calls `/numbers/purchase` with `lifecycle=standby`
4. Verify standby replenished

---

## Troubleshooting

### Issue: ModuleNotFoundError

**Solution**:
```bash
# Ensure virtual environment is activated
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Twilio API Errors

**Check**:
- Account SID and Auth Token are correct
- Proxy Service SID is correct
- Account has sufficient balance
- Numbers are available in requested area code

### Issue: Airtable Errors

**Check**:
- Base ID and API key are correct
- Table names match exactly (case-sensitive)
- Field names match schema (PhoneNumber vs Phone Number)

### Issue: Number Not Added to Proxy

**Check**:
- Number exists in Twilio account (not just purchased)
- Proxy Service SID is correct
- Number not already in another Proxy Service

---

## Success Criteria

All tests should pass with:
- ✅ No Python syntax errors
- ✅ Server starts successfully
- ✅ All endpoints return expected responses
- ✅ Airtable records created/updated correctly
- ✅ Twilio numbers purchased and added to Proxy
- ✅ Message prepending works
- ✅ Client deduplication prevents duplicates
- ✅ Zapier automations can use new endpoints

---

## Next Steps After Testing

1. **Deploy to Railway**: Push changes to production
2. **Update Zap Prompts**: Modify Zaps 2, 4, 5 to use `/numbers/purchase`
3. **Monitor Logs**: Watch for any production errors
4. **Phase 4**: Implement security (API keys, rate limiting)
