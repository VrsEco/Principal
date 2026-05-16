import src.intelligence.tools as tools_module


def test_system_company_user_tools_delegate_to_domain_modules(monkeypatch):
    calls = []

    monkeypatch.setattr(
        tools_module.system_ops_domain,
        "consult_rules",
        lambda query: calls.append(("consult", query)) or "rules-ok",
    )
    monkeypatch.setattr(
        tools_module.system_ops_domain,
        "query_database",
        lambda sql_query: calls.append(("query", sql_query)) or "query-ok",
    )
    monkeypatch.setattr(
        tools_module.system_ops_domain,
        "escalate_technical_issue",
        lambda error_description, context: calls.append(("escalate", error_description, context)) or "escalate-ok",
    )
    monkeypatch.setattr(
        tools_module.company_ops_domain,
        "update_company_status",
        lambda company_id, is_active, reason=None: calls.append(("company-status", company_id, is_active, reason)) or "company-ok",
    )
    monkeypatch.setattr(
        tools_module.company_ops_domain,
        "list_my_companies",
        lambda search_term=None: calls.append(("companies", search_term)) or "companies-ok",
    )
    monkeypatch.setattr(
        tools_module.company_ops_domain,
        "get_company_profile",
        lambda company_id=None: calls.append(("company-profile", company_id)) or "company-profile-ok",
    )
    monkeypatch.setattr(
        tools_module.company_ops_domain,
        "update_company_profile",
        lambda changes, company_id=None: calls.append(("company-update", changes, company_id)) or "company-update-ok",
    )
    monkeypatch.setattr(
        tools_module.company_ops_domain,
        "get_company_registration_diagnostics",
        lambda company_id=None: calls.append(("company-diagnostics", company_id)) or "company-diagnostics-ok",
    )
    monkeypatch.setattr(
        tools_module.user_ops_domain,
        "get_user_summary",
        lambda target_user=None, range="today": calls.append(("summary", target_user, range)) or "summary-ok",
    )
    monkeypatch.setattr(
        tools_module.user_ops_domain,
        "list_system_users",
        lambda: calls.append(("users",)) or "users-ok",
    )
    monkeypatch.setattr(
        tools_module.user_ops_domain,
        "register_system_user",
        lambda name, email, role="collaborator", whatsapp=None, telegram=None: calls.append(
            ("register", name, email, role, whatsapp, telegram)
        )
        or "register-ok",
    )
    monkeypatch.setattr(
        tools_module.user_ops_domain,
        "update_user_contacts",
        lambda user_id, whatsapp=None, telegram=None: calls.append(("contacts", user_id, whatsapp, telegram)) or "contacts-ok",
    )

    assert tools_module.consult_rules.func("policy") == "rules-ok"
    assert tools_module.query_database.func("SELECT * FROM projects") == "query-ok"
    assert tools_module.escalate_technical_issue.func("err", "ctx") == "escalate-ok"
    assert tools_module.update_company_status.func(31, True, "ok") == "company-ok"
    assert tools_module.list_my_companies.func("AA") == "companies-ok"
    assert tools_module.get_company_profile.func(31) == "company-profile-ok"
    assert tools_module.update_company_profile.func({"segment": "Serviços"}, 31) == "company-update-ok"
    assert tools_module.get_company_registration_diagnostics.func(31) == "company-diagnostics-ok"
    assert tools_module.get_user_summary.func("me", "week") == "summary-ok"
    assert tools_module.list_system_users.func() == "users-ok"
    assert tools_module.register_system_user.func("Ana", "ana@example.com", "client", "1", "ana") == "register-ok"
    assert tools_module.update_user_contacts.func(10, "2", "tg") == "contacts-ok"

    assert calls == [
        ("consult", "policy"),
        ("query", "SELECT * FROM projects"),
        ("escalate", "err", "ctx"),
        ("company-status", 31, True, "ok"),
        ("companies", "AA"),
        ("company-profile", 31),
        ("company-update", {"segment": "Serviços"}, 31),
        ("company-diagnostics", 31),
        ("summary", "me", "week"),
        ("users",),
        ("register", "Ana", "ana@example.com", "client", "1", "ana"),
        ("contacts", 10, "2", "tg"),
    ]
