# Zap 3: Number Attach Verification

## Purpose

Verify that newly purchased phone numbers are successfully attached to the Twilio Proxy Service and ready for use. This Zap completes the provisioning process started by Zaps 2, 4, and 5 by:
1. Calling the Railway API to attach the number to Proxy
2. Sending a test SMS to verify the number works
3. Updating the Number Inventory status to "Ready"
4. Sending confirmation email if the number is assigned to a sitter

## Trigger Configuration

**App**: Airtable  
**Trigger Event**: Updated Record in View  

### Setup Steps

1. **Base**: Phone Masking
2. **Table**: Number Inventory
3. **View**: Create a new view called "Pending Verification"
   - Filter: `Status` = "Pending"
4. **Trigger Field**: Status (triggers when Status changes to "Pending")

> [!NOTE]
> This Zap is triggered by Zaps 2, 4, and 5 when they create Number Inventory records with Status="Pending".

## Step-by-Step Configuration

### Step 1: Call Railway Attach-Number Endpoint

**App**: Webhooks by Zapier  
**Action**: POST Request  

**Configuration**:
- **URL**: `https://your-railway-app.railway.app/attach-number`
- **Method**: POST
- **Headers**:
  - `Content-Type`: `application/json`
- **Body** (JSON):
```json
{
  "sitter_id": "{{assigned_to_record_id}}",
  "phone_number": "{{phone_number}}"
}
```

**Field Mapping**:
- `sitter_id`: From trigger → Assigned To (linked record ID)
  - **Note**: This may be empty for Pool or Standby numbers
- `phone_number`: From trigger → Phone Number field

**Expected Response** (Success):
```json
{
  "success": true,
  "message": "Number attached successfully",
  "phone_number": "+13035551234",
  "proxy_phone_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Expected Response** (Error):
```json
{
  "success": false,
  "error": "Number already attached to Proxy",
  "details": "..."
}
```

### Step 2: Filter - Only Continue if Attach Succeeded

**App**: Filter by Zapier  

**Condition**:
- Field: `success` (from Step 1 response)
- Condition: `equals` `true`

This prevents updating Airtable if the attach failed.

### Step 3: Send Test SMS

**App**: Twilio  
**Action**: Send SMS  

**Configuration**:
- **From**: `{{phone_number}}` (the number being verified)
- **To**: `{{owner_phone}}` (hardcoded owner number, e.g., +13035550000)
- **Message**: `Test message from {{phone_number}}. This number is now active in the Phone Masking system.`

**Purpose**: Confirms the number can send messages through Twilio

> [!TIP]
> If you don't want to receive test SMS for every number, you can skip this step and rely on the Railway API response.

### Step 4: Update Number Inventory Status

**App**: Airtable  
**Action**: Update Record  

**Configuration**:
- **Table**: Number Inventory
- **Record ID**: `{{trigger_record_id}}` (from trigger)
- **Fields to Update**:
  - `Status`: `Ready`
  - `Proxy Phone SID`: `{{proxy_phone_sid}}` (from Step 1)
  - `Verified At`: `{{zap_meta_human_now}}`
  - `Last Test`: `{{zap_meta_human_now}}`

### Step 5: Check if Number is Assigned to Sitter

**App**: Filter by Zapier  

**Condition**:
- Field: `Lifecycle` (from trigger)
- Condition: `equals` `Reserved Active`

This filter ensures we only send emails for sitter numbers, not pool/standby numbers.

### Step 6: Update Sitter Status to Active

**App**: Airtable  
**Action**: Update Record  

**Configuration**:
- **Table**: Sitters
- **Record ID**: `{{assigned_to_record_id}}` (from trigger)
- **Fields to Update**:
  - `Status`: `Active`
  - `Activated At`: `{{zap_meta_human_now}}`

### Step 7: Send Sitter Activation Email

**App**: Gmail  
**Action**: Send Email  

**Configuration**:
- **To**: `{{owner_email}}`
- **Subject**: `Sitter Activated: {{sitter_name}}`
- **Body**:
```
Sitter successfully activated!

Name: {{sitter_name}}
Masked Number: {{phone_number}}
Status: Active

The sitter can now receive client messages through the masked number.

