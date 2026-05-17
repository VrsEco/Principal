from pathlib import Path
import sys
from types import SimpleNamespace


ROOT_DIR = Path(r"C:\GestaoVersus\app32")
APP_ROOT = ROOT_DIR / "app32" if (ROOT_DIR / "app32").exists() else ROOT_DIR
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def test_admin_company_scope_keeps_unassigned_tasks_in_active_company(monkeypatch):
    from services.my_work import discovery_service

    fake_user = SimpleNamespace(id=3, role="admin")

    class _FakeUserQuery:
        def get(self, user_id):
            return fake_user if user_id == 3 else None

    class _FakeCompanyQuery:
        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return [SimpleNamespace(id=10, name="Empresa Teste Versus", client_code="M1", is_active=True)]

    monkeypatch.setattr(discovery_service, "User", SimpleNamespace(query=_FakeUserQuery()))
    monkeypatch.setattr(discovery_service, "Company", SimpleNamespace(query=_FakeCompanyQuery(), is_active=True))
    monkeypatch.setattr(discovery_service, "_get_active_associated_companies", lambda user_id: [{"company_id": 10, "employee_id": 88, "is_active": True}])
    monkeypatch.setattr(discovery_service, "_normalize_user_role", lambda user, company_ids=None: "admin")
    monkeypatch.setattr(discovery_service, "build_employee_lookup_v2", lambda company_ids: ({}, {}))
    monkeypatch.setattr(discovery_service, "fetch_normalized_process_rows", lambda **kwargs: [])
    monkeypatch.setattr(discovery_service, "can_access_company", lambda company_id: False)
    monkeypatch.setattr(
        discovery_service,
        "fetch_normalized_project_rows",
        lambda **kwargs: [
            {
                "id": 2505,
                "company_id": 10,
                "title": "Tarefa minha",
                "status": "planned",
                "deadline_date": "2026-05-16",
                "deadline": "2026-05-16",
                "type": "project",
                "responsible_id": 88,
                "executor_id": 88,
                "project_title": "[LAB M1] Projeto Base",
            },
            {
                "id": 2506,
                "company_id": 10,
                "title": "Tarefa empresa",
                "status": "planned",
                "deadline_date": "2026-05-16",
                "deadline": "2026-05-16",
                "type": "project",
                "responsible_id": None,
                "executor_id": None,
                "project_title": "[LAB M1] Projeto Base",
            },
        ],
    )

    activities, scope_counts = discovery_service.get_user_activities_v2(
        user_id=3,
        scope="company",
        filters={"delivery_tags": ["open"], "due_date_end": "2026-05-16"},
        company_ids=[10],
        active_company_id=10,
    )

    assert [item["id"] for item in activities] == [2505, 2506]
    assert scope_counts["company"] == 2
