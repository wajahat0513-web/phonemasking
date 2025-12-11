# Zap 4: Pool Capacity Monitor

## Purpose

Automatically monitor the utilization of proxy pool numbers and purchase additional numbers when capacity reaches 87% or higher. This ensures the system always has enough pool numbers available for new client-sitter sessions without manual intervention.

## Trigger Configuration

**App**: Schedule by Zapier  
**Trigger Event**: Every 48 Hours  

### Setup Steps

1. Select "Schedule by Zapier"
2. Choose "Every X Hours"
3. Set interval to **48 hours**
4. Set start time (e.g., 2:00 AM to avoid peak hours)

> [!IMPORTANT]
> Do NOT set this to run more frequently than 48 hours. Frequent checks can lead to unnecessary purchases and increased costs.

## Step-by-Step Configuration

### Step 1: Count Ready Pool Numbers

**App**: Airtable  
**Action**: Find Records  

**Configuration**:
- **Table**: Number Inventory
- **Filter Formula**:
```
AND(
  {Lifecycle} = "Pool",
  {Status} = "Ready"
)
```
- **Max Records**: 100 (should be more than enough)

**Output**: List of ready pool numbers

### Step 2: Count Ready Pool Numbers (Code)

**App**: Code by Zapier  
**Action**: Run Python  

**Input Data**:
- `pool_numbers`: `{{step1_records}}` (array from Step 1)

**Code**:
```python
# Count ready pool numbers
pool_numbers = input_data.get('pool_numbers', [])
ready_count = len(pool_numbers)

output = {'ready_pool_count': ready_count}
```

**Output**: `ready_pool_count` (integer)

### Step 3: Get Active Session Count

**Option A: From Airtable Audit Log** (Recommended)

**App**: Airtable  
**Action**: Find Records  

**Configuration**:
- **Table**: Audit Log
- **Filter Formula**:
```
AND(
  {Event Type} = "session_created",
  {Status} = "active",
  DATETIME_DIFF(NOW(), {Created At}, 'days') <= 14
)
```
- **Max Records**: 100

**Then**: Count records using Code by Zapier (similar to Step 2)

**Option B: From Railway API** (TO BE IMPLEMENTED)

**App**: Webhooks by Zapier  
**Action**: GET Request  

**Configuration**:
- **URL**: `https://your-railway-app.railway.app/sessions/active-count`
- **Method**: GET

**Expected Response**:
```json
{
  "active_sessions": 15
}
```

> [!WARNING]
> The `/sessions/active-count` endpoint is NOT YET IMPLEMENTED. Use Option A (Airtable) until this endpoint is created.

### Step 4: Calculate Utilization Rate

**App**: Code by Zapier  
**Action**: Run Python  

**Input Data**:
- `ready_pool_count`: `{{step2_ready_pool_count}}`
- `active_sessions`: `{{step3_active_sessions}}`

**Code**:
```python
ready_pool = int(input_data.get('ready_pool_count', 0))
active_sessions = int(input_data.get('active_sessions', 0))

# Avoid division by zero
if ready_pool == 0:
    utilization_rate = 1.0  # 100% if no pool numbers
else:
    utilization_rate = active_sessions / ready_pool

output = {
    'utilization_rate': utilization_rate,
    'ready_pool': ready_pool,
    'active_sessions': active_sessions,
    'threshold_met': utilization_rate >= 0.87
}
```

**Output**:
- `utilization_rate`: Float (e.g., 0.75 = 75%)
- `threshold_met`: Boolean (true if ≥ 87%)

### Step 5: Filter - Only Continue if Threshold Met

**App**: Filter by Zapier  

**Condition 1**: Utilization Rate Check
- Field: `threshold_met` (from Step 4)
- Condition: `equals` `true`

**Condition 2**: No Pending Pool Numbers
- Field: Count of pending pool numbers (from new Airtable lookup)
- Condition: `equals` `0`

**Additional Check**: Cooldown Period (72 hours)
- Use Airtable to find last pool purchase timestamp
- Filter: Only continue if last purchase was >72 hours ago

### Step 6: Check Cooldown Period

**App**: Airtable  
**Action**: Find Records  

**Configuration**:
- **Table**: Number Inventory
- **Filter Formula**:
```
AND(
  {Lifecycle} = "Pool",
  DATETIME_DIFF(NOW(), {Purchased At}, 'hours') <= 72
)
```
- **Max Records**: 1

**Then**: Filter by Zapier
- If records found: STOP (cooldown active)
- If no records: CONTINUE (cooldown expired)

### Step 7: Purchase New Pool Number

**App**: Webhooks by Zapier  
**Action**: POST Request  

**Configuration**:
- **URL**: `https://your-railway-app.railway.app/inventory/check-and-replenish`
- **Method**: POST
- **Headers**:
  - `Content-Type`: `application/json`
- **Body** (JSON):
```json
{
  "lifecycle": "pool",
  "area_code": "303",
  "quantity": 1
}
```

> [!WARNING]
> This endpoint is NOT YET IMPLEMENTED. Alternative endpoint: `POST /numbers/purchase` (also needs implementation).

