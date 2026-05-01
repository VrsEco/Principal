from types import SimpleNamespace

from services.process_code_repair_service import rebuild_process_hierarchy_codes


class _FakeQuery:
    def __init__(self, items):
        self._items = list(items)

    def filter_by(self, **kwargs):
        items = [
            item for item in self._items
            if all(getattr(item, key) == value for key, value in kwargs.items())
        ]
        return _FakeQuery(items)

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._items)

    def get(self, item_id):
        for item in self._items:
            if getattr(item, "id", None) == item_id:
                return item
        return None


class _FakeColumn:
    def asc(self):
        return self


def test_rebuild_process_hierarchy_codes_updates_area_macro_and_process_codes(monkeypatch):
    company = SimpleNamespace(id=9, client_code="AA")
    areas = [
        SimpleNamespace(id=37, company_id=9, code="AB.C.1", order_index=1),
        SimpleNamespace(id=38, company_id=9, code="AB.C.2", order_index=2),
    ]
    macros = [
        SimpleNamespace(id=157, company_id=9, area_id=37, code="AB.C.1.2", order_index=2),
        SimpleNamespace(id=160, company_id=9, area_id=38, code="AB.C.2.1", order_index=1),
    ]
    processes = [
        SimpleNamespace(id=1, company_id=9, macro_id=157, code="AB.C.1.2.1", order_index=1),
        SimpleNamespace(id=2, company_id=9, macro_id=160, code="AB.C.2.1.1", order_index=1),
    ]

    fake_company_model = SimpleNamespace(query=_FakeQuery([company]))
    fake_col = _FakeColumn()
    fake_area_model = SimpleNamespace(query=_FakeQuery(areas), order_index=fake_col, id=fake_col)
    fake_macro_model = SimpleNamespace(query=_FakeQuery(macros), area_id=fake_col, order_index=fake_col, id=fake_col)
    fake_process_model = SimpleNamespace(query=_FakeQuery(processes), macro_id=fake_col, order_index=fake_col, id=fake_col)
    committed = {"value": False}
    fake_db = SimpleNamespace(session=SimpleNamespace(commit=lambda: committed.__setitem__("value", True)))

    monkeypatch.setattr("services.process_code_repair_service.Company", fake_company_model)
    monkeypatch.setattr("services.process_code_repair_service.ProcessArea", fake_area_model)
    monkeypatch.setattr("services.process_code_repair_service.MacroProcess", fake_macro_model)
    monkeypatch.setattr("services.process_code_repair_service.Process", fake_process_model)
    monkeypatch.setattr("services.process_code_repair_service.db", fake_db)

    result = rebuild_process_hierarchy_codes(9)

    assert committed["value"] is True
    assert result["company_code"] == "AA"
    assert areas[0].code == "AA.C.1"
    assert areas[1].code == "AA.C.2"
    assert macros[0].code == "AA.C.1.2"
    assert macros[1].code == "AA.C.2.1"
    assert processes[0].code == "AA.C.1.2.1"
    assert processes[1].code == "AA.C.2.1.1"
