import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import urgent_business_review as ubr_route


class _Row:
    def __init__(self, **payload):
        self.payload = payload

    def to_dict(self):
        return dict(self.payload)


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
    )
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    app.jinja_env.globals["static_asset_version"] = lambda path: "test"
    app.jinja_env.globals["has_permission"] = lambda *args, **kwargs: False
    app.jinja_env.globals["is_platform_admin"] = lambda: False
    app.jinja_env.globals["real_estate_auctions_enabled"] = lambda: False
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return None

    for endpoint in [
        "auth.profile",
        "configs.system_settings",
        "plans.plans_list",
        "usuarios.index",
        "main.efficiency_analysis",
        "main.efficiency_analysis_company",
        "meetings.meetings_manage_root",
        "portfolios.portfolios_page_redirect",
        "processes.bpms_analysis_redirect",
        "processes.process_instances_redirect",
        "processes.process_map",
        "processes.process_occurrences_redirect",
        "processes.process_portal_redirect",
        "processes.process_routines_analysis_page",
        "processes.process_routines_redirect",
        "processes.processes_list",
        "projects.project_analysis",
        "projects.projects_list",
        "work_journey.work_journey_redirect",
    ]:
        app.add_url_rule(f"/__test/{endpoint.replace('.', '/')}", endpoint=endpoint, view_func=lambda: "")
    app.register_blueprint(ubr_route.urgent_business_review_bp)
    return app


def test_consultive_cockpit_uses_active_company_not_request_company(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=42, name="Cliente A")
    captured = {}

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    def _fake_get_cockpit(*, company_id, limit=20):
        captured["company_id"] = company_id
        captured["limit"] = limit
        return {"company_id": company_id, "summary": {"urgent_needs_open": 0}}

    monkeypatch.setattr(ubr_route.BusinessReviewReadModelService, "get_cockpit", _fake_get_cockpit)

    response = app.test_client().get("/api/consultive/cockpit?company_id=999&limit=7")

    assert response.status_code == 200
    assert captured == {"company_id": 42, "limit": 7}
    assert response.get_json()["company_id"] == 42


def test_consultive_structural_front_analysis_uses_active_company(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=42, name="Cliente A")
    captured = {}

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    def _fake_get_structural_front_analysis(*, company_id, front_key):
        captured["company_id"] = company_id
        captured["front_key"] = front_key
        return {
            "company_id": company_id,
            "front": front_key,
            "action": "analyze_front",
            "state": "draft",
            "human_gate_required": True,
        }

    monkeypatch.setattr(
        ubr_route.BusinessReviewReadModelService,
        "get_structural_front_analysis",
        _fake_get_structural_front_analysis,
    )

    response = app.test_client().get("/api/consultive/cockpit/structural-fronts/processes/analysis?company_id=999")

    assert response.status_code == 200
    assert captured == {"company_id": 42, "front_key": "processes"}
    assert response.get_json()["front"] == "processes"


def test_create_urgent_need_uses_active_company_and_write_gate(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=42, name="Cliente A")
    captured = {}

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)
    monkeypatch.setattr(ubr_route, "has_company_full_access", lambda company_id: company_id == 42)

    def _fake_create_urgent_need(**kwargs):
        captured.update(kwargs)
        return _Row(id=10, company_id=kwargs["company_id"], title=kwargs["title"])

    monkeypatch.setattr(ubr_route.UrgentNeedService, "create_urgent_need", _fake_create_urgent_need)

    response = app.test_client().post(
        "/api/consultive/urgent-needs",
        json={
            "company_id": 999,
            "title": "Autuação fiscal",
            "project_id": 123,
            "urgency_level": "critical",
        },
    )

    assert response.status_code == 201
    assert captured["company_id"] == 42
    assert captured["title"] == "Autuação fiscal"
    assert captured["project_id"] == 123
    assert response.get_json()["company_id"] == 42


def test_project_task_tenant_contract_validates_via_project_company():
    source_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "services",
            "urgent_business_review_common.py",
        )
    )
    with open(source_path, "r", encoding="utf-8") as handle:
        source = handle.read()

    assert "ProjectTask.query.join(Project, Project.id == ProjectTask.project_id)" in source
    assert ".filter(Project.company_id == company_id)" in source
    assert ".filter(ProjectTask.is_deleted.is_(False))" in source


def test_urgent_need_route_keeps_business_rules_in_services():
    source_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "api",
            "routes",
            "urgent_business_review.py",
        )
    )
    with open(source_path, "r", encoding="utf-8") as handle:
        source = handle.read()

    assert "UrgentNeedService.create_urgent_need" in source
    assert "BusinessReviewService.create_review" in source
    assert "StructuralLearningService.create_learning_link" in source
    assert "BusinessReviewReadModelService.get_cockpit" in source
    assert "db.session" not in source


