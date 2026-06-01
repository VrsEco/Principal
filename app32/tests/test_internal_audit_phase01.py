from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (BASE_DIR / path).read_text(encoding="utf-8")


def test_internal_audit_spec_freezes_phase01_flow():
    spec = _read("docs/spec/auditoria_interna_fase_01_spec_v1.md")

    assert "Checklist\n→ execução\n→ ponto de auditoria\n→ papel de trabalho\n→ achado" in spec
    assert "→ projeto/atividade\n→ reunião de alinhamento\n→ relatório\n→ follow-up" in spec
    assert "Todas as consultas respeitarem `company_id`" in spec or "todas as consultas respeitarem `company_id`" in spec


def test_internal_audit_models_are_tenant_scoped():
    model = _read("models/internal_audit.py")

    for class_name in ["AuditArea", "AuditAuditor", "AuditChecklist", "AuditChecklistItem", "AuditSchedule"]:
        assert f"class {class_name}" in model
    assert model.count("company_id = db.Column") >= 5
    assert "description_for_report" in model
    assert "AUDIT_CHECKLIST_TYPES" in model


def test_internal_audit_routes_expose_phase01_catalogs():
    route = _read("api/routes/internal_audit.py")
    app_py = _read("app.py")

    assert "internal_audit_bp = Blueprint" in route
    assert '"/internal-audit/checklists"' in route
    assert '"/api/internal-audit/checklists"' in route
    assert '"/api/internal-audit/checklists/<int:checklist_id>/items"' in route
    assert "from api.routes.internal_audit import internal_audit_bp" in app_py
    assert "app.register_blueprint(internal_audit_bp)" in app_py


def test_internal_audit_sidebar_is_below_finance_and_before_sapiens():
    sidebar = _read("templates/partials/sidebar_standard.html")

    finance_index = sidebar.index("Gestão Financeira")
    audit_index = sidebar.index("Auditoria Interna")
    sapiens_index = sidebar.index("Sapiens")

    assert finance_index < audit_index < sapiens_index
    assert 'href="/internal-audit/checklists"' in sidebar
    assert 'href="/internal-audit/areas"' in sidebar
    assert 'href="/internal-audit/auditors"' in sidebar
