import requests

BASE_URL = "http://127.0.0.1:5032/api"
# Note: You might need a valid session cookie if running this outside the browser
# But since I'm just verifying structure, I'll check if the endpoints exist.

def test_wizard_audit():
    try:
        # This will likely fail with 401/403 if not authenticated, 
        # but let's see if the route is registered and responding.
        resp = requests.get(f"{BASE_URL}/indicators/audit")
        print(f"Audit status: {resp.status_code}")
    except Exception as e:
        print(f"Error connecting: {e}")

if __name__ == "__main__":
    test_wizard_audit()
