from services.airtable_client import sitters_table
import json

def find_sitter():
    twilio_num = "+18046046355"
    # Clean version
    clean_num = "8046046355"
    
    # Try exact match first
    formula = f"{{Twilio Number}} = '{twilio_num}'"
    records = sitters_table.all(formula=formula)
    print(f"Searching for exact match '{twilio_num}': {len(records)} found")
    
    # Try search version
    formula = f"SEARCH('{clean_num}', {{Twilio Number}})"
    records = sitters_table.all(formula=formula)
    print(f"Searching for clean version '{clean_num}': {len(records)} found")
    
    if records:
        print("\nSitter data found:")
        print(json.dumps(records[0]['fields'], indent=2))
    else:
        print("\nListing first 5 sitters to check field values:")
        all_recs = sitters_table.all(max_records=5)
        for r in all_recs:
            print(f"- {r['fields'].get('Full Name', 'No Name')} | Twilio: {r['fields'].get('Twilio Number', 'N/A')}")

if __name__ == "__main__":
    find_sitter()
