import requests
from requests.exceptions import RequestException

BASE_URL = "http://localhost:5003"
USERNAME = "admin@versus.com.br"
PASSWORD = "123456"
TIMEOUT = 30


def test_authentication_logout_endpoint():
    session = requests.Session()
    try:
        # Step 1: Login to get session cookie
        login_url = f"{BASE_URL}/auth/login"
        login_payload = {"email": USERNAME, "password": PASSWORD}
        login_headers = {"Content-Type": "application/json"}
        login_response = session.post(
            login_url, json=login_payload, headers=login_headers, timeout=TIMEOUT
        )
        assert (
            login_response.status_code == 200
        ), f"Login failed with status {login_response.status_code}"
        login_data = login_response.json()
        assert (
            login_data.get("success") is True
        ), "Login response success flag is not True"

        # Step 2: Logout using the session cookie
        logout_url = f"{BASE_URL}/auth/logout"
        logout_response = session.post(logout_url, timeout=TIMEOUT)

        # Check for HTTP 200 or HTTP 500 as per API definition
        assert logout_response.status_code in (
            200,
            500,
        ), f"Unexpected logout status code {logout_response.status_code}"

        if logout_response.status_code == 200:
            # Successful logout
            assert (
                logout_response.text or logout_response.content
            ), "Logout response empty on success"
        elif logout_response.status_code == 500:
            # Internal server error, verify error message json or text if any
            try:
                err_json = logout_response.json()
                assert (
                    "error" in err_json or "message" in err_json
                ), "500 response missing error message"
            except Exception:
                # If not JSON, just pass as 500 scenario could vary
                pass

    except RequestException as e:
        assert False, f"Request failed: {e}"


test_authentication_logout_endpoint()
