# Zap 5: Standby Keeper

## Purpose

Ensure there is always exactly one Standby Reserved number available in the inventory. This number is used by Zap 2 (Sitter Provisioning) to instantly assign numbers to new sitters without waiting for Twilio API calls.

## Trigger Configuration

**App**: Schedule by Zapier  
**Trigger Event**: Every 48 Hours  

### Setup Steps

1. Select "Schedule by Zapier"
2. Choose "Every X Hours"
3. Set interval to **48 hours**
4. Set start time (e.g., 3:00 AM, offset from Zap 4)

> [!TIP]
> Schedule this Zap to run at a different time than Zap 4 to distribute API load.

## Step-by-Step Configuration

### Step 1: Count Standby Reserved Numbers

**App**: Airtable  
**Action**: Find Records  

**Configuration**:
- **Table**: Number Inventory
- **Filter Formula**:
```
AND(
  {Lifecycle} = "Standby Reserved",
  {Status} = "Ready"
)
```
- **Max Records**: 5 (should only ever be 0 or 1)

**Output**: List of standby reserved numbers

### Step 2: Count Standby Numbers (Code)

**App**: Code by Zapier  
**Action**: Run Python  

**Input Data**:
- `standby_numbers`: `{{step1_records}}` (array from Step 1)

**Code**:
```python
# Count standby reserved numbers
standby_numbers = input_data.get('standby_numbers', [])
standby_count = len(standby_numbers)

output = {
    'standby_count': standby_count,
    'needs_replenishment': standby_count == 0
}
```

**Output**:
- `standby_count`: Integer (should be 0 or 1)
- `needs_replenishment`: Boolean (true if count is 0)

### Step 3: Filter - Only Continue if Standby is Missing

**App**: Filter by Zapier  

**Condition**:
- Field: `needs_replenishment` (from Step 2)
- Condition: `equals` `true`

This ensures we only purchase when standby is actually missing.

### Step 4: Check for Pending Standby Numbers

**App**: Airtable  
**Action**: Find Records  

**Configuration**:
- **Table**: Number Inventory
- **Filter Formula**:
```
AND(
  {Lifecycle} = "Standby Reserved",
  {Status} = "Pending"
)
```
- **Max Records**: 5

**Purpose**: Prevent duplicate purchases if a standby is already being provisioned

### Step 5: Filter - Only Continue if No Pending Standby

**App**: Filter by Zapier  

**Condition**:
- Field: Count of records from Step 4
- Condition: `equals` `0`

This prevents purchasing multiple standby numbers simultaneously.

### Step 6: Purchase New Standby Number

**App**: Webhooks by Zapier  
**Action**: POST Request  

**Configuration**:
- **URL**: `https://your-railway-app.railway.app/numbers/standby-replenish`
- **Method**: POST
- **Headers**:
  - `Content-Type`: `application/json`
- **Body** (JSON):
```json
{
  "lifecycle": "standby",
  "area_code": "303"
}
```

> [!WARNING]
> This endpoint is NOT YET IMPLEMENTED. See ENDPOINTS_REFERENCE.md for implementation requirements.

**Alternative Endpoint** (also needs implementation):
```
POST /numbers/purchase
{
  "lifecycle": "standby",
  "area_code": "303"
}
```

**Expected Response**:
```json
{
  "success": true,
  "phone_number": "+13035551234",
  "number_inventory_id": "recXXXXXXXXXXXXXX",
  "status": "pending"
}
```

### Step 7: Create Number Inventory Record

**App**: Airtable  
**Action**: Create Record  

**Configuration**:
- **Table**: Number Inventory
- **Fields**:
  - `Phone Number`: `{{phone_number}}` (from Step 6)
  - `Lifecycle`: `Standby Reserved`
  - `Status`: `Pending`
  - `Purchased At`: `{{zap_meta_human_now}}`
  - `Purchase Reason`: `Standby replenishment (auto)`

> [!NOTE]
> This record will trigger Zap 3 (Number Verification) to complete the attachment and set Status to "Ready".

### Step 8: Log Replenishment Event

**App**: Airtable  
**Action**: Create Record  

**Configuration**:
- **Table**: Audit Log
- **Fields**:
  - `Event Type`: `standby_replenishment`
  - `Details`: `Auto-purchased standby reserved number`
  - `Phone Number`: `{{phone_number}}`
  - `Status`: `success`
  - `Created At`: `{{zap_meta_human_now}}`

### Step 9: Send Notification Email (Optional)

