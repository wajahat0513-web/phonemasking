
from services.airtable_client import clients_table

print("Fetching latest client records...")
records = clients_table.all(max_records=1, sort=["-Created At"])

if not records:
    print("No records found in Clients table.")
else:
    print(f"Found {len(records)} records.")
    r = records[0]
    print(f"ID: {r['id']}")
    print("Fields found:")
    for key in r['fields'].keys():
        print(f" - '{key}'")