View Sitter: {{sitter_record_url}}
```

**Dynamic Fields**:
- `{{sitter_name}}`: Lookup from Sitters table using `{{assigned_to_record_id}}`
- `{{phone_number}}`: From trigger
- `{{sitter_record_url}}`: Airtable record URL

---

## Error Handling

### Attach Failed (Step 2 Filter)

If the Railway API returns `success: false`:
- Zap stops at Filter step
- Number Inventory Status remains "Pending"
- No email sent

**Manual Resolution**:
1. Check Railway server logs for error details
2. Verify number is valid and not already in Proxy
3. Manually update Status to "Pending" to re-trigger Zap

### Test SMS Failed (Step 3)

If Twilio cannot send test SMS:
- Zap will error at Step 3
- Check Twilio error code in Zap History
- Common issues:
  - Number not yet provisioned in Twilio
  - Owner phone number invalid
  - Twilio account balance too low

**Workaround**: Skip Step 3 (test SMS) if not critical

### Sitter Lookup Failed (Step 6)

If `assigned_to_record_id` is empty (pool/standby numbers):
- Step 5 filter will stop the Zap
- No sitter update or email sent
- This is expected behavior

---

## Testing Scenarios

### Test 1: Reserved Number Verification (Sitter)

**Setup**:
1. Create Number Inventory record:
   - Phone Number: `+13035551234`
   - Lifecycle: `Reserved Active`
   - Status: `Pending`
   - Assigned To: (link to test sitter)

**Expected Results**:
- Railway API called successfully
- Test SMS sent to owner
- Number Inventory Status = `Ready`
- Sitter Status = `Active`
- Activation email sent

### Test 2: Pool Number Verification

**Setup**:
1. Create Number Inventory record:
   - Phone Number: `+17205551234`
   - Lifecycle: `Pool`
   - Status: `Pending`
   - Assigned To: (empty)

**Expected Results**:
- Railway API called successfully
- Number Inventory Status = `Ready`
- No sitter update (Step 5 filter stops Zap)
- No email sent

### Test 3: Attach Failure

**Setup**:
1. Create Number Inventory record with invalid phone number
2. Set Status to `Pending`

**Expected Results**:
- Railway API returns `success: false`
- Step 2 filter stops Zap
- Number Inventory Status remains `Pending`
- Check Zap History for error details

---

## Validation Checklist

- [ ] Trigger view "Pending Verification" created in Number Inventory
- [ ] Railway endpoint URL is correct
- [ ] Filter after API call checks `success` field
- [ ] Test SMS step configured (or skipped if not needed)
- [ ] Airtable update sets Status to "Ready"
- [ ] Sitter filter checks Lifecycle = "Reserved Active"
- [ ] Email template includes all dynamic fields
- [ ] Test with Reserved, Pool, and Standby numbers
- [ ] Verify error handling for failed attachments
- [ ] Zap enabled and monitoring

## Codebase Integration

**Railway Endpoints**:
- `POST /attach-number`
  - **Status**: ✅ Implemented in `routers/numbers.py`
  - **Required Payload**:
    ```json
    {
      "sitter_id": "recXXXXXXXXXXXXXX",  // Optional for pool/standby
      "phone_number": "+13035551234"      // Optional, can use sitter lookup
    }
    ```
  - **Response**:
    ```json
    {
      "success": true,
      "message": "Number attached successfully",
      "phone_number": "+13035551234",
      "proxy_phone_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
    ```

**Related Files**:
- `routers/numbers.py`: `/attach-number` endpoint implementation
- `services/twilio_proxy.py`: Proxy Service integration
- `services/airtable_client.py`: Number Inventory updates

**Related Tables**:
- Airtable: Number Inventory, Sitters

## Notes

- This Zap is the final step in number provisioning
- It's triggered by Zaps 2 (sitter provisioning), 4 (pool purchase), and 5 (standby replenishment)
- The Railway API handles the actual Twilio Proxy attachment
- Test SMS is optional but recommended for initial setup
- Email notifications only sent for sitter numbers (not pool/standby)

## Troubleshooting

**Issue**: Zap triggers but Railway API returns 422 error  
**Solution**: Check that `phone_number` is in E.164 format and `sitter_id` is valid Airtable record ID

**Issue**: Number shows "Ready" but sitter still "Pending"  
**Solution**: Check Step 5 filter - ensure Lifecycle is exactly "Reserved Active" (case-sensitive)

**Issue**: Multiple Zap runs for same number  
**Solution**: Ensure trigger is "Updated Record" not "New or Updated Record" to avoid duplicate processing
