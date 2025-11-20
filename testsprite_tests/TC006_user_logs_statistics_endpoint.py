import requests

BASE_URL = "http://localhost:5003"
SESSION_COOKIE = "your_valid_session_cookie_value"
TIMEOUT = 30


def test_user_logs_statistics_endpoint():
    url = f"{BASE_URL}/logs/stats"
    params = {"company_id": 1, "days": 30}
    cookies = {"session": SESSION_COOKIE}
    try:
        response = requests.get(url, cookies=cookies, params=params, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert (
        response.status_code == 200
    ), f"Expected status code 200, got {response.status_code}"
    if response.content:
        try:
            data = response.json()
        except ValueError:
            assert False, "Response is not valid JSON"
        assert isinstance(data, dict), "Response JSON should be an object"
        assert data, "Response JSON is empty"
    else:
        # Empty response is acceptable as per PRD absence of explicit JSON
        pass


test_user_logs_statistics_endpoint()
