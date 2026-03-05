
import sys
import os
sys.path.append(os.getcwd())
from database.postgresql_db import list_integrations
try:
    items = list_integrations()
    print(f"COUNT: {len(items)}")
    for item in items:
        print(f"ID: {item['id']}, NAME: {item['name']}")
except Exception as e:
    print(f"ERROR: {e}")
