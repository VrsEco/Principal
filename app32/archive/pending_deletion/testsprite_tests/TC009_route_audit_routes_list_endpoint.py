import requests

BASE_URL = "http://localhost:5003"
TIMEOUT = 30

# Assuming session cookie is managed outside this test or to be set here before test
# For minimal fix, no auth parameter is passed, but could be modified to pass cookies={'session': '<valid_session_cookie>'}


def test_route_audit_routes_list_endpoint():
    url = f"{BASE_URL}/route-audit/api/routes"
    filters = ["all", "with_logging", "without_logging", "crud"]

    for filter_value in filters:
        try:
            response = requests.get(
                url, params={"filter": filter_value}, timeout=TIMEOUT
            )
        except requests.RequestException as e:
            assert False, f"Request failed for filter '{filter_value}': {e}"

        assert (
            response.status_code == 200
        ), f"Unexpected status code for filter '{filter_value}': {response.status_code}"

        try:
            response.json()
        except ValueError:
            assert False, f"Response is not valid JSON for filter '{filter_value}'."


test_route_audit_routes_list_endpoint()
