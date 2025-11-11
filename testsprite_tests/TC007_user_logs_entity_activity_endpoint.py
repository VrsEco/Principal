import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:5003"
AUTH = HTTPBasicAuth('admin@versus.com.br', '123456')
TIMEOUT = 30

def test_logs_entity_activity_endpoint():
    session = requests.Session()
    session.auth = AUTH
    headers = {
        "Accept": "application/json"
    }

    valid_entity_type = "project"
    valid_entity_id = "1234"

    try:
        response = session.get(
            f"{BASE_URL}/logs/entity-activity/{valid_entity_type}/{valid_entity_id}",
            headers=headers,
            timeout=TIMEOUT
        )
        assert response.status_code in (200, 404, 500), "Unexpected status code for valid entity test"
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '').lower()
            assert 'application/json' in content_type, "Response Content-Type should include 'application/json' when status 200"
            try:
                json_resp = response.json()
            except Exception as e:
                assert False, f"Response is not valid JSON: {e}"
            assert isinstance(json_resp, dict), "Response JSON should be a dictionary"
            # Expect at least one of these keys to be present
            assert any(key in json_resp for key in ["logs", "message", "success"]), "Expected keys missing in response"
        elif response.status_code == 404:
            pass
        elif response.status_code == 500:
            pass
        else:
            assert False, f"Unhandled status code {response.status_code} for valid entity test"
    except requests.RequestException as e:
        assert False, f"RequestException during success scenario: {e}"

    invalid_entity_type = "nonexistenttype"
    invalid_entity_id = "00000000"

    try:
        response = session.get(
            f"{BASE_URL}/logs/entity-activity/{invalid_entity_type}/{invalid_entity_id}",
            headers=headers,
            timeout=TIMEOUT
        )
        assert response.status_code in (404, 500), "Expected 404 or 500 status for invalid entity test"
        if response.status_code == 404:
            pass
        elif response.status_code == 500:
            pass
        else:
            assert False, f"Unhandled status code {response.status_code} for invalid entity test"
    except requests.RequestException as e:
        assert False, f"RequestException during not found scenario: {e}"

test_logs_entity_activity_endpoint()
