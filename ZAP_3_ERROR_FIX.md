# Zap 3 Error Fix Guide

## Error Message
```
Failed to assign number: ('422 Client Error: Unprocessable Entity for url: https://api.airtable.com/v0/appRhIAaMEWQsO6mm/Number%20Inventory/recGvjNsp0lUhtvFz', "{'type': 'ROW_TABLE_DOES_NOT_MATCH_LINKED_TABLE', 'message': 'Record ID rec1JpBG4sfRATQLZ belongs to table tbltLCwIzJQCDM7VH, but the field links to table tbl9UqavqrubOgcFb'}")
```

## Root Cause

Zap 3 is sending the **Number Inventory record ID** instead of the **Sitter record ID** to the `/attach-number` endpoint.

**What's happening**:
1. Zap 3 triggers on Number Inventory record (e.g., `recGvjNsp0lUhtvFz`)
2. It tries to send this as `sitter_id` to the Railway API
3. Railway API tries to link this ID to the Number Inventory's "Assigned Sitter" field
4. Airtable rejects it because the ID belongs to Number Inventory table, not Sitters table

## Solution: Fix Zap 3 Step 1 Configuration

### Current (WRONG) Configuration:
```json
{
  "sitter_id": "{{assigned_to_record_id}}"
}
```

### Correct Configuration:

**For Reserved Numbers (with assigned sitter)**:
```json
{
  "sitter_id": "{{Assigned Sitter}}"
}
```

**How to set this up in Zapier**:

1. **Go to Zap 3 → Step 1 (Webhooks by Zapier)**

2. **Click on the `sitter_id` field**

3. **In the dropdown, look for "Assigned Sitter"**
   - It will show as a linked record field
   - You'll see something like: `Assigned Sitter: 0: Value` or `Assigned Sitter (array)`

4. **Select the FIRST item from the array**:
   - If it shows `Assigned Sitter: 0: Value` → Select this
   - If it shows `Assigned Sitter` with array icon → Add `: 0` to get first item
   - The final field reference should be: `{{Assigned Sitter: 0: Value}}`

5. **Test the step** with a Number Inventory record that HAS an assigned sitter

### Alternative: Use Zapier Formatter

If the linked field is tricky, use Formatter:

1. **Add a Formatter step BEFORE the webhook**:
   - **App**: Formatter by Zapier
   - **Transform**: Text → Extract Pattern
   - **Input**: `{{Assigned Sitter}}`
   - **Pattern**: `rec[A-Za-z0-9]+`

2. **Use the formatter output** in the webhook:
   ```json
   {
     "sitter_id": "{{formatter_output}}"
   }
   ```

## For Pool/Standby Numbers (No Assigned Sitter)

Pool and Standby numbers don't have assigned sitters, so Zap 3 will fail for them. This is **expected behavior**.

**Two options**:

### Option A: Add a Filter Before Step 1
1. **Add Filter by Zapier** before the webhook call
2. **Condition**: 
   - Field: `Lifecycle` (from trigger)
   - Condition: `equals`
   - Value: `Reserved Active`
3. This ensures Zap 3 only runs for sitter numbers

### Option B: Handle the Error Gracefully
1. Keep the Zap as-is
2. When it fails for Pool/Standby numbers, that's OK
3. Those numbers will be attached when they're assigned to a sitter later

## Testing

### Test with Reserved Number:

1. **Create a Number Inventory record**:
   - Phone Number: `+13035551234`
   - Lifecycle: `Reserved Active`
   - Status: `Pending`
   - Assigned Sitter: (link to a real sitter record)

2. **Check Zap History**:
   - Step 1 should show: `sitter_id: recXXXXXXXXXXXXXX` (starts with "rec")
   - The ID should be from the Sitters table, NOT Number Inventory

3. **Verify in Railway logs**:
   ```
   INFO: Attaching new number for sitter recXXXXXXXXXXXXXX
   ```

### Test with Pool Number:

1. **Create a Number Inventory record**:
   - Phone Number: `+17205551234`
   - Lifecycle: `Pool`
   - Status: `Pending`
   - Assigned Sitter: (empty)

2. **Expected behavior**:
   - If you added the filter (Option A): Zap stops before webhook
   - If no filter (Option B): Zap fails with "sitter_id is required" - this is OK

## Quick Diagnostic

**To verify you're sending the correct sitter_id**:

1. Go to Zap History
2. Find a recent run
3. Click on Step 1 (Webhooks)
4. Look at the "Data Out" section
5. Check the `sitter_id` value:
   - ✅ **Correct**: Starts with `rec` and is 17 characters (e.g., `rec1JpBG4sfRATQLZ`)
   - ❌ **Wrong**: Is the same as the trigger record ID

**To find the correct field name**:

1. In Zap editor, click "Refresh fields" on the trigger
2. Look for a field that shows the linked Sitter record
3. Common field names:
   - `Assigned Sitter`
   - `Assigned Sitter: 0: Value`
   - `Assigned Sitter (from Number Inventory)`

## Summary

**The Fix**: Change Zap 3 Step 1 webhook body from:
```json
{
  "sitter_id": "{{assigned_to_record_id}}"  // ❌ WRONG - This is the Number Inventory ID
}
```

To:
```json
{
  "sitter_id": "{{Assigned Sitter: 0: Value}}"  // ✅ CORRECT - This is the Sitter ID
}
```

**Why this fixes it**: The Railway API needs the **Sitter record ID**, not the Number Inventory record ID. Linked fields in Zapier are arrays, so we need to extract the first (and only) item with `: 0`.
