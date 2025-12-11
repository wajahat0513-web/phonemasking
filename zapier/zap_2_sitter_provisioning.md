# Zap 2: Sitter Provisioning (Reserved Number Assignment)

## Purpose

Automatically assign a masked phone number to new sitters when they are added via the Airtable form. This Zap handles three scenarios:
- **Path A**: Standby number available → assign immediately and replenish standby
- **Path B**: No standby available → purchase new reserved number
- **Path C**: Remove sitter → unlink number and convert to standby

## Trigger Configuration

**App**: Airtable  
**Trigger Event**: New Record in View  

### Setup Steps

1. **Base**: Phone Masking
2. **Table**: Sitters
3. **View**: Create a new view called "Pending Provisioning"
   - Filter: `Reserved Number` is empty AND `Status` = "Pending"
4. **Trigger Field**: Any field (triggers when new record appears in view)

> [!NOTE]
> The "Add New Sitter" form creates records with Status="Pending" and no Reserved Number, which automatically adds them to this view.

## Path Logic

This Zap uses **Paths by Zapier** to handle three different scenarios.

### Path A: Standby Available (Assign + Replenish)

**Condition**: At least one Standby Reserved number exists in Number Inventory

**Steps**:
1. Find standby number in Number Inventory
2. Assign standby number to sitter
3. Update Number Inventory (Lifecycle: Reserved Active)
4. Purchase new standby number to replenish
5. Send welcome email to owner

### Path B: No Standby (Purchase New)

**Condition**: No Standby Reserved numbers exist

**Steps**:
1. Call Railway API to purchase new reserved number
2. Create Number Inventory record (Status: Pending)
3. Link number to sitter (will be completed by Zap 3)
4. Send "pending" email to owner

### Path C: Remove Sitter

**Condition**: Sitter record has `Function` field = "Remove"

**Steps**:
1. Find sitter's current reserved number
2. Unlink number from sitter
3. Update Number Inventory (Lifecycle: Standby Reserved)
4. Update sitter Status to "Inactive"

---

## Path A: Standby Available

### Step 1: Find Standby Number

**App**: Airtable  
**Action**: Find Record  

**Configuration**:
- **Table**: Number Inventory
- **Search Field**: Lifecycle
- **Search Value**: `Standby Reserved`
- **Additional Filter**: Status = `Ready`
- **Limit**: 1 (only need one number)

**Output**: Standby number record ID and phone number

### Step 2: Link Number to Sitter

**App**: Airtable  
**Action**: Update Record  

**Configuration**:
- **Table**: Sitters
- **Record ID**: `{{trigger_record_id}}` (from trigger)
- **Fields to Update**:
  - `Reserved Number`: `{{standby_number_record_id}}` (linked record)
  - `Status`: `Active`
  - `Provisioned At`: `{{zap_meta_human_now}}`

### Step 3: Update Number Inventory

**App**: Airtable  
**Action**: Update Record  

**Configuration**:
- **Table**: Number Inventory
- **Record ID**: `{{standby_number_record_id}}` (from Step 1)
- **Fields to Update**:
  - `Lifecycle`: `Reserved Active`
  - `Status`: `Ready`
  - `Assigned To`: `{{trigger_record_id}}` (sitter record ID)
  - `Assigned At`: `{{zap_meta_human_now}}`

### Step 4: Purchase New Standby Number

**App**: Webhooks by Zapier  
**Action**: POST Request  

**Configuration**:
- **URL**: `https://your-railway-app.railway.app/numbers/purchase`
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
> This endpoint is NOT YET IMPLEMENTED. Current workaround: Use `/attach-number` without sitter_id (requires code modification).

**Expected Response**:
```json
{
  "success": true,
  "phone_number": "+13035551234",
  "number_inventory_id": "recXXXXXXXXXXXXXX",
  "status": "pending"
}
```

### Step 5: Send Welcome Email

**App**: Gmail (or SendGrid)  
**Action**: Send Email  

**Configuration**:
- **To**: `{{owner_email}}` (from config or hardcoded)
- **Subject**: `New Sitter Provisioned: {{sitter_name}}`
- **Body**: (See email template in ZAP_PROMPTS.README.md)

**Dynamic Fields**:
- `{{sitter_name}}`: From trigger
- `{{reserved_number}}`: From Step 1
- `{{sitter_real_phone}}`: From trigger

---

## Path B: No Standby Available

### Step 1: Purchase Reserved Number

**App**: Webhooks by Zapier  
**Action**: POST Request  

**Configuration**:
- **URL**: `https://your-railway-app.railway.app/numbers/purchase`
- **Method**: POST
- **Headers**:
  - `Content-Type`: `application/json`
- **Body** (JSON):
```json
{
  "lifecycle": "reserved",
  "area_code": "303",
  "sitter_id": "{{trigger_record_id}}"
}
```

> [!WARNING]
> This endpoint is NOT YET IMPLEMENTED. See ENDPOINTS_REFERENCE.md for implementation requirements.