**App**: Gmail  
**Action**: Send Email  

**Configuration**:
- **To**: `{{owner_email}}`
- **Subject**: `Standby Number Replenished`
- **Body**:
```
Standby reserved number has been automatically replenished.

New Standby Number: {{phone_number}}
Status: Pending verification

This number will be used for the next new sitter.

View Inventory: [Airtable Number Inventory URL]
```

> [!TIP]
> This email is optional. You may want to disable it to reduce notification noise.

---

## Testing Scenarios

### Test 1: No Standby Available (Purchase Triggered)

**Setup**:
1. Manually delete or assign the standby reserved number
2. Ensure no pending standby numbers exist
3. Wait for scheduled trigger or manually run Zap

**Expected Results**:
- Standby count = 0
- Filter passes (needs_replenishment = true)
- Railway API called to purchase standby number
- Number Inventory record created (Status=Pending)
- Audit Log entry created
- Zap 3 triggered to verify new number
- Optional email sent

### Test 2: Standby Already Exists (No Purchase)

**Setup**:
- Ensure 1 standby reserved number exists with Status=Ready

**Expected Results**:
- Standby count = 1
- Filter stops Zap (needs_replenishment = false)
- No purchase made
- No Audit Log entry

### Test 3: Pending Standby Exists (No Duplicate)

**Setup**:
1. Create standby number with Status=Pending
2. Ensure no Ready standby exists

**Expected Results**:
- Step 3 filter passes (no Ready standby)
- Step 5 filter stops Zap (pending standby exists)
- No duplicate purchase made

---

## Validation Checklist

- [ ] Schedule set to every 48 hours
- [ ] Standby count query filters for Lifecycle=Standby Reserved AND Status=Ready
- [ ] Filter checks standby_count == 0
- [ ] Pending standby check prevents duplicates
- [ ] Railway API endpoint configured correctly
- [ ] Number Inventory record created with correct Lifecycle
- [ ] Audit Log entry created
- [ ] Optional email notification configured (or disabled)
- [ ] Test with no standby available
- [ ] Test with standby already present
- [ ] Verify Zap 3 is triggered after purchase
- [ ] Zap enabled and monitoring

## Codebase Integration

**Railway Endpoints**:

**Primary** (TO BE IMPLEMENTED):
- `POST /numbers/standby-replenish`
  - **Purpose**: Purchase one standby reserved number
  - **Payload**:
    ```json
    {
      "lifecycle": "standby",
      "area_code": "303"
    }
    ```
  - **Response**:
    ```json
    {
      "success": true,
      "phone_number": "+13035551234",
      "number_inventory_id": "recXXXXXXXXXXXXXX",
      "status": "pending"
    }
    ```

**Alternative** (TO BE IMPLEMENTED):
- `POST /numbers/purchase`
  - Same payload and response
  - Generic number purchase endpoint
  - See ENDPOINTS_REFERENCE.md for implementation details

**Implementation Requirements**:
1. Search for available Colorado numbers (303/720 area codes)
2. Purchase number via Twilio API
3. Create Airtable Number Inventory record
4. Return phone number and record ID
5. DO NOT attach to Proxy yet (Zap 3 handles that)

**Related Files**:
- `services/twilio_proxy.py`: Number purchasing logic (needs implementation)
- `services/number_pool.py`: Pool management
- `routers/numbers.py`: Number purchase endpoint (needs creation)

**Related Tables**:
- Airtable: Number Inventory, Audit Log

## Notes

- This Zap ensures instant sitter provisioning via Zap 2 Path A
- Only maintains 1 standby number (not multiple)
- Standby is consumed by Zap 2 and immediately replenished
- Zap 3 completes the verification process
- No cooldown period needed (only purchases when count is 0)
- Pending check prevents race conditions if Zap runs multiple times

## Troubleshooting

**Issue**: Multiple standby numbers created  
**Solution**: Verify Step 5 filter is checking for pending standby numbers

**Issue**: Standby never replenished after use  
**Solution**: Check that Zap 2 is correctly triggering this Zap's schedule, or verify schedule is active

**Issue**: Railway API returns error  
**Solution**: Endpoint not yet implemented; see ENDPOINTS_REFERENCE.md for implementation requirements

**Issue**: Zap 3 doesn't trigger after purchase  
**Solution**: Verify Number Inventory record has Status=Pending and Zap 3 is enabled

**Issue**: Standby count shows 2 or more  
**Solution**: Manually review Number Inventory and consolidate to 1 standby; investigate why duplicates were created
