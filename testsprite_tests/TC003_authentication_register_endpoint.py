import requests

BASE_URL = "http://localhost:5003"
AUTH_REGISTER_URL = f"{BASE_URL}/auth/register"
AUTH_LOGIN_URL = f"{BASE_URL}/auth/login"

ADMIN_USERNAME = "admin@versus.com.br"
ADMIN_PASSWORD = "123456"


def test_authentication_register_endpoint():
    session = requests.Session()
    try:
        # Step 1: Authenticate as admin to obtain session cookie
        login_payload = {
            "email": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "remember": False
        }
        login_resp = session.post(AUTH_LOGIN_URL, json=login_payload, timeout=30)
        assert login_resp.status_code == 200, "Admin login failed"
        login_data = login_resp.json()
        assert login_data.get("success") is True, "Admin login unsuccessful"

        headers = {
            "Content-Type": "application/json"
        }

        # Step 2: Test successful user creation
        new_user_payload = {
            "email": "testuser_register@example.com",
            "password": "StrongPassw0rd!",
            "remember": False
        }

        # Try creating user successfully
        resp = session.post(AUTH_REGISTER_URL, json=new_user_payload, headers=headers, timeout=30)
        assert resp.status_code == 200, f"Expected 200 status for user creation, got {resp.status_code}"
        resp_json = resp.json()
        assert resp_json.get("success", True), "User creation response does not indicate success"

        # Step 3: Test user creation with invalid data
        invalid_payloads = [
            {},  # empty payload
            {"email": "not-an-email", "password": "123456"},  # invalid email format
            {"email": "user@example.com"},  # missing password
            {"password": "nopasswordfield"},  # missing email
            {"email": "", "password": "pass"},  # empty email
            {"email": "user@example.com", "password": ""},  # empty password
        ]

        for invalid_data in invalid_payloads:
            resp_invalid = session.post(AUTH_REGISTER_URL, json=invalid_data, headers=headers, timeout=30)
            assert resp_invalid.status_code == 400, (
                f"Expected 400 status for invalid data {invalid_data}, got {resp_invalid.status_code}"
            )

        # Step 4: Test permission check by using a new session without login (no auth)
        session_no_auth = requests.Session()
        resp_no_auth = session_no_auth.post(AUTH_REGISTER_URL, json=new_user_payload, headers=headers, timeout=30)
        # According to PRD, 403 is "Access denied" - no valid session means no permission
        assert resp_no_auth.status_code == 403, f"Expected 403 status for unauthorized access, got {resp_no_auth.status_code}"

    finally:
        # Cleanup created user (if possible) - since no user DELETE API is documented,
        # and no resource ID returned, this step is omitted.
        # In a real environment, there should be a way to delete test user after creation.
        session.close()


test_authentication_register_endpoint()
