# Zap 1: Client Sync

## Purpose

Automatically synchronize client data from Time to Pet into the Airtable Clients table. This ensures that when clients are created or updated in Time to Pet, their information (including phone numbers) is immediately available in the Phone Masking system.

## Trigger Configuration

**App**: Time to Pet  
**Trigger Event**: New or Updated Client  
**Trigger Type**: Webhook (Catch Hook)

### Setup Steps

1. In Zapier, add trigger "Webhooks by Zapier"
2. Select "Catch Hook"
3. Copy the webhook URL provided by Zapier
4. In Time to Pet admin panel:
   - Navigate to Settings → Webhooks
   - Create new webhook for "Client Created" event
   - Create new webhook for "Client Updated" event
   - Paste Zapier webhook URL into both
   - Enable webhooks

### Expected Webhook Payload

Time to Pet will send JSON data in this format:

```json
{
  "event": "client.created",
  "client_id": "ttp_12345",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "3035551234",
  "address": "123 Main St, Denver, CO 80202",
  "created_at": "2025-12-11T10:30:00Z",
  "updated_at": "2025-12-11T10:30:00Z"
}
```

## Filter Logic

**Filter by Zapier** - Only continue if phone number is valid

**Condition**:
- Field: `phone` (from trigger)
- Condition: `exists` AND `is not empty`
- Additional check: `text length is greater than 9`

This prevents creating client records without valid phone numbers.

## Data Transformation

### Step 1: Format Phone Number to E.164

**App**: Formatter by Zapier  
**Transform**: Numbers → Format Phone Number  

**Configuration**:
- Input: `{{phone}}` (from trigger)
- To Format: E.164
- Default Country: US (+1)

**Output**: `+13035551234`

> [!IMPORTANT]
> E.164 format is REQUIRED for Twilio Proxy. All phone numbers must start with `+1` for US numbers.

### Step 2: Combine First and Last Name

**App**: Formatter by Zapier  
**Transform**: Text → Split Text

**Configuration**:
- Input: `{{first_name}} {{last_name}}`
- Separator: (leave blank for simple concatenation)

**Output**: `John Doe`

## Action: Upsert Client in Airtable

**App**: Airtable  
**Action**: Find or Create Record  

### Configuration

**Base**: Phone Masking  
**Table**: Clients  

**Search Field**: `Time to Pet ID`  
**Search Value**: `{{client_id}}` (from trigger)

**Field Mappings** (if creating new record):

| Airtable Field | Zapier Value | Notes |
|----------------|--------------|-------|
| Time to Pet ID | `{{client_id}}` | Unique identifier from Time to Pet |
| Client Name | `{{first_name}} {{last_name}}` | Combined name |
| Client Phone (E.164) | `{{formatted_phone}}` | From Formatter step |
| Email | `{{email}}` | Direct mapping |
| Address | `{{address}}` | Optional field |
| Created At | `{{created_at}}` | Timestamp from Time to Pet |
| Last Synced | `{{zap_meta_human_now}}` | Current timestamp |

**Update Behavior**: If record exists (matching Time to Pet ID):
- Update all fields EXCEPT `Time to Pet ID` and `Created At`
- This ensures client data stays in sync with Time to Pet

## Error Handling

### Duplicate Prevention

The "Find or Create Record" action uses `Time to Pet ID` as the unique identifier. This prevents duplicate client records even if:
- The same client is synced multiple times
- Client updates their phone number in Time to Pet
- Webhook fires multiple times for the same event

### Missing Phone Number

If the phone number is missing or invalid:
- Filter step will stop the Zap
- No Airtable record will be created
- Zap History will show "Filtered" status (not an error)

### Invalid E.164 Conversion

If Formatter cannot convert phone to E.164:
- Zap will error at the Formatter step
- Check Zap History for the invalid phone number
- Manually correct in Time to Pet and re-sync

## Testing Scenarios

### Test 1: New Client Creation

**Input** (simulate webhook):
```json
{
  "client_id": "ttp_test_001",
  "first_name": "Test",
  "last_name": "Client",
  "phone": "7205551234",
  "email": "test@example.com"
}
```

**Expected Output**:
- New record created in Airtable Clients table
- `Client Phone (E.164)` = `+17205551234`
- `Client Name` = `Test Client`
- `Time to Pet ID` = `ttp_test_001`

### Test 2: Client Update (Phone Change)

**Input**:
```json
{
  "client_id": "ttp_test_001",
  "first_name": "Test",
  "last_name": "Client",
  "phone": "3035559999",
  "email": "test@example.com"
}
```

**Expected Output**:
- Existing record updated (not duplicated)
- `Client Phone (E.164)` = `+13035559999`
- `Last Synced` timestamp updated

### Test 3: Missing Phone Number (Filtered)

**Input**:
```json
{
  "client_id": "ttp_test_002",
  "first_name": "No",
  "last_name": "Phone",
  "phone": "",
  "email": "nophone@example.com"
}
```

**Expected Output**:
- Zap stops at Filter step
- No Airtable record created
- Zap History shows "Filtered" (not error)

## Validation Checklist

After building this Zap:

- [ ] Webhook URL configured in Time to Pet for both "Created" and "Updated" events
- [ ] Filter step prevents empty phone numbers
- [ ] Formatter converts phone to E.164 format
- [ ] Airtable action uses "Find or Create Record" (not "Create Record")
- [ ] Search field is set to "Time to Pet ID"
- [ ] All required fields are mapped correctly
- [ ] Test with sample webhook payload shows successful record creation
- [ ] Test with duplicate client_id shows update (not duplicate)
- [ ] Zap is enabled and monitoring webhook

## Codebase Integration

**Railway Endpoints**: None (this Zap is Airtable-only)

**Related Tables**:
- Airtable: Clients table

**Dependencies**:
- Time to Pet webhook must be configured
- Airtable base must have Clients table with correct schema

## Notes

- This Zap runs independently of the Railway server
- Client records created here are used by the Out-of-Session handler when clients text sitters
- If a client texts a sitter BEFORE Time to Pet syncs them, the Out-of-Session handler will create a "shell" client record (see `routers/sessions.py`)
- The upsert logic here will fill in the missing details when Time to Pet eventually syncs

## Troubleshooting

**Issue**: Duplicate clients with different Time to Pet IDs  
**Solution**: Check if Time to Pet is sending different IDs for the same client (contact Time to Pet support)

**Issue**: Phone numbers not converting to E.164  
**Solution**: Verify Default Country is set to "US" in Formatter step

**Issue**: Webhook not triggering  
**Solution**: Check Time to Pet webhook configuration and test with their "Send Test Webhook" feature
