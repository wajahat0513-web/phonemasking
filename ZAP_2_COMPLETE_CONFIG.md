# Zap 2: Updated Configuration (100% Requirements Met)

## ✅ All Client Requirements Implemented

This configuration uses the **new `/numbers/purchase` endpoint** that was just deployed.

---

## Complete Zap 2 Flow

### **TRIGGER: New Record in Sitters Table**
- **Table**: Sitters
- **View**: "Pending Provisioning"
- **Filter**: Status = "Pending" AND Reserved Number is empty

---

## **PATHS CONFIGURATION**

Use **Paths by Zapier** with 3 paths:

### **Path A: Standby Available** ✅
**Condition**: Check if standby number exists

### **Path B: No Standby** ✅
**Condition**: No standby available

### **Path C: Remove Sitter** ✅
**Condition**: Function field = "Remove"

---

## PATH A: Standby Available (Assign + Replenish)

### **Step A1: Find Standby Number**
**App**: Airtable - Find Record

```
Table: Number Inventory
Search Field: Lifecycle
Search Value: Standby Reserved
Additional Filter: Status = Ready
Limit: 1
```

### **Step A2: Update Number Inventory (Assign to Sitter)**
**App**: Airtable - Update Record

```
Table: Number Inventory
Record ID: {{A1__record_id}}
Fields:
  - Lifecycle: Reserved Active
  - Assigned Sitter: [{{trigger__record_id}}]
  - Status: Ready
```

### **Step A3: Update Sitter (Link Number)**
**App**: Airtable - Update Record

```
Table: Sitters
Record ID: {{trigger__record_id}}
Fields:
  - Reserved Number: [{{A1__record_id}}]
  - Status: Active
  - Twilio Number: {{A1__PhoneNumber}}
```

### **Step A4: Purchase New Standby (Replenish)** ✅ NEW
**App**: Webhooks by Zapier - POST

```
URL: https://your-railway-app.railway.app/numbers/purchase
Method: POST
Headers:
  Content-Type: application/json
Body:
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
  "status": "pending",
  "twilio_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

### **Step A5: Send Welcome Email**
**App**: Gmail - Send Email

```
To: owner@example.com
Subject: Sitter Activated: {{trigger__Name}}
Body:
Sitter successfully activated!

Name: {{trigger__Name}}
Masked Number: {{A1__PhoneNumber}}
Real Phone: {{trigger__Phone Number}}
Status: Active

The sitter can now receive client messages through the masked number.

View Sitter: {{trigger__airtable_record_url}}
```

---

## PATH B: No Standby (Purchase New Reserved)

### **Step B1: Purchase Reserved Number** ✅ NEW
**App**: Webhooks by Zapier - POST

```
URL: https://your-railway-app.railway.app/numbers/purchase
Method: POST
Headers:
  Content-Type: application/json
Body:
{
  "lifecycle": "reserved",
  "area_code": "303",
  "sitter_id": "{{trigger__record_id}}"
}
```

**Expected Response**:
```json
{
  "success": true,
  "phone_number": "+13035551234",
  "number_inventory_id": "recXXXXXXXXXXXXXX",
  "status": "pending",
  "twilio_sid": "PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

### **Step B2: Update Sitter (Link Pending Number)**
**App**: Airtable - Update Record

```
Table: Sitters
Record ID: {{trigger__record_id}}
Fields:
  - Reserved Number: [{{B1__number_inventory_id}}]
  - Status: Pending
  - Twilio Number: {{B1__phone_number}}
```

### **Step B3: Send Pending Email**
**App**: Gmail - Send Email

```
To: owner@example.com
Subject: Sitter Number Pending: {{trigger__Name}}
Body:
New sitter added: {{trigger__Name}}

Reserved number purchased: {{B1__phone_number}}
Status: Pending verification

This number will be activated by Zap 3 within a few minutes.

Sitter Record: {{trigger__airtable_record_url}}
```

---

## PATH C: Remove Sitter (Convert to Standby)

### **Step C1: Find Sitter's Number**
**App**: Airtable - Find Record

```
Table: Number Inventory
Search Field: Assigned Sitter
Search Value: {{trigger__record_id}}
```

### **Step C2: Update Number Inventory (Release)**
**App**: Airtable - Update Record

```
Table: Number Inventory
Record ID: {{C1__record_id}}
Fields:
  - Lifecycle: Standby Reserved
  - Assigned Sitter: (clear/empty)
  - Status: Ready
```

### **Step C3: Update Sitter (Deactivate)**
**App**: Airtable - Update Record

```
Table: Sitters
Record ID: {{trigger__record_id}}
Fields:
  - Reserved Number: (clear/empty)
  - Status: Inactive
  - Twilio Number: (clear/empty)
```

---

## ✅ Requirements Verification

| Requirement | Path | Implementation | Status |
|-------------|------|----------------|--------|
| **Assign standby if available** | A | Steps A1-A3 | ✅ |
| **Replenish standby after assignment** | A | Step A4 (`/numbers/purchase` with `lifecycle=standby`) | ✅ |
| **Purchase new if no standby** | B | Step B1 (`/numbers/purchase` with `lifecycle=reserved`) | ✅ |
| **Send appropriate email** | A, B | Steps A5, B3 | ✅ |
| **Remove sitter → standby** | C | Steps C1-C3 | ✅ |

---

## 🎯 Key Updates from Original

| Feature | Old | New |
|---------|-----|-----|
| **Purchase Endpoint** | ❌ Not implemented | ✅ `/numbers/purchase` |
| **Path A Replenish** | ⚠️ Workaround needed | ✅ Direct API call |
| **Path B Purchase** | ⚠️ Workaround needed | ✅ Direct API call |
| **Sitter Linking** | Manual | ✅ Automatic via `sitter_id` |

---

## 🧪 Testing Checklist

### **Test Path A**:
1. Create standby number in Airtable (Lifecycle=Standby Reserved, Status=Ready)
2. Submit "Add New Sitter" form
3. **Verify**:
   - ✅ Standby assigned to sitter
   - ✅ Sitter Status = Active
   - ✅ Number Lifecycle = Reserved Active
   - ✅ New standby purchased (check Airtable)
   - ✅ Welcome email received

### **Test Path B**:
1. Delete all standby numbers
2. Submit "Add New Sitter" form
3. **Verify**:
   - ✅ New number purchased
   - ✅ Number Inventory created (Status=Pending)
   - ✅ Sitter Status = Pending
   - ✅ Pending email received
   - ✅ Zap 3 activates it (Status→Ready, Sitter→Active)

### **Test Path C**:
1. Create sitter with assigned number
2. Update sitter: Function = "Remove"
3. **Verify**:
   - ✅ Number unlinked from sitter
   - ✅ Sitter Status = Inactive
   - ✅ Number Lifecycle = Standby Reserved
   - ✅ Number ready for next sitter

---

## 🚀 Deployment Steps

1. **Update Zap 2** with this configuration
2. **Test Path A** (easiest to test)
3. **Test Path B** (requires Zap 3 working)
4. **Test Path C** (sitter removal)
5. **Enable Zap** for production

---

## 📋 Summary

**All requirements met**:
- ✅ Path A: Assign standby + replenish
- ✅ Path B: Purchase new reserved
- ✅ Path C: Remove sitter → standby
- ✅ Appropriate emails for each path
- ✅ Uses new `/numbers/purchase` endpoint
- ✅ Automatic sitter linking
- ✅ Zap 3 integration for activation

**No workarounds needed** - everything uses proper API endpoints! 🎉