def test_financial_ref_id_does_not_satisfy_canonical_link_contract():
    source_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "services",
            "urgent_business_review_common.py",
        )
    )
    with open(source_path, "r", encoding="utf-8") as handle:
        source = handle.read()

    link_block = source.split("links = {", 1)[1].split("}", 1)[0]
    assert "financial_ref_id" not in link_block
    assert 'links["financial_ref_id"] = financial_ref_id' in source


def test_migration_requires_non_empty_risk_acceptance_reason():
    migration_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "versions",
            "20260630_1845_create_urgent_business_review_overlays.py",
        )
    )
    with open(migration_path, "r", encoding="utf-8") as handle:
        source = handle.read()

    assert "financial_ref_id IS NOT NULL" not in source
    assert "btrim(risk_acceptance_reason) <> ''" in source
    assert "btrim(accepted_risk_reason) <> ''" in source


def test_consultive_cockpit_page_renders_minimal_shell(monkeypatch):
    app = _build_app()

    class _Company:
        id = 42
        name = "Cliente A"
        client_code = "CLA"

        def to_dict(self):
            return {"id": self.id, "name": self.name, "client_code": self.client_code}

    active_company = _Company()

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    response = app.test_client().get("/consultive/cockpit")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Cockpit do Consultor" in body
    assert "cc-compact-header" in body
    assert "/api/consultive/cockpit?limit=12" in body


def test_consultive_cockpit_template_has_responsive_contract():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "cc-compact-header" in body
    assert "@media (max-width: 780px)" in body
    assert "@media (max-width: 460px)" in body
    assert "grid-template-columns: 1fr" in body
    assert "Camada Consultiva" in body
    assert "credentials: 'same-origin'" in body
    assert "renderStructuralFallback" in body
    assert "Sessão não autenticada" in body



def test_consultive_cockpit_static_preview_exists_for_visual_alignment():
    preview_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "docs",
            "previews",
            "consultive_cockpit_preview.html",
        )
    )
    with open(preview_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "Cockpit do Consultor" in body
    assert "Defesa de autuação fiscal" in body
    assert "Business Reviews" in body
    assert "Necessidades Urgentes" in body
    assert "cc-open-link" in body
    assert "Estruturação Empresarial" in body
    assert "Identidade Organizacional" in body
    assert "Processos" in body
    assert "Planejamento Estratégico" in body
    assert "Gerenciamento Estratégico" in body
    assert "4 - Teia · Pendente · 0%" in body
    assert "Registrar Business Review" in body
    assert "cc-modal" in body
    assert "cc-modal-demo" not in body
    assert "Pop-up de registro (exemplo)" not in body
    assert "arquivo Jinja aberto via file://" not in body
    assert "@media (max-width:780px)" in body



def test_consultive_cockpit_urgent_project_card_contract():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "projectCode" in body
    assert "${projectCode} - ${project.name || item.title}" in body
    assert "Programa:" in body
    assert "Urgência:" in body
    assert "Criação:" in body
    assert "Vencimento:" in body
    assert "Responsável:" in body
    assert "Última movimentação:" in body
    assert "Abrir projeto" in body



def test_consultive_cockpit_template_removed_intro_focus_blocks():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "cc-operator-strip" not in body
    assert "cc-focus" not in body
    assert "Qualificar a dor" not in body
    assert "P0 · urgência" not in body



def test_consultive_cockpit_business_review_register_modal_contract():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "A registrar" in body
    assert "Registrado" in body
    assert "data-cc-register-br" in body
    assert "cc-br-modal" in body
    assert "Necessidade Identificada" in body
    assert "Solução Aplicada" in body
    assert "Resultado Alcançado" in body
    assert "Valor<input" in body
    assert "cc-br-added-value-type" in body
    assert "cc-br-added-value-period" in body
    assert "Valor capturado:" in body
    assert "/api/consultive/business-reviews/${encodeURIComponent(reviewId)}/decision" in body


def test_business_review_update_accepts_identified_need_title():
    route_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "api", "routes", "urgent_business_review.py")
    )
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "business_review_service.py")
    )
    with open(route_path, "r", encoding="utf-8") as handle:
        route_body = handle.read()
    with open(service_path, "r", encoding="utf-8") as handle:
        service_body = handle.read()

    assert "title=data.get(\"title\")" in route_body
    assert "title: str | None = None" in service_body
    assert "row.title = clean_text(title) or row.title" in service_body



def test_business_review_added_value_amount_type_period_contract():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "cc-br-added-value-amount" in body
    assert "cc-br-added-value-type" in body
    assert "cc-br-added-value-period" in body
    assert "formatAddedValue" in body
    assert "parseAddedValue" in body
    assert "recorrente" in body
    assert "mensal" in body



