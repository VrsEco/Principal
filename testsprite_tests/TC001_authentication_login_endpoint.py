import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:5003"
LOGIN_ENDPOINT = "/auth/login"
TIMEOUT = 30

AUTH_CREDENTIALS = {
    "username": "admin@versus.com.br",
    "password": "123456"
}

def test_authentication_login_endpoint():
    url = BASE_URL + LOGIN_ENDPOINT
    headers = {"Content-Type": "application/json"}

    # 1. Test successful login with valid credentials
    valid_payload = {
        "email": AUTH_CREDENTIALS["username"],
        "password": AUTH_CREDENTIALS["password"]
    }
    try:
        response = requests.post(url, json=valid_payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        json_data = response.json()
        assert "success" in json_data and json_data["success"] is True
        assert "message" in json_data
        assert "user" in json_data and isinstance(json_data["user"], dict)
    except Exception as e:
        raise AssertionError(f"Valid login test failed: {e}")

    # 2. Test invalid data handling (missing required fields)
    invalid_payloads = [
        {},  # empty body
        {"email": "not_an_email", "password": "pass"},  # invalid email format
        {"email": AUTH_CREDENTIALS["username"]},  # missing password
        {"password": AUTH_CREDENTIALS["password"]},  # missing email
        {"email": "", "password": ""}  # empty strings
    ]
    for payload in invalid_payloads:
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
            # Expecting 400 Bad Request because of invalid data
            assert response.status_code == 400, f"Expected 400 for invalid payload {payload}, got {response.status_code}"
        except Exception as e:
            raise AssertionError(f"Invalid data test failed for payload {payload}: {e}")

    # 3. Test incorrect credentials response
    wrong_credentials_payload = {
        "email": AUTH_CREDENTIALS["username"],
        "password": "wrongpassword"
    }
    try:
        response = requests.post(url, json=wrong_credentials_payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 401, f"Expected 401 for wrong credentials, got {response.status_code}"
    except Exception as e:
        raise AssertionError(f"Wrong credentials test failed: {e}")

test_authentication_login_endpoint()