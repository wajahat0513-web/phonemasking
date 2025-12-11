# Railway Deployment Checklist

## ✅ Current Configuration Status

Your Railway setup is already configured correctly:
- ✅ `railway.json` exists with Dockerfile builder
- ✅ `Dockerfile` properly configured
- ✅ `requirements.txt` has all dependencies
- ✅ `.env.example` shows all required variables

## 🔧 Required Configuration in Railway Dashboard

### 1. Environment Variables (CRITICAL)

Go to your Railway project → **Variables** tab and add these:

#### Twilio Credentials
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_actual_auth_token
TWILIO_PROXY_SERVICE_SID=KSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Where to find**:
- Go to https://console.twilio.com/
- Account SID and Auth Token: Dashboard home page
- Proxy Service SID: Proxy → Services → Click your service → Copy SID

#### Airtable Credentials
```
AIRTABLE_API_KEY=patxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AIRTABLE_BASE_ID=appxxxxxxxxxxxxxx
```

**Where to find**:
- API Key: https://airtable.com/create/tokens (create a Personal Access Token)
- Base ID: Open your base → Help → API documentation → Copy base ID from URL

#### Airtable Table Names (Optional - only if different from defaults)
```
AIRTABLE_SITTERS_TABLE=Sitters
AIRTABLE_CLIENTS_TABLE=Clients
AIRTABLE_MESSAGES_TABLE=Messages
AIRTABLE_NUMBER_INVENTORY_TABLE=Number Inventory
AIRTABLE_AUDIT_LOG_TABLE=Audit Log
```

**Note**: Only add these if your table names are different from the defaults shown above.

---

### 2. Deployment Settings

#### Build Settings
- ✅ **Builder**: Dockerfile (already configured in railway.json)
- ✅ **Dockerfile Path**: `Dockerfile` (already configured)
- ✅ **Start Command**: `python start.py` (already configured)

#### Runtime Settings
- ✅ **Restart Policy**: ON_FAILURE (already configured)
- ✅ **Max Retries**: 10 (already configured)

---

### 3. Networking Configuration

#### Public Domain
1. Go to **Settings** tab
2. Scroll to **Networking**
3. Click **Generate Domain** (if not already done)
4. Copy your Railway URL (e.g., `https://phonemasking-production.up.railway.app`)

**You'll need this URL for**:
- Twilio webhook configuration
- Zapier webhook actions
- Testing endpoints

---

### 4. Twilio Webhook Configuration

After Railway deploys, configure Twilio webhooks:

#### Proxy Service Webhooks
1. Go to https://console.twilio.com/us1/develop/proxy/services
2. Click your Proxy Service
3. Scroll to **Callback Configuration**
4. Set these webhooks:

**Out-of-Session Callback URL**:
```
https://your-railway-app.up.railway.app/out-of-session
```
Method: `POST`

**Intercept Callback URL**:
```
https://your-railway-app.up.railway.app/intercept
```
Method: `POST`

**Session TTL**: `1209600` (14 days in seconds)

---

### 5. Health Check Endpoint (Optional but Recommended)

Railway automatically monitors your service. To add a custom health check:

1. Go to **Settings** → **Health Check**
2. Set path to `/` or `/docs`
3. Expected status: `200`

---

## 🚀 Deployment Steps

### Step 1: Verify Environment Variables
```bash
# In Railway dashboard, check Variables tab
# Ensure all required variables are set
```

### Step 2: Monitor Deployment
1. Go to **Deployments** tab
2. Watch the build logs
3. Look for:
   - ✅ "Building Dockerfile"
   - ✅ "Installing dependencies"
   - ✅ "Starting application"
   - ✅ "Uvicorn running on http://0.0.0.0:8080"

### Step 3: Check Deployment Status
```bash
# Should show "Active" with green indicator
```

### Step 4: Test Endpoints
```bash
# Replace with your actual Railway URL
curl https://your-railway-app.up.railway.app/docs

# Should return Swagger UI HTML
```

---

## 🧪 Post-Deployment Testing

### Test 1: API Documentation
```bash
# Open in browser
https://your-railway-app.up.railway.app/docs
```
**Expected**: Swagger UI with all endpoints listed

### Test 2: Number Purchase Endpoint
```bash
curl -X POST https://your-railway-app.up.railway.app/numbers/purchase \
  -H "Content-Type: application/json" \
  -d '{
    "lifecycle": "pool",
    "area_code": "303"
  }'
```
**Expected**: JSON response with purchased number details

