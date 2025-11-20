import json
import requests

BASE_URL = "http://localhost:5003"
LOGIN_PAYLOAD = {"email": "admin@versus.com.br", "password": "123456"}

company_id = 13
plan_id = 8
employee_id = 12

endpoints = [
    ("GET", f"/api/companies/{company_id}", None, "Company profile"),
    ("GET", f"/api/companies/{company_id}/employees", None, "Employees list"),
    (
        "GET",
        f"/api/companies/{company_id}/employees/{employee_id}",
        None,
        "Employee detail (GET)",
    ),
    ("GET", f"/api/companies/{company_id}/mvv", None, "Company MVV"),
    (
        "GET",
        f"/api/companies/{company_id}/routine-tasks/overdue",
        None,
        "Routine overdue",
    ),
    (
        "GET",
        f"/api/companies/{company_id}/routine-tasks/upcoming",
        None,
        "Routine upcoming",
    ),
    ("GET", f"/api/relatorios/projetos/{company_id}", None, "Relatorio projetos API"),
]


def main():
    session = requests.Session()
    login_resp = session.post(f"{BASE_URL}/auth/login", json=LOGIN_PAYLOAD, timeout=30)
    print(f"Login status: {login_resp.status_code}")
    if login_resp.status_code != 200:
        print(login_resp.text)
        return
    for method, path, payload, label in endpoints:
        url = f"{BASE_URL}{path}"
        try:
            resp = session.request(method, url, json=payload, timeout=30)
            content_type = resp.headers.get("Content-Type", "")
            print(f"{label}: {method} {path} -> {resp.status_code}")
            if "application/json" in content_type:
                try:
                    data = resp.json()
                    snippet = json.dumps(data, indent=2, ensure_ascii=False)
                    print(snippet[:500])
                except Exception:
                    print(resp.text[:200])
            else:
                print(resp.text[:200])
        except requests.RequestException as exc:
            print(f"{label}: {method} {path} -> EXCEPTION {exc}")


if __name__ == "__main__":
    main()
