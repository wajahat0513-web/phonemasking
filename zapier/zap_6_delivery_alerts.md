# Zap 6: Delivery/Error Alerts (System Status Callback)

## Purpose

Monitor message delivery status from Twilio and handle failures intelligently:
- **Temporary failures**: Automatically retry after delay
- **Permanent failures**: Alert sitter immediately
- **Systemic issues**: Alert owner when multiple failures occur

This Zap ensures reliable message delivery and provides visibility into system health.

## Trigger Configuration

**App**: Webhooks by Zapier  
**Trigger Event**: Catch Hook  

### Setup Steps

1. In Zapier, add trigger "Webhooks by Zapier"
2. Select "Catch Hook"
3. Copy the webhook URL provided by Zapier
4. In Twilio Console:
   - Navigate to Messaging → Services → [Your Messaging Service]
   - Scroll to "Advanced Settings"
   - Set "Status Callback URL" to the Zapier webhook URL
   - Enable callbacks for: `failed`, `undelivered`
   - Save configuration

### Expected Webhook Payload

Twilio sends JSON data when a message fails:

```json
{
  "MessageSid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "MessageStatus": "failed",
  "ErrorCode": "30007",
  "ErrorMessage": "Carrier violation",
  "To": "+13035551234",
  "From": "+17205559999",
  "Body": "Hello from client",
  "AccountSid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "MessagingServiceSid": "MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Key Fields**:
- `ErrorCode`: Twilio error code (determines retry logic)
- `MessageStatus`: `failed` or `undelivered`
- `To`/`From`: Phone numbers involved
- `Body`: Message content (for logging)

## Path Logic

This Zap uses **Paths by Zapier** to handle different error types.

### Path A: Temporary Failures (Auto-Retry)

**Error Codes**: 30002, 30003, 30004, 30005, 5xx (server errors)

**Steps**:
1. Log error to Audit Log
2. Delay 10 minutes
3. Retry message via Twilio API
4. Log retry attempt

### Path B: Permanent Failures (Sitter Alert)

**Error Codes**: All others (30007, 30008, 21610, etc.)

**Steps**:
1. Log error to Audit Log
2. Send SMS alert to sitter
3. Check for systemic issues (Path C)

### Path C: Systemic Issues (Owner Alert)

**Condition**: 5+ permanent failures in last 24 hours

**Steps**:
1. Count recent failures in Audit Log
2. Send email alert to owner with failure summary

---

## Path A: Temporary Failures (Auto-Retry)

### Step 1: Filter - Temporary Error Codes

**App**: Filter by Zapier  

**Conditions** (OR logic):
- `ErrorCode` equals `30002` (Account suspended)
- `ErrorCode` equals `30003` (Unreachable destination)
- `ErrorCode` equals `30004` (Message blocked)
- `ErrorCode` equals `30005` (Unknown destination)
- `ErrorCode` starts with `5` (5xx server errors)

### Step 2: Log Temporary Failure

**App**: Airtable  
**Action**: Create Record  

**Configuration**:
- **Table**: Audit Log
- **Fields**:
  - `Event Type`: `message_failed_temporary`
  - `Details`: `Error {{ErrorCode}}: {{ErrorMessage}}`
  - `Phone Number`: `{{To}}`
  - `Message SID`: `{{MessageSid}}`
  - `Status`: `retrying`
  - `Created At`: `{{zap_meta_human_now}}`

### Step 3: Delay 10 Minutes

**App**: Delay by Zapier  
**Action**: Delay For  

**Configuration**:
- **Delay Duration**: 10 minutes

### Step 4: Retry Message

**App**: Twilio  
**Action**: Send SMS  

**Configuration**:
- **From**: `{{From}}` (original sender)
- **To**: `{{To}}` (original recipient)
- **Message**: `{{Body}}` (original message)

### Step 5: Log Retry Attempt

**App**: Airtable  
**Action**: Create Record  

**Configuration**:
- **Table**: Audit Log
- **Fields**:
  - `Event Type`: `message_retry`
  - `Details`: `Retry after error {{ErrorCode}}`
  - `Phone Number`: `{{To}}`
  - `Original Message SID`: `{{MessageSid}}`
  - `Retry Message SID`: `{{new_message_sid}}` (from Step 4)
  - `Status`: `sent`
  - `Created At`: `{{zap_meta_human_now}}`

---

## Path B: Permanent Failures (Sitter Alert)

### Step 1: Filter - Permanent Error Codes

**App**: Filter by Zapier  

**Condition**:
- `ErrorCode` does NOT match temporary codes (30002-30005, 5xx)

**Common Permanent Codes**:
- `30007`: Carrier violation (spam filter)
- `30008`: Unknown error
- `21610`: Message not sent (blacklisted number)
- `21614`: Invalid phone number

### Step 2: Log Permanent Failure

**App**: Airtable  
**Action**: Create Record  

**Configuration**:
- **Table**: Audit Log
- **Fields**:
  - `Event Type`: `message_failed_permanent`
  - `Details`: `Error {{ErrorCode}}: {{ErrorMessage}}`
  - `Phone Number`: `{{To}}`
  - `Message SID`: `{{MessageSid}}`
  - `Message Body`: `{{Body}}`
  - `Status`: `failed`
  - `Created At`: `{{zap_meta_human_now}}`

### Step 3: Identify Affected Sitter

**App**: Airtable  
**Action**: Find Record  

**Configuration**:
- **Table**: Sitters
- **Search Field**: Sitter Real Phone Number
- **Search Value**: `{{To}}` or `{{From}}` (depending on direction)

> [!NOTE]
> You may need to use Code by Zapier to determine if the sitter is the sender or recipient based on the message direction.

### Step 4: Send SMS Alert to Sitter

**App**: Twilio  
**Action**: Send SMS  

**Configuration**:
- **From**: `{{system_phone_number}}` (dedicated alert number)
- **To**: `{{sitter_real_phone}}` (from Step 3)
- **Message**:
```
ALERT: A message to/from a client failed to deliver.

