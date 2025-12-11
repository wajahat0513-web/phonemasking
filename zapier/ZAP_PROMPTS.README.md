# Zapier Automation Prompts

## Overview

This directory contains step-by-step configuration guides for all 6 Zapier automations required for the Phone Masking system. These prompts are designed to be implementation-ready, providing exact field mappings, filter logic, and testing scenarios.

## Quick Reference

| Zap # | Name | Trigger | Primary Action | Railway Endpoint |
|-------|------|---------|----------------|------------------|
| 1 | Client Sync | Time to Pet Webhook | Airtable Upsert | None (Airtable only) |
| 2 | Sitter Provisioning | Airtable Form | Number Assignment | `POST /attach-number` |
| 3 | Number Verification | Airtable Update | Attach & Test Number | `POST /attach-number` |
| 4 | Pool Monitor | Schedule (48h) | Auto-Purchase Pool Number | `POST /inventory/check-and-replenish` ⚠️ |
| 5 | Standby Keeper | Schedule (48h) | Replenish Standby | `POST /numbers/standby-replenish` ⚠️ |
| 6 | Delivery Alerts | Twilio Callback | Error Handling & Alerts | None (Direct Twilio/Email) |

⚠️ = Endpoint requires implementation (see [ENDPOINTS_REFERENCE.md](ENDPOINTS_REFERENCE.md))

## File Structure

```
zapier/
├── ZAP_PROMPTS.README.md          # This file
├── ENDPOINTS_REFERENCE.md          # API endpoint documentation
├── zap_1_client_sync.md           # Client synchronization from Time to Pet
├── zap_2_sitter_provisioning.md   # New sitter onboarding & number assignment
├── zap_3_number_verification.md   # Number attachment verification
├── zap_4_pool_monitor.md          # Automated pool capacity management
├── zap_5_standby_keeper.md        # Standby number replenishment
└── zap_6_delivery_alerts.md       # Message delivery error handling
```

## General Setup Instructions

### Authentication Requirements

Before building any Zaps, ensure you have the following credentials configured in Zapier:

1. **Airtable**
   - Personal Access Token with read/write access to the Phone Masking base
   - Base ID and Table IDs for: Sitters, Clients, Number Inventory, Audit Log

2. **Twilio**
   - Account SID and Auth Token
   - Proxy Service SID
   - Messaging Service SID (for Zap 6)

3. **Railway** (Custom Webhooks)
   - Base URL: `https://your-railway-app.railway.app`
   - No authentication required (endpoints are public)

4. **Time to Pet** (Zap 1 only)
   - Webhook URL configuration in Time to Pet admin panel
   - API key (if required)

5. **Email Service** (Zaps 2, 6)
   - Gmail OAuth or SendGrid API key
   - Owner email address for notifications

### Testing Mode

All Zaps should be built and tested in **Draft Mode** before enabling:

1. Use Zapier's "Test" feature for each step
2. Verify data mapping with sample payloads
3. Check Airtable records are created/updated correctly
4. Confirm Railway endpoints return expected responses
5. Enable Zap only after successful end-to-end test

### Common Zapier Utilities

Several Zaps require these built-in Zapier tools:

- **Formatter by Zapier**: Phone number normalization to E.164 format
- **Filter by Zapier**: Conditional logic (utilization thresholds, error codes)
- **Delay by Zapier**: Retry delays (Zap 6)
- **Paths by Zapier**: Multi-branch logic (Zaps 2, 6)
- **Code by Zapier**: Custom calculations (Zap 4 utilization rate)

## Implementation Order

Build Zaps in this sequence to minimize dependencies:

1. **Zap 1** (Client Sync) - Populates Clients table
2. **Zap 3** (Number Verification) - Required by Zaps 2, 4, 5
3. **Zap 2** (Sitter Provisioning) - Depends on Zap 3
4. **Zap 5** (Standby Keeper) - Depends on Zaps 2 & 3
5. **Zap 4** (Pool Monitor) - Depends on Zap 3
6. **Zap 6** (Delivery Alerts) - Independent, can be built anytime