### Test 3: Debug Endpoint (Inventory Check)
```bash
curl https://your-railway-app.up.railway.app/numbers/debug
```
**Expected**: JSON with inventory statistics

---

## 📊 Monitoring & Logs

### View Logs
1. Go to **Deployments** tab
2. Click on active deployment
3. View real-time logs

**Look for**:
- ✅ "Started server process"
- ✅ "Application startup complete"
- ✅ "Uvicorn running on http://0.0.0.0:8080"

### Common Log Messages
```
INFO: Searching for available numbers in area code 303
INFO: Purchasing number: +13035551234
INFO: Purchased Twilio Number
INFO: Created new client record for +13035559999
INFO: Prepending client name to message: John Doe
```

---

## ⚠️ Common Issues & Solutions

### Issue 1: Build Fails - Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Check `requirements.txt` is committed and pushed
```bash
git add requirements.txt
git commit -m "fix: add requirements.txt"
git push
```

---

### Issue 2: Application Won't Start
**Error**: `Address already in use`

**Solution**: Railway sets PORT automatically. Ensure `start.py` uses:
```python
port = int(os.getenv("PORT", 8080))
```
✅ Already configured correctly in your code

---

### Issue 3: Environment Variables Not Found
**Error**: `KeyError: 'TWILIO_ACCOUNT_SID'`

**Solution**: 
1. Go to Railway Variables tab
2. Add missing variable
3. Redeploy (Railway auto-redeploys on variable changes)

---

### Issue 4: Twilio Webhooks Not Working
**Error**: Twilio shows webhook timeout

**Solution**:
1. Verify Railway URL is correct in Twilio
2. Check Railway logs for incoming requests
3. Ensure endpoints return within 10 seconds

---

### Issue 5: Airtable Connection Fails
**Error**: `401 Unauthorized` or `404 Not Found`

**Solution**:
1. Verify AIRTABLE_API_KEY is a Personal Access Token (starts with `pat`)
2. Verify AIRTABLE_BASE_ID is correct (starts with `app`)
3. Check table names match exactly (case-sensitive)

---

## 🔒 Security Recommendations (Optional - Phase 4)

### Add API Key Authentication
1. Add to Railway Variables:
```
API_KEYS=your_zapier_key,your_admin_key
```

2. Uncomment authentication middleware in `main.py` (when implemented)

### IP Whitelisting
Railway supports IP whitelisting in Pro plan:
- Zapier IP ranges
- Twilio IP ranges
- Your office/home IP

---

## 📈 Scaling Configuration

### Current Setup (Starter Plan)
- ✅ Auto-restart on failure
- ✅ 512MB RAM
- ✅ 1 vCPU

### If You Need More (Pro Plan)
1. Go to **Settings** → **Resources**
2. Adjust:
   - RAM: Up to 8GB
   - vCPU: Up to 8 cores
   - Replicas: Multiple instances

---

## ✅ Final Checklist

Before going live with Zapier:

- [ ] All environment variables set in Railway
- [ ] Deployment shows "Active" status
- [ ] `/docs` endpoint accessible
- [ ] Test `/numbers/purchase` endpoint works
- [ ] Twilio webhooks configured
- [ ] Proxy Service SID correct
- [ ] Airtable connection working
- [ ] Logs show no errors
- [ ] Railway URL copied for Zapier configuration

---

## 🎯 Next Steps After Railway Setup

1. **Update Zapier Automations**:
   - Zap 2: Use `https://your-railway-app.up.railway.app/numbers/purchase`
   - Zap 3: Use `https://your-railway-app.up.railway.app/attach-number`
   - Zap 4: Use `https://your-railway-app.up.railway.app/numbers/purchase`
   - Zap 5: Use `https://your-railway-app.up.railway.app/numbers/purchase`

2. **Test Each Zap**:
   - Follow test scenarios in `zapier/zap_X_*.md` files
   - Verify Railway logs show incoming requests
   - Check Airtable records are created

3. **Monitor Production**:
   - Watch Railway logs for errors
   - Check Twilio usage/costs
   - Monitor Airtable record counts

---

## 📞 Support Resources

- **Railway Docs**: https://docs.railway.app/
- **Railway Discord**: https://discord.gg/railway
- **Twilio Support**: https://support.twilio.com/
- **Airtable Support**: https://support.airtable.com/

---

## 🎉 You're All Set!

Your code is deployed. Railway will:
1. ✅ Detect the push
2. ✅ Build using Dockerfile
3. ✅ Install dependencies
4. ✅ Start the application
5. ✅ Assign a public URL

**Estimated deployment time**: 2-5 minutes

Check the Railway dashboard for deployment status!
