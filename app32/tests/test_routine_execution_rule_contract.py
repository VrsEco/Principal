from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ui_exposes_execution_modes_roles_and_triggers():
    template = (ROOT / "templates" / "routine_details.html").read_text(encoding="utf-8")

    assert 'value="scheduled"' in template
    assert 'value="triggered"' in template
    assert 'value="hybrid"' in template
    assert 'id="responsibleRoleId"' in template
    assert 'id="executorRoleRows"' in template
    assert 'id="triggerRows"' in template
    assert '/execution-rule`' in template
    assert '/routine-trigger-events/${eventId}/confirm' in template


def test_migration_is_tenant_scoped_and_has_idempotency_constraint():
    migration = (ROOT / "migrations" / "versions" / "20260901_1900_routine_roles_and_triggers.py").read_text(
        encoding="utf-8"
    )

    assert "routine_role_assignments" in migration
    assert "routine_triggers" in migration
    assert "routine_trigger_events" in migration
    assert "company_id" in migration
    assert "uq_routine_trigger_event_key" in migration


def test_http_contract_keeps_explicit_company_permission_guards():
    routes = (ROOT / "api" / "routes" / "processes.py").read_text(encoding="utf-8")

    assert "has_permission(company_id, 'processes', 'view')" in routes
    assert "has_permission(company_id, 'processes', 'create')" in routes
    assert routes.count("has_company_full_access(company_id)") >= 2


def test_new_trigger_is_not_flushed_before_required_fields_are_assigned():
    service = (ROOT / "services" / "routine_execution_rule_service.py").read_text(encoding="utf-8")
    save_rule_body = service.split("def save_execution_rule", 1)[1].split("def dispatch_routine_event", 1)[0]

    assert "db.session.flush()" not in save_rule_body
    assert 'trigger.trigger_code = item["trigger_code"]' in save_rule_body
    assert 'trigger.name = item["name"]' in save_rule_body
