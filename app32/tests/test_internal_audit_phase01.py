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

    for class_name in [
        "AuditArea",
        "AuditAuditor",
        "AuditChecklist",
        "AuditChecklistItem",
        "AuditSchedule",
        "AuditExecution",
        "AuditExecutionItem",
        "AuditPoint",
        "AuditWorkpaper",
        "AuditFinding",
        "AuditEvidenceLink",
        "AuditReport",
        "AuditFollowUp",
    ]:
        assert f"class {class_name}" in model
    assert model.count("company_id = db.Column") >= 13
    assert "description_for_report" in model
    assert "AUDIT_CHECKLIST_TYPES" in model
    assert "__tablename__ = \"audit_executions\"" in model
    assert "__tablename__ = \"audit_execution_items\"" in model
    assert "__tablename__ = \"audit_points\"" in model
    assert "__tablename__ = \"audit_workpapers\"" in model
    assert "__tablename__ = \"audit_findings\"" in model
    assert "__tablename__ = \"audit_evidence_links\"" in model
    assert "__tablename__ = \"audit_reports\"" in model
    assert "__tablename__ = \"audit_follow_ups\"" in model


def test_internal_audit_routes_expose_phase01_catalogs():
    route = _read("api/routes/internal_audit.py")
    app_py = _read("app.py")

    assert "internal_audit_bp = Blueprint" in route
    assert '"/internal-audit/checklists"' in route
    assert '"/internal-audit/executions"' in route
    assert '"/internal-audit/points"' in route
    assert '"/internal-audit/workpapers"' in route
    assert '"/internal-audit/findings"' in route
    assert '"/internal-audit/reports"' in route
    assert '"/internal-audit/follow-ups"' in route
    assert '"/api/internal-audit/checklists"' in route
    assert '"/api/internal-audit/checklists/<int:checklist_id>/items"' in route
    assert '"/api/internal-audit/executions"' in route
    assert '"/api/internal-audit/execution-items/<int:execution_item_id>"' in route
    assert '"/api/internal-audit/points"' in route
    assert '"/api/internal-audit/workpapers"' in route
    assert '"/api/internal-audit/findings"' in route
    assert '"/api/internal-audit/evidence-links"' in route
    assert '"/api/internal-audit/reports"' in route
    assert '"/api/internal-audit/follow-ups"' in route
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
    assert 'href="/internal-audit/executions"' in sidebar
    assert 'href="/internal-audit/points"' in sidebar
    assert 'href="/internal-audit/workpapers"' in sidebar
    assert 'href="/internal-audit/findings"' in sidebar
    assert 'href="/internal-audit/reports"' in sidebar
    assert 'href="/internal-audit/follow-ups"' in sidebar


def test_internal_audit_wave2_service_generates_points_from_exceptions():
    service = _read("services/internal_audit_service.py")

    assert "def create_execution" in service
    assert "def update_execution_item" in service
    assert "def _ensure_point_for_execution_item" in service
    assert "status in {\"qualified_conforming\", \"non_conforming\"}" in service
    assert "origin_type=\"checklist\"" in service
    assert "subject_type=\"audit_execution_item\"" in service


def test_internal_audit_wave2_templates_exist():
    for template in [
        "templates/modules/internal_audit/executions.html",
        "templates/modules/internal_audit/execution_detail.html",
        "templates/modules/internal_audit/points.html",
    ]:
        content = _read(template)
        assert "Onda 2" in content
        assert "/api/internal-audit/" in content


def test_internal_audit_wave3_service_formalizes_workpapers_findings_and_remediation_links():
    service = _read("services/internal_audit_service.py")

    assert "def create_workpaper" in service
    assert "def create_finding" in service
    assert "def update_finding" in service
    assert "def create_evidence_link" in service
    assert "point.status = \"converted_to_finding\"" in service
    assert "project_id" in service
    assert "task_id" in service
    assert "_validate_project_link" in service
    assert "_validate_task_link" in service
    assert "company_id=company_id" in service


def test_internal_audit_wave3_templates_exist():
    for template in [
        "templates/modules/internal_audit/workpapers.html",
        "templates/modules/internal_audit/findings.html",
    ]:
        content = _read(template)
        assert "Onda 3" in content
        assert "/api/internal-audit/" in content


def test_internal_audit_wave4_service_versions_reports_and_tracks_followups():
    service = _read("services/internal_audit_service.py")

    assert "def create_report" in service
    assert "def update_report" in service
    assert "def issue_report" in service
    assert "def _build_report_snapshot" in service
    assert "Relatório emitido é imutável" in service
    assert 'previous_issued.status = "superseded"' in service
    assert "def create_follow_up" in service
    assert "AUDIT_FOLLOW_UP_STATUSES" in service
    assert "company_id=company_id" in service


def test_internal_audit_wave4_templates_exist():
    for template in [
        "templates/modules/internal_audit/reports.html",
        "templates/modules/internal_audit/follow_ups.html",
        "templates/modules/internal_audit/report_print.html",
    ]:
        content = _read(template)
        assert "Onda 4" in content or "Documento controlado" in content
        assert "/api/internal-audit/" in content or "window.print()" in content
