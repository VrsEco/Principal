from services import my_work_service


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
        self.last_query = None
        self.last_params = None

    def execute(self, query, params=None):
        self.last_query = query
        self.last_params = params

    def fetchall(self):
        return list(self._rows)


def test_fetch_normalized_project_rows_falls_back_when_optional_columns_are_missing(monkeypatch):
    fake_rows = [
        {
            "activity_id": 45,
            "activity_code": "AA.J.31.45",
            "activity_title": "Validar backlog MCP",
            "activity_description": "Corrigir leitura de atividades abertas.",
            "activity_status": "planned",
            "activity_stage": "inbox",
            "activity_priority": "high",
            "activity_deadline": None,
            "estimated_hours": 2,
            "worked_hours": 0,
            "amount": None,
            "metadata": None,
            "project_id": 31,
            "responsible_id": 9,
            "executor_id": None,
            "responsible_name": "Fabiano",
            "executor_name": None,
            "company_id": 9,
            "plan_id": None,
            "project_title": "Agentes de Work V3",
            "project_description": "Projeto técnico",
            "project_status": "planned",
            "project_priority": "high",
            "start_date": None,
            "end_date": None,
            "created_at": None,
            "updated_at": None,
            "project_code": "AA.J.31",
            "plan_name": None,
            "company_name": "AA - Versus Gestão Corporativa",
        }
    ]
    cursor = _FakeCursor(fake_rows)

    monkeypatch.setattr(my_work_service, "_fetch_v2_project_rows", lambda *args, **kwargs: [])
    monkeypatch.setattr(my_work_service, "_project_activities_table_available", lambda cursor: True)
    monkeypatch.setattr(my_work_service, "_fetch_project_rows_from_json", lambda *args, **kwargs: [])

    def _fake_has_column(_cursor, table_name, column_name):
        return {
            ("company_projects", "code"): True,
            ("project_activities", "code"): False,
            ("project_activities", "amount"): False,
            ("project_activities", "metadata"): False,
        }.get((table_name, column_name), True)

    monkeypatch.setattr(my_work_service, "_table_has_column", _fake_has_column)

    rows = my_work_service._fetch_normalized_project_rows(cursor, company_ids=[9])

    assert len(rows) == 1
    assert rows[0]["activity_code"] == "AA.J.31.45"
    assert rows[0]["project_code"] == "AA.J.31"
    assert "pa.code AS activity_code" not in cursor.last_query
    assert "pa.amount" not in cursor.last_query
    assert "pa.metadata" not in cursor.last_query
    assert "NULL AS amount" in cursor.last_query
    assert "NULL AS metadata" in cursor.last_query
