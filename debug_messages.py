
from services.airtable_client import messages_table

print("Fetching latest message records...")
# Helper to just get a few records
records = messages_table.all(max_records=5, sort=["-Timestamp"])

if not records:
    print("No records found in Messages table.")
else:
    print(f"Found {len(records)} records.")
    for r in records:
        f = r['fields']
        print(f"ID: {r['id']} | Status: '{f.get('Status')}' | Body: {f.get('Body')}")
