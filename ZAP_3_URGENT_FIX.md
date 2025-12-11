# ZAP 3 URGENT FIX

## The Problem

Zap 3 is calling `/attach-number` which is designed to:
1. Get an UNASSIGNED number from pool
2. Assign it to a sitter  
3. Add to Proxy

But for Zap 3, the number is ALREADY ASSIGNED (Zap 2 did this). So step #2 fails with table mismatch error.

## Immediate Workaround

**Option 1: Use Twilio Directly in Zap 3 (RECOMMENDED)**

Instead of calling Railway `/attach-number`, use Twilio's API directly:

### Zap 3 Step 1: Add Number to Proxy (Twilio API)

**App**: Webhooks by Zapier
**Action**: POST

**URL**: 
```
https://proxy.twilio.com/v1/Services/{{PROXY_SERVICE_SID}}/PhoneNumbers
```

**Headers**:
```
Authorization: Basic {{base64(ACCOUNT_SID:AUTH_TOKEN)}}
Content-Type: application/x-www-form-urlencoded
```

**Body** (form-encoded):
```
PhoneNumberSid={{338182815__Twilio SID}}
```

**Expected Response**:
```json
{
  "sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "phone_number": "+13035551234"
}
```

This bypasses the Railway API entirely and adds the number directly to Proxy.

---

## Option 2: Create New Railway Endpoint (Better Long-term)

Add a new endpoint `/numbers/add-to-proxy` that ONLY adds to Proxy without reassigning:

```python
@router.post("/numbers/add-to-proxy")
async def add_to_proxy(phone_number: str):
    """
    Add an already-purchased number to Proxy Service.
    Used by Zap 3 for numbers that are already assigned.
    """
    try:
        from services.twilio_proxy import add_number_to_proxy_service
        proxy_sid = add_number_to_proxy_service(phone_number)
        
        return {
            "success": True,
            "proxy_phone_sid": proxy_sid,
            "phone_number": phone_number
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

Then Zap 3 calls:
```json
{
  "phone_number": "{{338182815__PhoneNumber}}"
}
```

---

## Quick Test

To verify the number just needs to be added to Proxy:

1. Go to Twilio Console → Proxy → Phone Numbers
2. Manually add the number `+13035551234`
3. Check if it works

If manual add works, then Zap 3 just needs to call Twilio's Proxy API directly (Option 1).

---

## Recommended Action

**Use Option 1** (Twilio API directly) because:
- ✅ No code changes needed
- ✅ Works immediately  
- ✅ Simpler than Railway endpoint
- ✅ One less network hop

Update Zap 3 Step 1 to call Twilio Proxy API instead of Railway.
