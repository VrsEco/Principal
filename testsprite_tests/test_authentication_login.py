"""
Teste de autenticação - Login endpoint
"""
import requests

BASE_URL = "http://localhost:5003"
LOGIN_ENDPOINT = "/auth/login"
TIMEOUT = 30

AUTH_CREDENTIALS = {"username": "admin@versus.com.br", "password": "123456"}


def test_authentication_login_endpoint():
    """Test the /auth/login POST endpoint for successful login with valid credentials, invalid data handling, and incorrect credentials response."""
    url = BASE_URL + LOGIN_ENDPOINT
    headers = {"Content-Type": "application/json"}

    # 1. Test successful login with valid credentials
    valid_payload = {
        "email": AUTH_CREDENTIALS["username"],
        "password": AUTH_CREDENTIALS["password"],
    }
    try:
        response = requests.post(
            url, json=valid_payload, headers=headers, timeout=TIMEOUT
        )
        assert (
            response.status_code == 200
        ), f"Expected status code 200, got {response.status_code}"
        json_data = response.json()
        assert "success" in json_data and json_data["success"] is True
        assert "message" in json_data
        assert "user" in json_data and isinstance(json_data["user"], dict)
    except Exception as e:
        raise AssertionError(f"Valid login test failed: {e}")

    # 2. Test invalid data handling (missing required fields)
    invalid_payloads = [
        ({}, 400),  # empty body - Bad Request
        (
            {"email": AUTH_CREDENTIALS["username"]},
            400,
        ),  # missing password - Bad Request
        (
            {"password": AUTH_CREDENTIALS["password"]},
            400,
        ),  # missing email - Bad Request
        ({"email": "", "password": ""}, 400),  # empty strings - Bad Request
        (
            {"email": "not_an_email", "password": "pass"},
            401,
        ),  # invalid email format - treated as invalid credentials
    ]
    for payload, expected_status in invalid_payloads:
        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=TIMEOUT
            )
            # API may return 400 for missing fields or 401 for invalid credentials
            assert (
                response.status_code == expected_status
            ), f"Expected {expected_status} for invalid payload {payload}, got {response.status_code}"
        except Exception as e:
            raise AssertionError(f"Invalid data test failed for payload {payload}: {e}")

    # 3. Test incorrect credentials response
    wrong_credentials_payload = {
        "email": AUTH_CREDENTIALS["username"],
        "password": "wrongpassword",
    }
    try:
        response = requests.post(
            url, json=wrong_credentials_payload, headers=headers, timeout=TIMEOUT
        )
        assert (
            response.status_code == 401
        ), f"Expected 401 for wrong credentials, got {response.status_code}"
    except Exception as e:
        raise AssertionError(f"Wrong credentials test failed: {e}")
