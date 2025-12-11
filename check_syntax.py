"""
Syntax Validation Script
Checks all modified Python files for syntax errors without running them
"""

import py_compile
import sys
from pathlib import Path

files_to_check = [
    "services/twilio_proxy.py",
    "services/airtable_client.py",
    "routers/numbers.py",
    "routers/intercept.py",
    "routers/sessions.py",
]

print("🔍 Checking Python syntax for modified files...\n")

errors = []
success_count = 0

for file_path in files_to_check:
    try:
        py_compile.compile(file_path, doraise=True)
        print(f"✅ {file_path} - OK")
        success_count += 1
    except py_compile.PyCompileError as e:
        print(f"❌ {file_path} - SYNTAX ERROR")
        print(f"   {e}")
        errors.append((file_path, str(e)))

print(f"\n📊 Results: {success_count}/{len(files_to_check)} files passed")

if errors:
    print("\n❌ Errors found:")
    for file_path, error in errors:
        print(f"\n{file_path}:")
        print(f"  {error}")
    sys.exit(1)
else:
    print("\n✅ All files have valid Python syntax!")
    sys.exit(0)
