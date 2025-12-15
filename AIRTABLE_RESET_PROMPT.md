# Airtable AI - Complete Database Reset Prompt

## 🤖 Copy and Paste This Into Airtable AI

```
Delete all records from the following tables:
- Sitters
- Clients  
- Number Inventory
- Messages
- Audit Log

Then create the following test data exactly as specified:

---

SITTERS TABLE - Create 3 records:

Record 1:
- Name: "Sarah Johnson"
- Phone Number: "+13035550001"
- Email: "sarah@example.com"
- Status: "Active"
- Twilio Number: "+18046046355"
- Reserved Number: Link to Number Inventory record with PhoneNumber "+18046046355"

Record 2:
- Name: "Mike Davis"
- Phone Number: "+13035550002"
- Email: "mike@example.com"
- Status: "Pending"
- Twilio Number: (empty)
- Reserved Number: (empty)

Record 3:
- Name: "Emma Wilson"
- Phone Number: "+13035550003"
- Email: "emma@example.com"
- Status: "Inactive"
- Twilio Number: (empty)
- Reserved Number: (empty)

---

CLIENTS TABLE - Create 5 records:

Record 1:
- Name: "Alice Brown"
- Phone Number: "+13035550101"
- Created At: 2025-12-11

Record 2:
- Name: "Bob Martinez"
- Phone Number: "+13035550102"
- Created At: 2025-12-11

Record 3:
- Name: "Carol Davis"
- Phone Number: "+13035550103"
- Created At: 2025-12-11

Record 4:
- Name: "David Lee"
- Phone Number: "+13035550104"
- Created At: 2025-12-11

Record 5:
- Name: "Eva Garcia"
- Phone Number: "+13035550105"
- Created At: 2025-12-11

---

NUMBER INVENTORY TABLE - Create 4 records:

Record 1:
- PhoneNumber: "+18046046355"
- Lifecycle: "Reserved Active"
- Status: "Ready"
- Purchase Date: 2025-12-10
- Twilio SID: "PN1234567890abcdef1234567890abcd"
- Proxy Phone SID: "PN1234567890abcdef1234567890abcd"
- Attach Status: "Ready"
- Assigned Sitter: Link to Sitter "Sarah Johnson"

Record 2:
- PhoneNumber: "+17205864405"
- Lifecycle: "Pool"
- Status: "Pending"
- Purchase Date: 2025-12-11
- Twilio SID: "PN2234567890abcdef1234567890abcd"
- Proxy Phone SID: (empty)
- Attach Status: "Pending"
- Assigned Sitter: (empty)

Record 3:
- PhoneNumber: "+19522484813"
- Lifecycle: "Pool"
- Status: "Ready"
- Purchase Date: 2025-12-10
- Twilio SID: "PN3234567890abcdef1234567890abcd"
- Proxy Phone SID: "PN3234567890abcdef1234567890abcd"
- Attach Status: "Ready"
- Assigned Sitter: (empty)

Record 4:
- PhoneNumber: "+18335709378"
- Lifecycle: "Standby Reserved"
- Status: "Ready"
- Purchase Date: 2025-12-10
- Twilio SID: "PN4234567890abcdef1234567890abcd"
- Proxy Phone SID: "PN4234567890abcdef1234567890abcd"
- Attach Status: "Ready"
- Assigned Sitter: (empty)

---

MESSAGES TABLE - Leave empty

AUDIT LOG TABLE - Leave empty

---

IMPORTANT NOTES:
1. Use ONLY the phone numbers listed above (these are your actual Twilio numbers)
2. Ensure all linked records are properly connected
3. All phone numbers must be in E.164 format (+1XXXXXXXXXX)
4. Lifecycle values must match exactly: "Reserved Active", "Pool", or "Standby Reserved"
5. Status values must be either "Pending" or "Ready"
```

---

## ✅ After Running This Command

Your Airtable will have:

**Sitters (3 records)**:
- ✅ Sarah Johnson: Active with assigned number
- ✅ Mike Davis: Pending, ready for Zap 2 testing
- ✅ Emma Wilson: Inactive

**Clients (5 records)**:
- ✅ 5 test clients with valid phone numbers

**Number Inventory (4 records)**:
- ✅ 1 Reserved Active (assigned to Sarah)
- ✅ 1 Pool Pending (for Zap 3 testing)
- ✅ 1 Pool Ready
- ✅ 1 Standby Reserved (for Zap 2 Path A testing)

**Messages**: Empty (will be populated by system)

**Audit Log**: Empty (will be populated by system)

---

## 🧪 Ready for Testing

After this reset, you can immediately test:

1. **Zap 3**: Use +17205864405 (Pool, Pending)
2. **Zap 2 Path A**: Use Mike Davis (will get standby +18335709378)
3. **Zap 2 Path B**: Delete standby, add new sitter
4. **Zap 2 Path C**: Use Emma Wilson (remove sitter)

---

## ⚠️ Important

**Before running**: Make sure these phone numbers exist in your Twilio account:
- +18046046355
- +17205864405
- +19522484813
- +18335709378

If any don't exist, replace them with numbers you actually own in Twilio.
