# Zap 3 "Not Found" Error - Quick Fix

## Error: "Not Found"

This means the endpoint doesn't exist at the URL you're calling.

## Checklist

### 1. Verify Railway Deployment

**Go to Railway Dashboard** → Your Project → **Deployments**

Check that:
- ✅ Latest deployment shows "Active" (green)
- ✅ Build completed successfully
- ✅ Logs show "Uvicorn running on http://0.0.0.0:8080"

**If still deploying**: Wait 1-2 more minutes

### 2. Verify the Exact URL

The URL should be **exactly**:
```
https://your-railway-app.railway.app/numbers/add-to-proxy
```

**Common mistakes**:
- ❌ `https://.../add-to-proxy` (missing `/numbers/`)
- ❌ `https://.../number/add-to-proxy` (singular "number")
- ❌ `https://.../numbers/add-proxy` (missing "to")
- ✅ `https://.../numbers/add-to-proxy` (CORRECT)

### 3. Test the Endpoint Manually

**Option A: Use Browser**

Go to:
```
https://your-railway-app.railway.app/docs
```

You should see the Swagger UI with all endpoints listed, including:
- `POST /numbers/add-to-proxy`

Click on it to test.

**Option B: Use curl**

```bash
curl -X POST https://your-railway-app.railway.app/numbers/add-to-proxy \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+13035551234"}'
```

**Expected response** (if number exists):
```json
{
  "success": true,
  "proxy_phone_sid": "PNxxx...",
  "phone_number": "+13035551234"
}
```

### 4. Check Railway Logs

In Railway dashboard:
1. Go to **Deployments** → Click active deployment
2. Look for startup logs:
   ```
   INFO: Started server process
   INFO: Application startup complete
   INFO: Uvicorn running on http://0.0.0.0:8080
   ```

3. Look for route registration:
   ```
   POST /numbers/add-to-proxy
   ```

### 5. Verify in Zapier

In Zap 3, Step 1:

**URL field should show**:
```
https://phonemasking-production-XXXX.up.railway.app/numbers/add-to-proxy
```

**NOT**:
- `https://.../attach-number` (old endpoint)
- `https://.../add-to-proxy` (missing /numbers/)

## Quick Test

1. **Copy your Railway URL** from Railway dashboard (Settings → Domains)
2. **Add `/docs` to the end**
3. **Open in browser**: `https://your-app.railway.app/docs`
4. **Look for** `POST /numbers/add-to-proxy` in the list
5. **If you see it**: Endpoint is deployed ✅
6. **If you don't see it**: Railway hasn't deployed yet ⏳

## If Still Not Working

### Check Git Push Succeeded

```bash
git log --oneline -3
```

Should show:
```
9237563 feat: add /numbers/add-to-proxy endpoint for Zap 3
39a0eed feat: number purchasing, message prepending, client deduplication
...
```

### Force Railway Redeploy

1. Go to Railway dashboard
2. Click **Deployments**
3. Click **⋮** (three dots) on latest deployment
4. Click **Redeploy**

### Check Railway Environment Variables

Make sure all required variables are still set:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PROXY_SERVICE_SID`
- `AIRTABLE_API_KEY`
- `AIRTABLE_BASE_ID`

## Temporary Workaround

While waiting for deployment, you can use **Twilio's API directly** in Zap 3:

**URL**:
```
https://proxy.twilio.com/v1/Services/YOUR_PROXY_SID/PhoneNumbers
```

**Method**: POST

**Auth**: Basic (Account SID / Auth Token)

**Body** (form-urlencoded):
```
PhoneNumberSid={{338182815__Twilio SID}}
```

This bypasses Railway entirely.

## Summary

**Most likely cause**: Railway is still deploying (takes 2-5 minutes)

**Solution**: 
1. Check Railway dashboard for deployment status
2. Once "Active", verify endpoint at `/docs`
3. Update Zap 3 with correct URL
4. Test again

**Correct URL format**:
```
https://[your-railway-domain]/numbers/add-to-proxy
                              ^^^^^^^^ Don't forget this part!
```
