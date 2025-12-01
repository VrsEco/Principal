import requests
import json

url = "http://127.0.0.1:5003/api/companies/13/process-instances"
payload = {
    "process_id": 64,
    "title": "Test Instance",
    "description": "Created via reproduction script",
    "trigger_type": "manual",
    "priority": "normal"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