## Troubleshooting Guide

### Common Issues

**Issue**: Zap triggers but action fails with "Record not found"
- **Cause**: Airtable record ID is incorrect or record was deleted
- **Solution**: Use "Find Record" action before "Update Record" with fallback to "Create Record"

**Issue**: Railway endpoint returns 422 Unprocessable Entity
- **Cause**: Missing required fields or incorrect data format
- **Solution**: Check [ENDPOINTS_REFERENCE.md](ENDPOINTS_REFERENCE.md) for exact payload schema

**Issue**: Phone number validation fails
- **Cause**: Number not in E.164 format (+1XXXXXXXXXX)
- **Solution**: Add "Formatter by Zapier" step to normalize phone numbers

**Issue**: Zap 4/5 triggers too frequently
- **Cause**: Schedule interval is too short
- **Solution**: Verify schedule is set to "Every 48 hours" not "Every 48 minutes"

**Issue**: Duplicate records created in Airtable
- **Cause**: Using "Create Record" instead of "Update or Create Record"
- **Solution**: Switch to Airtable's "Find or Create" action with unique identifier

### Debug Checklist

When a Zap fails:

1. ✅ Check Zap History for error message
2. ✅ Verify all required fields are mapped (not empty)
3. ✅ Test Railway endpoint directly with curl/Postman
4. ✅ Check Airtable field types match data being sent
5. ✅ Review Audit Log table for system errors
6. ✅ Confirm authentication tokens are valid
7. ✅ Check Railway server logs for detailed errors

## Email Templates

### Sitter Welcome Email (Zap 2 - Path A & B)

**Subject**: Your Masked Phone Number is Ready

**Body**:
```
Hi [Sitter Name],

Your masked phone number has been successfully provisioned!

Masked Number: [Reserved Number]
Status: Active

Clients can now text you at this number, and all messages will be forwarded to your personal phone ([Sitter Real Phone]).

Important: Reply to client messages from your personal phone - the system will automatically route them through the masked number.

Questions? Contact support@pureinpet.com

Best,
Pure In Home Pet Sitting Team
```

### Number Assignment Failure Email (Zap 2 - Error Path)

**Subject**: Action Required: Sitter Number Assignment Failed

**Body**:
```
ALERT: Sitter number assignment failed

Sitter: [Sitter Name]
Email: [Sitter Email]
Error: [Error Message from Railway]

Action Required: Manually assign a number or investigate the error.

View Sitter Record: [Airtable Record URL]
```

### Systemic Failure Alert (Zap 6 - Path C)

**Subject**: URGENT: Multiple Message Delivery Failures Detected

**Body**:
```
SYSTEM ALERT: 5+ message delivery failures in the last 24 hours

This may indicate a systemic issue with Twilio or the Proxy Service.

Recent Failures:
[List of last 5 failures with error codes]

Action Required: 
1. Check Twilio Console for service status
2. Review Audit Log in Airtable
3. Verify Proxy Service configuration

View Audit Log: [Airtable Audit Log URL]
```

## Support

For questions about:
- **Zapier Configuration**: See individual Zap prompt files
- **Railway API**: See [ENDPOINTS_REFERENCE.md](ENDPOINTS_REFERENCE.md)
- **Airtable Schema**: See [airtabledatabaseschema.csv](../airtabledatabaseschema.csv)
- **Project Requirements**: See [PROJECT_REQUIREMENTS.md](../PROJECT_REQUIREMENTS.md)
- **Testing**: See [extras/COMPLETE_TEST_GUIDE.md](../extras/COMPLETE_TEST_GUIDE.md)

## Version History

- **v1.0** (2025-12-11): Initial documentation created
  - All 6 Zap prompts documented
  - Endpoints reference guide added
  - Email templates included
