import requests

BASE_URL = "http://localhost:5003"
USERNAME = "admin@versus.com.br"
PASSWORD = "123456"
TIMEOUT = 30

def test_user_logs_list_endpoint():
    session = requests.Session()
    # Perform login to get session cookie
    login_url = f"{BASE_URL}/auth/login"
    login_payload = {
        "email": USERNAME,
        "password": PASSWORD
    }
    headers = {"Accept": "application/json"}

    login_response = session.post(login_url, json=login_payload, headers=headers, timeout=TIMEOUT)
    assert login_response.status_code == 200, f"Login failed with status code {login_response.status_code}"
    login_json = login_response.json()
    assert login_json.get("success") is True, "Login did not succeed"

    # Define a set of query parameters to test pagination and filters
    test_queries = [
        {},  # no filters
        {"limit": 10, "offset": 0},
        {"limit": 5, "offset": 10},
        {"entity_type": "project"},
        {"action": "create"},
        {"user_id": 1},
        {"company_id": 1},
        {"entity_type": "task", "action": "update", "limit": 3, "offset": 2},
    ]

    url = f"{BASE_URL}/logs/"

    for params in test_queries:
        try:
            response = session.get(url, headers=headers, params=params, timeout=TIMEOUT)
            assert response.status_code == 200, f"Expected 200 but got {response.status_code} for params {params}"

            json_data = response.json()
            assert isinstance(json_data, dict), "Response is not a JSON object"
            assert "success" in json_data, "'success' field missing in response"
            assert json_data["success"] is True, "'success' field is not True"
            assert "logs" in json_data, "'logs' field missing in response"
            assert isinstance(json_data["logs"], list), "'logs' is not a list"
            assert "pagination" in json_data, "'pagination' field missing in response"
            assert isinstance(json_data["pagination"], dict), "'pagination' is not an object"
        except requests.exceptions.RequestException as e:
            assert False, f"Request failed: {e}"
        except (ValueError, AssertionError) as e:
            assert False, f"Response validation failed: {e}"

test_user_logs_list_endpoint()
