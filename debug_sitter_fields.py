
from services.airtable_client import sitters_table

print("Fetching one Sitter record...")
records = sitters_table.all(max_records=1)

if not records:
    print("No records found in Sitters table.")
else:
    print("Fields in Sitters table:")
    for key in records[0]['fields'].keys():
        print(f" - '{key}'")
