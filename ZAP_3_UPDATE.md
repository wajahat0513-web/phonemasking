# Zap 3 - Updated Configuration

## ✅ NEW ENDPOINT DEPLOYED

A new endpoint `/numbers/add-to-proxy` has been created specifically for Zap 3.

**Endpoint**: `POST /numbers/add-to-proxy`

**Purpose**: Adds an already-purchased and already-assigned number to Twilio Proxy Service without reassigning it.

---

## Update Zap 3 Step 1

### Old Configuration (WRONG):
```
URL: https://your-railway-app.railway.app/attach-number
Body: {"sitter_id": "{{Assigned Sitter: 0}}"}
```

### New Configuration (CORRECT):
```
URL: https://your-railway-app.railway.app/numbers/add-to-proxy
Body: {"phone_number": "{{338182815__PhoneNumber}}"}
```

---

## Step-by-Step Update Instructions

1. **Go to Zap 3** → **Step 1** (Webhooks by Zapier)

2. **Update the URL**:
   - Old: `https://your-railway-app.railway.app/attach-number`
   - New: `https://your-railway-app.railway.app/numbers/add-to-proxy`

3. **Update the Request Body**:
   - Remove: `sitter_id` field
   - Keep only: `phone_number` field
   
   **Final JSON**:
   ```json
   {
     "phone_number": "{{338182815__PhoneNumber}}"
   }
   ```

4. **Headers** (keep as-is):
   ```
   Content-Type: application/json
   ```

5. **Method** (keep as-is):
   ```
   POST
   ```

6. **Test the step** with a Number Inventory record that has:
   - Phone Number: Valid Twilio number
   - Status: Pending
   - Lifecycle: Reserved Active (or any)

---

## Expected Response

**Success**:
```json
{
  "success": true,
  "proxy_phone_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "phone_number": "+13035551234"
}
```

**Error** (number already in Proxy):
```json
{
  "success": false,
  "error": "Number already exists in Proxy Service",
  "details": "Check that number exists in Twilio and is not already in Proxy"
}
```

---

## What This Endpoint Does

1. ✅ Takes the phone number from the request
2. ✅ Adds it to Twilio Proxy Service (calls Twilio API)
3. ✅ Updates Number Inventory in Airtable:
   - Sets `Proxy Phone SID`
   - Sets `Attach Status` = "Ready"
   - Sets `Status` = "Ready"
4. ✅ Returns success response

**Does NOT**:
- ❌ Reassign the number to a sitter (already assigned by Zap 2)
- ❌ Require sitter_id
- ❌ Look up available numbers from pool

---

## Testing

### Test Case 1: New Reserved Number

**Setup**:
1. Create Number Inventory record:
   - Phone Number: `+13035551234` (must exist in Twilio)
   - Lifecycle: `Reserved Active`
   - Status: `Pending`
   - Assigned Sitter: (linked to a sitter)

**Expected**:
- ✅ Webhook returns `success: true`
- ✅ Number added to Twilio Proxy
- ✅ Airtable Status updated to "Ready"
- ✅ Proxy Phone SID populated

### Test Case 2: Already in Proxy

**Setup**:
1. Manually add number to Proxy in Twilio Console
2. Trigger Zap 3 with same number

**Expected**:
- ⚠️ Webhook returns `success: false`
- ⚠️ Error: "Number already exists in Proxy"
- ✅ Zap continues (filter handles this)

---

## Complete Zap 3 Flow

1. **Trigger**: Airtable - New/Updated Record in "Pending Verification" view
2. **Step 1**: Webhooks - POST to `/numbers/add-to-proxy` ← **UPDATED**
3. **Step 2**: Filter - Only continue if `success` = true
4. **Step 3**: Twilio - Send test SMS (optional)
5. **Step 4**: Airtable - Update Status to "Ready" (can skip if endpoint does this)
6. **Step 5**: Filter - Check if Lifecycle = "Reserved Active"
7. **Step 6**: Airtable - Update Sitter Status to "Active"
8. **Step 7**: Gmail - Send activation email

---

## Deployment Status

- ✅ Code committed: `feat: add /numbers/add-to-proxy endpoint for Zap 3`
- ✅ Pushed to GitHub
- ⏳ Railway deploying (check dashboard)
- ⏳ Update Zap 3 configuration (after Railway deployment completes)

---

## Verification

After updating Zap 3:

1. **Check Railway logs** for:
   ```
   INFO: Adding number +13035551234 to Proxy Service
   INFO: Successfully added +13035551234 to Proxy (SID: PNxxx...)
   ```

2. **Check Twilio Console** → Proxy → Phone Numbers:
   - Number should appear in list

3. **Check Airtable** Number Inventory:
   - Status = "Ready"
   - Proxy Phone SID populated

---

## Troubleshooting

**Error: "Number does not exist in Twilio"**
- Solution: Verify number was purchased (check Twilio Console → Phone Numbers)

**Error: "Number already in Proxy"**
- Solution: This is OK if number was manually added. Zap will skip to next step.

**Error: "Invalid phone number format"**
- Solution: Ensure phone number is in E.164 format (+1XXXXXXXXXX)

---

## Summary

**What changed**:
- ❌ Old: `/attach-number` (requires sitter_id, reassigns number)
- ✅ New: `/numbers/add-to-proxy` (only needs phone_number, just adds to Proxy)

**Why this fixes it**:
- Numbers from Zap 2 are already assigned to sitters
- We just need to add them to Proxy, not reassign them
- New endpoint does exactly that

**Next steps**:
1. Wait for Railway deployment to complete (~2 minutes)
2. Update Zap 3 Step 1 with new URL and body
3. Test with a pending number
4. Verify in Twilio Console and Airtable