**Expected Response**:
```json
{
  "success": true,
  "phone_number": "+13035551234",
  "number_inventory_id": "recXXXXXXXXXXXXXX",
  "status": "pending"
}
```

### Step 2: Create Number Inventory Record

**App**: Airtable  
**Action**: Create Record  

**Configuration**:
- **Table**: Number Inventory
- **Fields**:
  - `Phone Number`: `{{phone_number}}` (from Step 1)
  - `Lifecycle`: `Reserved Active`
  - `Status`: `Pending`
  - `Assigned To`: `{{trigger_record_id}}` (sitter record ID)
  - `Purchased At`: `{{zap_meta_human_now}}`

### Step 3: Link Number to Sitter (Partial)

**App**: Airtable  
**Action**: Update Record  

**Configuration**:
- **Table**: Sitters
- **Record ID**: `{{trigger_record_id}}`
- **Fields**:
  - `Reserved Number`: `{{number_inventory_record_id}}` (from Step 2)
  - `Status`: `Pending` (will be updated to Active by Zap 3)

### Step 4: Send Pending Email

**App**: Gmail  
**Action**: Send Email  

**Configuration**:
- **To**: `{{owner_email}}`
- **Subject**: `Sitter Number Pending: {{sitter_name}}`
- **Body**:
```
New sitter added: {{sitter_name}}

Reserved number purchase initiated: {{phone_number}}
Status: Pending verification

This number will be activated by Zap 3 within a few minutes.

Sitter Record: {{airtable_record_url}}
```

---

## Path C: Remove Sitter

### Step 1: Find Sitter's Reserved Number

**App**: Airtable  
**Action**: Find Record  

**Configuration**:
- **Table**: Number Inventory
- **Search Field**: Assigned To (linked record)
- **Search Value**: `{{trigger_record_id}}`

### Step 2: Unlink Number from Sitter

**App**: Airtable  
**Action**: Update Record  

**Configuration**:
- **Table**: Sitters
- **Record ID**: `{{trigger_record_id}}`
- **Fields**:
  - `Reserved Number`: (clear/empty)
  - `Status`: `Inactive`
  - `Deactivated At`: `{{zap_meta_human_now}}`

### Step 3: Convert Number to Standby

**App**: Airtable  
**Action**: Update Record  

**Configuration**:
- **Table**: Number Inventory
- **Record ID**: `{{number_record_id}}` (from Step 1)
- **Fields**:
  - `Lifecycle`: `Standby Reserved`
  - `Status`: `Ready`
  - `Assigned To`: (clear/empty)
  - `Released At`: `{{zap_meta_human_now}}`

---

## Testing Scenarios

### Test 1: Path A (Standby Available)

**Setup**:
1. Manually create a Standby Reserved number in Number Inventory
2. Submit "Add New Sitter" form

**Expected Results**:
- Standby number assigned to sitter
- Sitter Status = Active
- Number Inventory Lifecycle = Reserved Active
- New standby purchase initiated
- Welcome email sent

### Test 2: Path B (No Standby)

**Setup**:
1. Ensure no Standby Reserved numbers exist
2. Submit "Add New Sitter" form

**Expected Results**:
- Railway API called to purchase number
- Number Inventory record created (Status=Pending)
- Sitter Status = Pending
- Pending email sent
- Zap 3 will complete activation

### Test 3: Path C (Remove Sitter)

**Setup**:
1. Create sitter with assigned reserved number
2. Update sitter record with Function = "Remove"

**Expected Results**:
- Number unlinked from sitter
- Sitter Status = Inactive
- Number Inventory Lifecycle = Standby Reserved
- Number available for next new sitter

## Validation Checklist

- [ ] Trigger view "Pending Provisioning" created in Sitters table
- [ ] Paths configured with correct conditions
- [ ] Path A: Standby lookup finds correct number
- [ ] Path A: Replenishment purchase initiated
- [ ] Path B: Purchase endpoint called with correct payload
- [ ] Path C: Number properly converted to standby
- [ ] Email templates configured with dynamic fields
- [ ] Test all 3 paths with sample data
- [ ] Zap enabled and monitoring

## Codebase Integration

**Railway Endpoints**:
- `POST /numbers/purchase` (TO BE IMPLEMENTED)
  - Required for Path A (standby replenishment) and Path B (new reserved)
  - See ENDPOINTS_REFERENCE.md for implementation details

**Alternative** (current workaround):
- `POST /attach-number` with `sitter_id` parameter
  - Currently implemented in `routers/numbers.py`
  - Does NOT purchase numbers, only assigns existing ones

**Related Tables**:
- Airtable: Sitters, Number Inventory

## Notes

- Path A is the preferred flow (faster provisioning)
- Path B requires Zap 3 to complete activation
- Path C enables sitter reassignment without losing numbers
- Email notifications keep owner informed of provisioning status
