
from services.airtable_client import inventory_table

print("Fetching all inventory records...")
records = inventory_table.all()

if not records:
    print("No records found in inventory table.")
else:
    print(f"Found {len(records)} records.")
    print("First record fields:")
    print(records[0]['fields'])
    
    print("\nChecking for pool candidates:")
    for r in records:
        f = r['fields']
        print(f"ID: {r['id']} | Lifecycle: {f.get('Lifecycle')} | Status: {f.get('Status')} | Phone: {f.get('PhoneNumber') or f.get('Phone Number')}")
