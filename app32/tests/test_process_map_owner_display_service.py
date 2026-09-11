from types import SimpleNamespace

from services import process_map_owner_display_service as owner_display_service


def _map_data(owner="Ana"):
    return {"areas": [{"macros": [{"owner": owner}]}]}


def test_owner_display_employee_keeps_persisted_owner_without_database_query(monkeypatch):
    map_data = _map_data()
    monkeypatch.setattr(owner_display_service.db, "session", object())

    owner_display_service.apply_owner_display_mode(
        map_data,
        company_id=7,
        owner_display_mode="employee",
    )

    assert map_data["areas"][0]["macros"][0]["owner_display"] == "Ana"


def test_owner_display_role_queries_only_the_active_company(monkeypatch):
    captured = {}

    class FakeQuery:
        def outerjoin(self, *args):
            return self

        def filter(self, *args):
            captured["filters"] = args
            return self

        def order_by(self, *args):
            return self

        def all(self):
            return [("Ana", "Gerente de Operações")]

    monkeypatch.setattr(
        owner_display_service.db,
        "session",
        SimpleNamespace(query=lambda *args: FakeQuery()),
    )
    map_data = _map_data()

    owner_display_service.apply_owner_display_mode(
        map_data,
        company_id=7,
        owner_display_mode="role",
    )

    assert captured["filters"]
    assert map_data["areas"][0]["macros"][0]["owner_display"] == "Gerente de Operações"


def test_owner_display_role_does_not_fall_back_to_employee_name_when_role_is_missing(monkeypatch):
    class FakeQuery:
        def outerjoin(self, *args):
            return self

        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def all(self):
            return [("Ana", None)]

    monkeypatch.setattr(
        owner_display_service.db,
        "session",
        SimpleNamespace(query=lambda *args: FakeQuery()),
    )
    map_data = _map_data()

    owner_display_service.apply_owner_display_mode(
        map_data,
        company_id=7,
        owner_display_mode="role",
    )

    assert map_data["areas"][0]["macros"][0]["owner_display"] == "Cargo não informado"


def test_normalize_owner_display_mode_rejects_unknown_mode():
    try:
        owner_display_service.normalize_owner_display_mode("name-and-role")
    except ValueError as exc:
        assert str(exc) == "Modo de exibição do dono inválido."
    else:
        raise AssertionError("Modo desconhecido deve ser recusado.")