Error: {{ErrorMessage}}

Please contact the client directly if urgent. For support, reply to this message.
```

---

## Path C: Systemic Issues (Owner Alert)

### Step 1: Count Recent Permanent Failures

**App**: Airtable  
**Action**: Find Records  

**Configuration**:
- **Table**: Audit Log
- **Filter Formula**:
```
AND(
  {Event Type} = "message_failed_permanent",
  DATETIME_DIFF(NOW(), {Created At}, 'hours') <= 24
)
```
- **Max Records**: 100

### Step 2: Filter - Only if 5+ Failures

**App**: Filter by Zapier  

**Condition**:
- Count of records from Step 1 is greater than or equal to `5`

### Step 3: Send Owner Alert Email

**App**: Gmail  
**Action**: Send Email  

**Configuration**:
- **To**: `{{owner_email}}`
- **Subject**: `URGENT: Multiple Message Delivery Failures`
- **Body**: (See email template in ZAP_PROMPTS.README.md)

**Dynamic Fields**:
- `{{failure_count}}`: Count from Step 1
- `{{recent_failures}}`: List of last 5 failures with error codes

---

## Testing Scenarios

### Test 1: Temporary Failure (Auto-Retry)

**Input** (simulate webhook):
```json
{
  "MessageSid": "SM_test_001",
  "MessageStatus": "failed",
  "ErrorCode": "30003",
  "ErrorMessage": "Unreachable destination handset",
  "To": "+13035551234",
  "From": "+17205559999",
  "Body": "Test message"
}
```

**Expected Results**:
- Path A triggered
- Audit Log entry created (event_type: message_failed_temporary)
- 10-minute delay
- Message retried via Twilio
- Retry logged in Audit Log

### Test 2: Permanent Failure (Sitter Alert)

**Input**:
```json
{
  "MessageSid": "SM_test_002",
  "MessageStatus": "failed",
  "ErrorCode": "30007",
  "ErrorMessage": "Carrier violation",
  "To": "+13035551234",
  "From": "+17205559999",
  "Body": "Test message"
}
```

**Expected Results**:
- Path B triggered
- Audit Log entry created (event_type: message_failed_permanent)
- Sitter identified from phone number
- SMS alert sent to sitter
- No retry attempted

### Test 3: Systemic Issue (Owner Alert)

**Setup**:
1. Create 5+ permanent failure records in Audit Log (within 24 hours)
2. Trigger Zap with another permanent failure

**Expected Results**:
- Path B triggered (permanent failure)
- Path C also triggered (systemic check)
- Owner email sent with failure summary
- Email includes list of recent failures

---

## Validation Checklist

- [ ] Webhook URL configured in Twilio Messaging Service
- [ ] Twilio callbacks enabled for `failed` and `undelivered` statuses
- [ ] Path A filter includes all temporary error codes
- [ ] Path B filter excludes temporary error codes
- [ ] Delay set to exactly 10 minutes (not 10 hours!)
- [ ] Retry uses original message content and phone numbers
- [ ] Sitter lookup correctly identifies affected sitter
- [ ] SMS alert message is clear and actionable
- [ ] Systemic check counts failures in last 24 hours
- [ ] Owner email includes failure details
- [ ] Test with temporary error code (30003)
- [ ] Test with permanent error code (30007)
- [ ] Test systemic alert with 5+ failures
- [ ] Zap enabled and monitoring

## Codebase Integration

**Railway Endpoints**: None (this Zap uses direct Twilio/Airtable integration)

**Twilio Configuration**:
- Status Callback URL must be set in Twilio Messaging Service
- Callbacks must be enabled for `failed` and `undelivered` events
- System phone number needed for sitter alerts (can be any Twilio number)

**Related Tables**:
- Airtable: Audit Log, Sitters

**Related Files**:
- No Railway code changes needed
- This Zap operates independently of the Railway server

## Notes

- This Zap provides critical visibility into message delivery issues
- Auto-retry for temporary failures improves reliability
- Sitter alerts ensure they know when messages fail
- Owner alerts detect systemic problems (Twilio outages, account issues)
- Only retries once (prevents infinite retry loops)
- Audit Log provides complete failure history for debugging

## Troubleshooting

**Issue**: Zap not triggering for failed messages  
**Solution**: Verify Status Callback URL is set in Twilio Messaging Service and callbacks are enabled

**Issue**: Retry loop (message keeps failing and retrying)  
**Solution**: Ensure only ONE retry attempt (no loop back to Path A after retry)

**Issue**: Sitter lookup fails  
**Solution**: Verify phone numbers in Sitters table are in E.164 format matching Twilio's format

**Issue**: Too many owner alerts  
**Solution**: Adjust systemic threshold from 5 to higher number (e.g., 10)

**Issue**: Temporary failures not retrying  
**Solution**: Check Path A filter includes all temporary error codes (30002-30005, 5xx)

## Error Code Reference

**Temporary (Auto-Retry)**:
- `30002`: Account suspended
- `30003`: Unreachable destination
- `30004`: Message blocked
- `30005`: Unknown destination
- `5xx`: Twilio server errors

**Permanent (Alert Only)**:
- `30007`: Carrier violation (spam filter)
- `30008`: Unknown error
- `21610`: Message not sent (blacklisted)
- `21614`: Invalid phone number
- `21408`: Permission to send denied

For complete error code list, see [Twilio Error Code Documentation](https://www.twilio.com/docs/api/errors).
