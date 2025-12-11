# Issue Analysis and Gap Report

This document outlines the discrepancies between the Client Requirements, the current Production API Usage (OpenAPI), and the actual Codebase implementation.

## 1. Missing Number Purchasing Logic (Critical)

*   **Requirement**: The project brief explicitly requires the system to "Purchase 34 Reserved numbers... Purchase exactly one new local Pool Number" via Zaps 4 & 5. It specifically mentions an **"Attach-Number Routine"** server handler that manages **Twilio API calls for purchasing**.
*   **Production API**: The OpenAPI spec shows `/attach-number` but its description only says "Assigns a new phone number to a Sitter". It **does not** list any endpoint for simply purchasing a number (e.g., `/numbers/purchase`) or inventory replenishment.
*   **Current Codebase**: `services/number_pool.py` and `routers/numbers.py` only fetch *available* numbers from Airtable. There is **zero code** to search for or buy numbers from Twilio.
*   **Action**: Create a new endpoint `/numbers/purchase` (or update `/attach-number` to handle purchase flags) and implement `services/twilio_proxy.py` logic to search and buy phone numbers + add them to Airtable.

## 2. Intercept Handler Missing Prepend Logic

*   **Requirement**: "Intercept Handler (Sitter Clarity): Prepends the client's name (e.g., [Client Name]: Hey...)".
*   **Production API**: The `/intercept` endpoint exists but its description says "Callback endpoint triggered for every message... details to Airtable". It does not mention message modification.
*   **Current Codebase**: `routers/intercept.py` simply logs the message and returns `{}`. It does not modify the message body or instruct Twilio to do so.
*   **Action**: Update `routers/intercept.py` to return the correct Twilio TwiML or JSON response that instructs the Proxy service to modify the message body with the `[Client Name]:` prefix.

## 3. Missing Zapier-Specific Automation Endpoints

*   **Requirement**: "Zap 4: Pool Capacity Monitor" and "Zap 5: Standby Keeper" need to trigger the server to buy numbers.
*   **Production API**: **Missing**. There is no endpoint for "Check Pool Health" or "Replenish Standby" that Zapier can call. Zapier can only call `/attach-number` which requires a `sitter_id`.
*   **Current Codebase**: No such logic exists.
*   **Action**: Implement endpoints like `POST /inventory/check-and-replenish` or `POST /numbers/standby-replenish` for Zapier to trigger.

## 4. Client Creation Race Condition

*   **Requirement**: "Zap 1 – Client Sync" handles client creation.
*   **Production API**: `/out-of-session` description: "Handles the initial contact...".
*   **Current Codebase**: `routers/sessions.py` also calls `create_client(From)`.
*   **Conflict**: If a client texts before Zap 1 runs, the system creates a "shell" client. When Zap 1 runs, it might duplicate or fail.
*   **Action**: Ensure `create_client` in `services/airtable_client.py` uses aggressive deduplication (Upsert logic) based on E.164 phone numbers.

## 5. Deprecated/Debug Endpoints in Production

*   **Observation**: The OpenAPI spec includes `/numbers/debug`.
*   **Issue**: Generally, debug endpoints should be disabled or protected in production to prevent leaking system state (inventory counts, etc.).
*   **Action**: Consider removing `/numbers/debug` or adding authentication.

## Summary of Required Changes

| Priority | Component | Task |
| :--- | :--- | :--- |
| 🚨 **High** | `services/twilio_proxy.py` | Add `search_and_purchase_number(area_code)` function. |
| 🚨 **High** | `routers/numbers.py` | Create logic to handle "Purchase New Number" requests (for Pool/Standby). |
| 🚨 **High** | `routers/intercept.py` | Implement message body modification (Prepend logic). |
| 🟡 **Medium** | `routers/sessions.py` | Refine Client creation logic to avoid race conditions with Zap 1. |
| 🟢 **Low** | `routers/numbers.py` | Secure or remove `/numbers/debug` from production build. |