**Expected Response**:
```json
{
  "success": true,
  "phone_number": "+13035551234",
  "number_inventory_id": "recXXXXXXXXXXXXXX",
  "status": "pending"
}
```

### Step 8: Create Number Inventory Record

**App**: Airtable  
**Action**: Create Record  

**Configuration**:
- **Table**: Number Inventory
- **Fields**:
  - `Phone Number`: `{{phone_number}}` (from Step 7)
  - `Lifecycle`: `Pool`
  - `Status`: `Pending`
  - `Purchased At`: `{{zap_meta_human_now}}`
  - `Purchase Reason`: `Auto-scaling (Utilization: {{utilization_rate}})`

> [!NOTE]
> This record will trigger Zap 3 (Number Verification) to complete the attachment process.

### Step 9: Log Purchase Event

**App**: Airtable  
**Action**: Create Record  

**Configuration**:
- **Table**: Audit Log
- **Fields**:
  - `Event Type`: `pool_purchase`
  - `Details`: `Auto-purchased pool number due to {{utilization_rate}}% utilization`
  - `Phone Number`: `{{phone_number}}`
  - `Status`: `success`
  - `Created At`: `{{zap_meta_human_now}}`

---

## Testing Scenarios

### Test 1: High Utilization (Purchase Triggered)

**Setup**:
1. Manually adjust test data:
   - Ready Pool Numbers: 10
   - Active Sessions: 9 (90% utilization)
2. Ensure no pending pool numbers
3. Ensure cooldown period expired

**Expected Results**:
- Utilization calculated as 0.90 (90%)
- Threshold met (≥ 0.87)
- Railway API called to purchase 1 pool number
- Number Inventory record created (Status=Pending)
- Audit Log entry created
- Zap 3 triggered to verify new number

### Test 2: Low Utilization (No Purchase)

**Setup**:
- Ready Pool Numbers: 20
- Active Sessions: 10 (50% utilization)

**Expected Results**:
- Utilization calculated as 0.50 (50%)
- Threshold NOT met
- Zap stops at Step 5 filter
- No purchase made

### Test 3: Cooldown Active (No Purchase)

**Setup**:
- Utilization: 90% (threshold met)
- Last pool purchase: 24 hours ago (within 72h cooldown)

**Expected Results**:
- Threshold met
- Cooldown check finds recent purchase
- Zap stops at Step 6 filter
- No purchase made

---

## Validation Checklist

- [ ] Schedule set to every 48 hours (not 48 minutes!)
- [ ] Pool number count query filters for Lifecycle=Pool AND Status=Ready
- [ ] Active session count accurate (Airtable or Railway API)
- [ ] Utilization calculation correct (active/ready)
- [ ] Filter checks threshold ≥ 0.87
- [ ] Cooldown check prevents purchases within 72 hours
- [ ] Railway API endpoint configured correctly
- [ ] Number Inventory record created with Status=Pending
- [ ] Audit Log entry created for tracking
- [ ] Test with simulated high utilization
- [ ] Verify Zap 3 is triggered after purchase
- [ ] Zap enabled and monitoring

## Codebase Integration

**Railway Endpoints**:

**Primary** (TO BE IMPLEMENTED):
- `POST /inventory/check-and-replenish`
  - **Purpose**: Check pool health and purchase if needed
  - **Payload**:
    ```json
    {
      "lifecycle": "pool",
      "area_code": "303",
      "quantity": 1
    }
    ```
  - **Response**:
    ```json
    {
      "success": true,
      "phone_number": "+13035551234",
      "number_inventory_id": "recXXXXXXXXXXXXXX"
    }
    ```

**Alternative** (TO BE IMPLEMENTED):
- `POST /numbers/purchase`
  - Same payload and response as above
  - See ENDPOINTS_REFERENCE.md for implementation details

**Related Files**:
- `services/twilio_proxy.py`: Number purchasing logic (needs implementation)
- `services/number_pool.py`: Pool management
- `routers/numbers.py`: Number purchase endpoint (needs creation)

**Related Tables**:
- Airtable: Number Inventory, Audit Log

## Notes

- This Zap prevents pool exhaustion by proactive purchasing
- 87% threshold provides buffer before running out of numbers
- 72-hour cooldown prevents rapid successive purchases
- Purchases exactly 1 number at a time (not bulk)
- Zap 3 completes the verification and activation process
- Audit Log provides purchase history for cost tracking

## Troubleshooting

**Issue**: Zap purchases numbers too frequently  
**Solution**: Verify cooldown check (Step 6) is working and set to 72 hours

**Issue**: Utilization always shows 100%  
**Solution**: Check that ready_pool_count is not zero; verify pool numbers exist with Status=Ready

**Issue**: Railway API returns error  
**Solution**: Endpoint not yet implemented; see ENDPOINTS_REFERENCE.md for implementation requirements

**Issue**: Zap doesn't trigger at scheduled time  
**Solution**: Check Zapier account status and ensure Zap is enabled (not paused)
