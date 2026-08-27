from types import SimpleNamespace


class _QuerySpy:
    def __init__(self):
        self.criteria = []

    def join(self, *args, **kwargs):
        return self

    def outerjoin(self, *args, **kwargs):
        return self

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        return self

    def all(self):
        return []


class _SessionSpy:
    def __init__(self, query):
        self.query_spy = query

    def query(self, *args, **kwargs):
        return self.query_spy


def test_fetch_normalized_project_rows_excludes_soft_deleted_tasks(monkeypatch):
    from services.my_work import project_service

    query = _QuerySpy()
    monkeypatch.setattr(
        project_service,
        "db",
        SimpleNamespace(session=_SessionSpy(query)),
    )
    monkeypatch.setattr(
        project_service,
        "fetch_project_rows_from_json",
        lambda **kwargs: [],
    )

    rows = project_service.fetch_normalized_project_rows(company_ids=[9])

    assert rows == []
    compiled_criteria = " ".join(str(criterion) for criterion in query.criteria)
    assert "project_tasks.is_deleted IS false" in compiled_criteria
