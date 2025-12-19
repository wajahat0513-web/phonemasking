
from services.airtable_client import messages_table

print("Fetching one message record...")
records = messages_table.all(max_records=1)

if not records:
    print("No records found.")
else:
    print("Fields in Messages table:")
    for key in records[0]['fields'].keys():
        print(f" - '{key}'")
