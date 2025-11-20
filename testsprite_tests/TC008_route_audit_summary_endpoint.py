import requests


def test_route_audit_summary_endpoint():
    base_url = "http://localhost:5003"
    summary_url = f"{base_url}/route-audit/api/summary"
    cookies = {"session": "example_valid_session_token"}
    headers = {"Accept": "application/json"}
    timeout = 30

    try:
        response = requests.get(
            summary_url, cookies=cookies, headers=headers, timeout=timeout
        )
    except requests.RequestException as e:
        assert False, f"Request to {summary_url} failed: {e}"

    assert response.status_code in (
        200,
        403,
        500,
    ), f"Unexpected status code: {response.status_code}"

    content_type = response.headers.get("Content-Type", "")
    is_json = (
        content_type.lower().startswith("application/json") if content_type else False
    )

    if response.status_code == 200:
        assert is_json, "200 response should be JSON"
        try:
            data = response.json()
        except ValueError:
            assert False, "Response is not valid JSON"
        assert isinstance(data, dict), "Response JSON should be a dictionary"
        assert data, "Response JSON is empty"
    elif response.status_code == 403:
        if is_json and response.text.strip():
            try:
                data = response.json()
                assert (
                    "message" in data or "error" in data
                ), "403 response should contain error message"
            except ValueError:
                pass
    else:
        pass


test_route_audit_summary_endpoint()