def test_business_review_cards_are_collapsible():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "is-collapsed" in body
    assert "cc-collapse-button" in body
    assert "data-cc-toggle-review" in body
    assert "${title} - ${stateLabel}" in body
    assert "aria-expanded" in body



def test_consultive_cockpit_removed_business_review_summary_panel():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "4 campos do Business Review" not in body
    assert "cc-identified-need" not in body
    assert "cc-applied-solution" not in body
    assert "cc-achieved-result" not in body
    assert "cc-added-value\">" not in body


def test_consultive_cockpit_structural_enterprise_contract():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "Estruturação Empresarial" in body
    assert "defaultStructuralFronts" in body
    assert "Identidade Organizacional" in body
    assert "Missão" in body
    assert "Visão" in body
    assert "Valores" in body
    assert "Posicionamento" in body
    assert "Organograma" in body
    assert "Processos" in body
    assert "Arquitetura" in body
    assert "Modelagem" in body
    assert "Implantação" in body
    assert "Estabilização" in body
    assert "Auditoria" in body
    assert "Planejamento Estratégico" in body
    assert "Vinculado à gestão" in body
    assert "Gerenciamento Estratégico" in body
    assert "2 - Ciclos · OK · 100%" in body
    assert "3 - Incentivos · Revisar · 40%" in body
    assert "4 - Teia · Pendente · 0%" in body
    assert "Abrir frente" in body
    assert "Analisar frente" in body
    assert "data-cc-open-structural-front" in body
    assert "function openStructuralFront" in body
    assert "/companies/${encodeURIComponent(companyId)}/identity" in body
    assert "data-cc-analyze-structural-front" in body
    assert "cc-front-analysis-modal" in body
    assert "/api/consultive/cockpit/structural-fronts/${encodeURIComponent(frontKey)}/analysis" in body
    assert "renderFrontAnalysis" in body
    assert "Aprendizados a converter" not in body


def test_consultive_cockpit_analysis_modal_is_operationally_readable():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "cc-analysis-row" in body
    assert "analysisItemTitle" in body
    assert "analysisItemText" in body
    assert "Evidências internas <span>${evidenceCount}</span>" in body
    assert "Gaps metodológicos <span>${gapsCount}</span>" in body
    assert "Recomendações <span>${recommendationsCount}</span>" in body
    assert "Validação do consultor obrigatória" in body
    assert "Próxima ação recomendada" in body
    assert "Avisos técnicos" in body
    assert "position: sticky" in body


