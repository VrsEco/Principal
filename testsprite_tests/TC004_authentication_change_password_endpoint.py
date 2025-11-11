import requests

BASE_URL = "http://localhost:5003"
AUTH_LOGIN_ENDPOINT = "/auth/login"
CHANGE_PASSWORD_ENDPOINT = "/auth/change-password"


def test_authentication_change_password_endpoint():
    session = requests.Session()
    timeout = 30

    # 1. Authenticate to get session cookie
    login_payload = {
        "email": "admin@versus.com.br",
        "password": "123456"
    }
    try:
        login_resp = session.post(
            BASE_URL + AUTH_LOGIN_ENDPOINT,
            json=login_payload,
            timeout=timeout
        )
        assert login_resp.status_code == 200, f"Login failed with status {login_resp.status_code}"
        login_data = login_resp.json()
        assert login_data.get("success") is True, "Login response success flag is not True"
        assert "session" in session.cookies, "Session cookie not set after login"

        # 2. Test successful password update
        valid_change_payload = {
            "current_password": "123456",
            "new_password": "newStrongP@ssw0rd"
        }
        resp = session.post(
            BASE_URL + CHANGE_PASSWORD_ENDPOINT,
            json=valid_change_payload,
            timeout=timeout
        )
        assert resp.status_code == 200, f"Change password success failed with status {resp.status_code}"

        # 3. Test validation failure: missing new_password
        invalid_payload_1 = {
            "current_password": "newStrongP@ssw0rd"
        }
        resp = session.post(
            BASE_URL + CHANGE_PASSWORD_ENDPOINT,
            json=invalid_payload_1,
            timeout=timeout
        )
        assert resp.status_code == 400, f"Expected 400 for missing new_password, got {resp.status_code}"

        # 4. Test validation failure: new_password too short or invalid (assuming <8 chars invalid)
        invalid_payload_2 = {
            "current_password": "newStrongP@ssw0rd",
            "new_password": "short"
        }
        resp = session.post(
            BASE_URL + CHANGE_PASSWORD_ENDPOINT,
            json=invalid_payload_2,
            timeout=timeout
        )
        assert resp.status_code == 400, f"Expected 400 for invalid new_password, got {resp.status_code}"

    finally:
        # Change password back to original if it was changed
        try:
            reset_payload = {
                "current_password": "newStrongP@ssw0rd",
                "new_password": "123456"
            }
            resp = session.post(
                BASE_URL + CHANGE_PASSWORD_ENDPOINT,
                json=reset_payload,
                timeout=timeout
            )
            assert resp.status_code == 200
        except Exception:
            pass

    # 5. Test unauthorized access - no session cookie
    no_auth_payload = {
        "current_password": "123456",
        "new_password": "anotherNewP@ss1"
    }
    no_auth_resp = requests.post(
        BASE_URL + CHANGE_PASSWORD_ENDPOINT,
        json=no_auth_payload,
        timeout=timeout
    )
    assert no_auth_resp.status_code == 401, f"Expected 401 unauthorized but got {no_auth_resp.status_code}"


test_authentication_change_password_endpoint()
