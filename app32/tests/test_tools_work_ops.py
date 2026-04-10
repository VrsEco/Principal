from src.intelligence import tools as tools_module


def test_tools_get_my_work_wrapper_delegates_to_work_domain(monkeypatch) -> None:
    called = {}

    def _fake_get_my_work(*, scope="me", company_ids=None, search_term=None):
        called.update({"scope": scope, "company_ids": company_ids, "search_term": search_term})
        return "ok"

    monkeypatch.setattr(tools_module.work_ops_domain, "get_my_work", _fake_get_my_work)

    assert tools_module.get_my_work.func(scope="team", company_ids="12", search_term="Ana") == "ok"
    assert called == {"scope": "team", "company_ids": "12", "search_term": "Ana"}