def test_business_review_read_model_exposes_structural_front_analysis_contract():
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "business_review_read_model_service.py")
    )
    with open(service_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "STRUCTURAL_FRONTS" in body
    assert '"structural_enterprise"' in body
    assert "def get_structural_front_analysis" in body
    assert '"internal_evidence"' in body
    assert '"engineering_gaps"' in body
    assert '"human_gate_required": True' in body


def test_processes_front_analysis_uses_real_app32_sources():
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "business_review_read_model_service.py")
    )
    with open(service_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "def _processes_front_analysis" in body
    assert "StructuringJourneyService.get_journey" in body
    assert "ProcessArea" in body
    assert "MacroProcess" in body
    assert "ProcessBpmnDiagram" in body
    assert "ProcessRoutine" in body
    assert "ProcessStep" in body
    assert "ProcessActivityExecutionContract" in body
    assert "AuditChecklist" in body
    assert "AuditSchedule" in body
    assert "processes_without_owner" in body
    assert "processes_with_modeling" in body
    assert "3 ciclos dentro das faixas de controle" in body


def test_identity_front_analysis_uses_real_app32_sources():
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "business_review_read_model_service.py")
    )
    with open(service_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "def _identity_front_analysis" in body
    assert "OrganizationalIdentity" in body
    assert "Company.query.filter" in body
    assert "Role.query.filter" in body
    assert "Employee.query.filter" in body
    assert "StrategyMaturationItem" in body
    assert "mission_present" in body
    assert "vision_present" in body
    assert "values_present" in body
    assert "positioning_present" in body
    assert "organogram_present" in body
    assert "dupla fonte para missão, visão e valores" in body


def test_growth_plan_front_analysis_uses_real_app32_sources():
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "business_review_read_model_service.py")
    )
    with open(service_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "def _growth_plan_front_analysis" in body
    assert "Plan.query.filter" in body
    assert "PlanDriver.query.join" in body
    assert "PlanSectionStatus.query.join" in body
    assert "OKRGlobal.query.filter" in body
    assert "OKRArea.query.filter" in body
    assert "KeyResult.query.join" in body
    assert "KeyResultArea.query.join" in body
    assert "Project.query.filter" in body
    assert "ProcessStrategicAlignmentLink" in body
    assert "structured = active_growth_plans_total > 0" in body
    assert "linked_to_management" in body
    assert "qualidade estratégica" in body


def test_strategic_management_front_analysis_uses_real_app32_sources():
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "business_review_read_model_service.py")
    )
    with open(service_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "def _strategic_management_front_analysis" in body
    assert "Indicator.query.filter" in body
    assert "IndicatorGoal" in body
    assert "IndicatorData" in body
    assert "Meeting.query.filter" in body
    assert "IncentiveRuleSet" in body
    assert "IncentiveRule" in body
    assert "IncentiveGovernabilityMatrix" in body
    assert "IndicatorEntityLink" in body
    assert "IndicatorLineOfSight" in body
    assert "Responsável do Indicador" in body
    assert "Teia de Conexões" in body
    assert "decisão, ação e aprendizado" in body


def test_consultive_cockpit_layout_prioritizes_structural_enterprise():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "cc-structural-panel { grid-column: 1 / -1; border-color: #99f6e4" in body
    assert "cc-urgent-panel" in body
    assert "cc-review-panel" in body
    assert "linear-gradient(135deg, #f0fdfa" in body
    assert "linear-gradient(135deg, #fff1f2" in body
    assert "linear-gradient(135deg, #eff6ff" in body
    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in body
    assert "min-height: 13.5rem" in body
    assert "margin-top: auto" in body
    assert ".cc-structural-card .cc-tags" in body
    assert ".cc-urgent-panel .cc-item .cc-tags" in body
    assert ".cc-review-panel .cc-item .cc-tags" in body
    assert "grid-template-columns: 1fr" in body
    assert body.index("Estruturação Empresarial") < body.index("Necessidades Urgentes") < body.index("Business Reviews")
    assert "@media (max-width: 1180px)" in body


def test_consultive_cockpit_structural_tags_show_maturity_microstatus():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "1 - Missão · OK · 100%" in body
    assert "2 - Visão · Parcial · 60%" in body
    assert "4 - Posicionamento · Pendente · 0%" in body
    assert "1 - Arquitetura · OK · 100%" in body
    assert "4 - Estabilização · 1/3 ciclos" in body
    assert "4 - Vinculado à gestão · Pendente · 0%" in body
    assert "3 - Incentivos · Revisar · 40%" in body
    assert "4 - Teia · Pendente · 0%" in body
    assert "status-ok" in body
    assert "status-partial" in body
    assert "status-review" in body
    assert "status-pending" in body


def test_consultive_cockpit_operational_metadata_has_semantic_colors():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "meta-program" in body
    assert "meta-urgency" in body
    assert "meta-created" in body
    assert "meta-due" in body
    assert "meta-owner" in body
    assert "meta-updated" in body
    assert "field-need" in body
    assert "field-solution" in body
    assert "field-result" in body
    assert "field-value" in body


def test_standard_sidebar_exposes_consultive_cockpit_entry():
    sidebar_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "partials",
            "sidebar_standard.html",
        )
    )
    with open(sidebar_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "Consultivo" in body
    assert "/consultive/cockpit" in body
    assert "Cockpit do Consultor" in body
    assert "request.path.startswith('/consultive')" in body
    assert body.index("Módulos") < body.index("Consultivo")


def test_business_review_read_model_is_resilient_to_missing_rollout_tables():
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "business_review_read_model_service.py")
    )
    with open(service_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "SQLAlchemyError" in body
    assert "def _safe_all" in body
    assert "db.session.rollback()" in body
    assert '"warnings": warnings' in body
    assert "return []" in body


def test_consultive_cockpit_uses_standard_left_sidebar():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert '{% extends "layouts/workspace.html" %}' in body
    assert "block sidebar_left" not in body



def test_business_review_read_model_exposes_structuring_maturity_track_contract():
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "business_review_read_model_service.py")
    )
    with open(service_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert '"maturity_track"' in body
    assert "def _structuring_maturity_track_payload" in body
    assert "StructuringJourneyService.get_journey" in body
    assert "Fase 00" in body
    assert "Base Organizacional / empresa na mão" in body
    assert "identidade mínima, organograma, responsabilidades" in body
    assert "Validar missão, visão, valores, posicionamento e organograma" in body
    assert "Fase 01" in body
    assert "Fase 02" in body
    assert "Fase 03" in body
    assert '"detail_url": "/structuring-journey/consultant"' in body


def test_consultive_cockpit_renders_structuring_maturity_track_before_fronts():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "business_review_cockpit.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "cc-maturity-track" in body
    assert "renderMaturityTrack" in body
    assert "Trilha de Maturidade da Estruturação" in body
    assert "Base Organizacional / empresa na mão" in body
    assert "Validar missão, visão, valores, posicionamento e organograma" in body
    assert "Ver detalhe da trilha" in body
    assert "/structuring-journey/consultant" in body
    assert body.index('id="cc-maturity-track"') < body.index('id="cc-structural-list"')
