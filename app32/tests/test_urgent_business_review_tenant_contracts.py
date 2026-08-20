import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import urgent_business_review as ubr_route
from services.consultive_protocol_service import ConsultiveProtocolService


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


def test_register_assisted_analysis_uses_active_company_and_write_gate(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=42, name="Cliente A")
    captured = {}

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)
    monkeypatch.setattr(ubr_route, "has_company_full_access", lambda company_id: company_id == 42)

    def _fake_register_assisted_analysis(**kwargs):
        captured.update(kwargs)
        return {"id": 77, "company_id": kwargs["company_id"], "front_key": kwargs["front_key"]}

    monkeypatch.setattr(
        ubr_route.ConsultiveAssistedAnalysisService,
        "register_assisted_analysis",
        _fake_register_assisted_analysis,
    )

    response = app.test_client().post(
        "/api/consultive/cockpit/fronts/processes/assisted-analyses",
        json={"company_id": 999, "diagnosis": "Processos sem estabilização"},
    )

    assert response.status_code == 201
    assert captured["company_id"] == 42
    assert captured["front_key"] == "processes"
    assert captured["payload"]["company_id"] == 999
    assert response.get_json()["company_id"] == 42


def test_register_assisted_analysis_decision_uses_active_company_and_service(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=42, name="Cliente A")
    captured = {}

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)
    monkeypatch.setattr(ubr_route, "has_company_full_access", lambda company_id: company_id == 42)

    def _fake_register_consultant_decision(**kwargs):
        captured.update(kwargs)
        return {"id": 88, "company_id": kwargs["company_id"], "analysis_id": kwargs["analysis_id"]}

    monkeypatch.setattr(
        ubr_route.ConsultiveAssistedAnalysisService,
        "register_consultant_decision",
        _fake_register_consultant_decision,
    )

    response = app.test_client().post(
        "/api/consultive/cockpit/assisted-analyses/77/decision",
        json={"company_id": 999, "consultant_decision": "accept", "decision_reason": "Aderente"},
    )

    assert response.status_code == 201
    assert captured["company_id"] == 42
    assert captured["analysis_id"] == 77
    assert captured["payload"]["company_id"] == 999
    assert response.get_json()["analysis_id"] == 77



def test_front_level_mcp_protocol_covers_all_structural_fronts():
    expected_subphases = {
        "identity": ["mission", "vision", "values", "positioning", "org_chart"],
        "processes": ["architecture", "modeling", "implantation", "stabilization", "audit"],
        "growth_plan": ["structured", "connected", "deployed", "linked_to_management"],
        "strategic_management": ["indicators", "cycles", "incentives", "connection_web"],
    }

    for front_key, subphases in expected_subphases.items():
        protocol = ConsultiveProtocolService.resolve_protocol(
            company_id=42,
            front_key=front_key,
            audience="ai_cli",
        )

        assert protocol["subphase_key"] is None
        assert protocol["protocol_version"] == "front-guide-v1"
        assert protocol["protocol"]["subphases"] == subphases
        assert "consultive_get_next_action" in protocol["protocol"]["mcp_tools"]
        assert "consultive_get_front_context" in protocol["protocol"]["mcp_tools"]
        assert "consultive_resolve_protocol" in protocol["protocol"]["mcp_tools"]
        assert "pesquisa profunda" in protocol["prompt_markdown"]
        assert "Squad Cliente" in protocol["prompt_markdown"]
        assert "Squad Versus" in protocol["prompt_markdown"]
        assert "Squad Engenharia" in protocol["prompt_markdown"]
        assert "não execute mutação operacional" in protocol["prompt_markdown"]
        assert "estado atual do handoff" in protocol["prompt_markdown"]
        assert "um prompt não eleva role" in protocol["prompt_markdown"]
        journey_guide = protocol["protocol"]["journey_guide"]
        assert journey_guide["entry_state"] == "collecting_evidence"
        assert journey_guide["states"][-1]["key"] == "blocked"
        action_policy = {item["action"]: item["autonomy"] for item in journey_guide["action_policy"]}
        assert action_policy["register_canonical_data"] == "cannot"
        assert action_policy["execute_authorized_mutation"] == "gated"


def test_subphase_mcp_protocol_remains_available_for_deepening():
    protocol = ConsultiveProtocolService.resolve_protocol(
        company_id=42,
        front_key="identity",
        subphase_key="mission",
        audience="ai_cli",
    )

    assert protocol["subphase_key"] == "mission"
    assert "Missão" in protocol["title"]
    assert "Perguntas obrigatórias" in protocol["prompt_markdown"]
    assert "pesquise boas práticas" in protocol["prompt_markdown"]
    assert protocol["protocol"]["journey_guide"]["entry_state"] == "collecting_evidence"
    assert "não valide por outro squad" in protocol["prompt_markdown"]
    assert "um prompt não eleva role" in protocol["prompt_markdown"]

def test_consultive_protocol_route_resolves_active_company_protocol(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=42, name="Cliente A")
    captured = {}

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    def _fake_resolve_protocol(**kwargs):
        captured.update(kwargs)
        return {"company_id": kwargs["company_id"], "front_key": kwargs["front_key"], "title": "Protocolo ativo"}

    monkeypatch.setattr(ubr_route.ConsultiveProtocolService, "resolve_protocol", _fake_resolve_protocol)

    response = app.test_client().get(
        "/api/consultive/cockpit/fronts/identity/protocol?company_id=999&subphase_key=mission&audience=ai_cli"
    )

    assert response.status_code == 200
    assert captured["company_id"] == 42
    assert captured["front_key"] == "identity"
    assert captured["subphase_key"] == "mission"
    assert response.get_json()["title"] == "Protocolo ativo"


def test_upsert_consultive_protocol_uses_active_company_and_write_gate(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=42, name="Cliente A")
    captured = {}

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)
    monkeypatch.setattr(ubr_route, "has_company_full_access", lambda company_id: company_id == 42)

    def _fake_upsert_protocol(**kwargs):
        captured.update(kwargs)
        return {"id": 9, "company_id": kwargs["company_id"], "title": kwargs["payload"]["title"]}

    monkeypatch.setattr(ubr_route.ConsultiveProtocolService, "upsert_protocol", _fake_upsert_protocol)

    response = app.test_client().post(
        "/api/consultive/protocols",
        json={"company_id": 999, "front_key": "identity", "title": "Missão profunda", "prompt_markdown": "..."},
    )

    assert response.status_code == 201
    assert captured["company_id"] == 42
    assert captured["payload"]["company_id"] == 999
    assert response.get_json()["company_id"] == 42


def test_list_consultive_protocols_uses_active_company_catalog(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=42, name="Cliente A")
    captured = {}

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    def _fake_list_protocol_catalog(**kwargs):
        captured.update(kwargs)
        return {"company_id": kwargs["company_id"], "audience": kwargs["audience"], "items": []}

    monkeypatch.setattr(ubr_route.ConsultiveProtocolService, "list_protocol_catalog", _fake_list_protocol_catalog)

    response = app.test_client().get("/api/consultive/protocols?company_id=999&audience=versus_squad")

    assert response.status_code == 200
    assert captured == {"company_id": 42, "audience": "versus_squad"}
    assert response.get_json()["company_id"] == 42


def test_consultive_protocols_page_renders_workspace(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(
        id=42,
        name="Cliente A",
        to_dict=lambda: {"id": 42, "name": "Cliente A"},
    )

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    response = app.test_client().get("/consultive/protocols")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Protocolos Consultivos" in body
    assert "Biblioteca versionada de instruções" in body
    assert "/api/consultive/protocols" in body
    assert "Criar/editar versão" in body


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
    assert "ConsultiveAssistedAnalysisService.register_assisted_analysis" in source
    assert "ConsultiveAssistedAnalysisService.register_consultant_decision" in source
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


def test_consultive_structural_front_page_renders_consultive_shell(monkeypatch):
    app = _build_app()

    class _Company:
        id = 42
        name = "Cliente A"
        client_code = "CLA"

        def to_dict(self):
            return {"id": self.id, "name": self.name, "client_code": self.client_code}

    active_company = _Company()

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    response = app.test_client().get("/consultive/cockpit/fronts/identity")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Camada Consultiva · Estruturação Empresarial" in body
    assert "Identidade Organizacional" in body
    assert 'data-front-key="identity"' in body
    assert "/api/consultive/cockpit/structural-fronts/${encodeURIComponent(frontKey)}/analysis" in body
    assert "/companies/42/identity" in body
    assert "Voltar ao Cockpit" in body


def test_consultive_processes_front_page_renders_without_operational_redirect(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(
        id=42,
        name="Cliente A",
        to_dict=lambda: {"id": 42, "name": "Cliente A"},
    )

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    response = app.test_client().get("/consultive/cockpit/fronts/processes")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-front-key="processes"' in body
    assert "Processos" in body
    assert "Abrir fonte operacional" not in body


def test_consultive_growth_plan_front_page_renders_consultive_shell(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(
        id=42,
        name="Cliente A",
        to_dict=lambda: {"id": 42, "name": "Cliente A"},
    )

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    response = app.test_client().get("/consultive/cockpit/fronts/growth_plan")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-front-key="growth_plan"' in body
    assert "Planejamento Estratégico" in body
    assert "Abrir fonte operacional" not in body


def test_consultive_strategic_management_front_page_renders_consultive_shell(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(
        id=42,
        name="Cliente A",
        to_dict=lambda: {"id": 42, "name": "Cliente A"},
    )

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    response = app.test_client().get("/consultive/cockpit/fronts/strategic_management")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-front-key="strategic_management"' in body
    assert "Gerenciamento Estratégico" in body
    assert "Abrir fonte operacional" not in body


def test_consultive_structural_front_page_exposes_tenant_owned_mcp_assistance(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(
        id=42,
        name="Cliente A",
        to_dict=lambda: {"id": 42, "name": "Cliente A"},
    )

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    response = app.test_client().get("/consultive/cockpit/fronts/processes")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Análise Assistida via MCP" in body
    assert "IA do cliente, método Versus e validação humana" in body
    assert "Custo/token do cliente" in body
    assert "Contexto MCP" in body
    assert "IA/CLI do cliente" in body
    assert "Validação dos squads" in body
    assert "Decisão do consultor" in body
    assert "Ver roteiro MCP para IA/CLI" in body
    assert "Registrar análise recebida" in body
    assert "Registrar decisão do consultor" in body
    assert "O APP32 não dispara a IA" in body
    assert "resultado trazido pela IA/CLI" in body
    assert "cf-mcp-guide-modal" in body
    assert "Roteiro MCP para IA/CLI" in body
    assert "consultive_get_front_context" in body
    assert "consultive_get_front_evidence" in body
    assert "consultive_get_front_gaps" in body
    assert "consultive_get_methodology_guidance" in body
    assert "consultive_resolve_protocol" in body
    assert "perguntas pendentes ao gestor/consultor" in body
    assert "data-cf-open-mcp-guide" in body
    assert "data-cf-open-analysis-register" in body
    assert "data-cf-open-decision-register" in body
    assert "mcpGuidePrompt" in body
    assert "openMcpGuide" in body
    assert "openModal('cf-analysis-register-modal')" in body
    assert "openModal('cf-decision-register-modal')" in body
    assert "company_id:" in body
    assert "Não tome decisão final" in body
    assert "company_id" in body
    assert "cf-analysis-register-modal" in body
    assert "data-cf-analysis-register-form" in body
    assert "Resultado trazido pela IA/CLI via MCP" in body
    assert "diagnosis" in body
    assert "benchmarks" in body
    assert "risks" in body
    assert "recommendations" in body
    assert "client_squad_validation" in body
    assert "versus_squad_validation" in body
    assert "engineering_squad_validation" in body
    assert "analysis_status" in body
    assert "Salvar análise no APP32" in body
    assert "submitAssistedAnalysis" in body
    assert "/assisted-analyses" in body
    assert "Será registrada no tenant ativo" in body
    assert "cf-decision-register-modal" in body
    assert "data-cf-decision-register-form" in body
    assert "Validação humana antes da ação operacional" in body
    assert "analysis_id" in body
    assert "consultant_decision" in body
    assert "conversion_target" in body
    assert "decision_reason" in body
    assert "next_action" in body
    assert "governance_notes" in body
    assert "Salvar decisão no APP32" in body
    assert "submitConsultantDecision" in body
    assert "/decision" in body
    assert "Decisão humana obrigatória" in body


def test_consultive_structural_front_page_rejects_unknown_front(monkeypatch):
    app = _build_app()
    active_company = SimpleNamespace(id=42, name="Cliente A")

    monkeypatch.setattr(ubr_route, "get_active_company", lambda: active_company)

    response = app.test_client().get("/consultive/cockpit/fronts/unknown")

    assert response.status_code == 404


def test_consultive_assisted_analysis_mcp_technical_contract_spec_exists():
    spec_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "docs",
            "spec",
            "contrato_tecnico_analise_assistida_mcp_v1.md",
        )
    )
    with open(spec_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "AssistedAnalysis" in body
    assert "AssistedAnalysisValidation" in body
    assert "AssistedAnalysisDecision" in body
    assert "consultive_register_assisted_analysis" in body
    assert "consultive_register_squad_validation" in body
    assert "consultive_register_consultant_decision" in body
    assert "consultive_create_recommended_action" in body
    assert "company_id" in body
    assert "Registro de análise não cria objeto operacional automaticamente" in body
    assert "Ação operacional é tool própria e posterior" in body
    assert "UI deixa claro que APP32 não dispara IA" in body


def test_consultive_assisted_analysis_models_are_tenant_scoped_and_gate_safe():
    model_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "models",
            "consultive_assisted_analysis.py",
        )
    )
    with open(model_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "__tablename__ = \"consultive_assisted_analyses\"" in body
    assert "__tablename__ = \"consultive_assisted_analysis_validations\"" in body
    assert "__tablename__ = \"consultive_assisted_analysis_decisions\"" in body
    assert "company_id = db.Column" in body
    assert "front_key IN" in body
    assert "source_payload_json = db.Column(db.JSON" in body
    assert "analysis_id = db.Column" in body
    assert "conversion_target" in body
    assert "sem executar IA dentro do APP32" in body


def test_consultive_assisted_analysis_migration_is_idempotent_and_tenant_scoped():
    migration_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "versions",
            "20260701_1015_create_consultive_assisted_analysis.py",
        )
    )
    with open(migration_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "CREATE TABLE IF NOT EXISTS public.consultive_assisted_analyses" in body
    assert "company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE" in body
    assert "consultive_assisted_analysis_validations" in body
    assert "consultive_assisted_analysis_decisions" in body
    assert "CREATE INDEX IF NOT EXISTS ix_consultive_assisted_analyses_company_front" in body
    assert "DROP TABLE IF EXISTS public.consultive_assisted_analysis_decisions" in body


def test_consultive_assisted_analysis_mcp_tools_are_registered_in_catalog():
    catalog_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "src", "intelligence", "tool_catalog.py")
    )
    tools_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "src", "core", "mcp_consultive_assisted_analysis_tools.py")
    )
    with open(catalog_path, "r", encoding="utf-8") as handle:
        catalog = handle.read()
    with open(tools_path, "r", encoding="utf-8") as handle:
        tools = handle.read()

    assert "register_consultive_assisted_analysis_tools" in catalog
    assert "consultive_get_next_action" in catalog
    assert "consultive_get_front_context" in catalog
    assert "consultive_register_assisted_analysis" in catalog
    assert "consultive_register_consultant_decision" in catalog
    assert "consultive_create_recommended_action" in catalog
    assert "BusinessReviewReadModelService.get_structural_front_analysis" in tools
    assert "ConsultiveAssistedAnalysisService.register_assisted_analysis" in tools
    assert "human_gate_required=write" in tools


def test_consultive_protocol_library_is_versioned_modifiable_and_mcp_first():
    model_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "models", "consultive_protocol.py")
    )
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "consultive_protocol_service.py")
    )
    migration_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "versions",
            "20260701_1030_create_consultive_protocols.py",
        )
    )
    with open(model_path, "r", encoding="utf-8") as handle:
        model = handle.read()
    with open(service_path, "r", encoding="utf-8") as handle:
        service = handle.read()
    with open(migration_path, "r", encoding="utf-8") as handle:
        migration = handle.read()

    assert "__tablename__ = \"consultive_protocols\"" in model
    assert "company_id = db.Column" in model
    assert "protocol_version" in model
    assert "prompt_markdown" in model
    assert "protocol_json" in model
    assert "CONSULTIVE_PROTOCOL_AUDIENCE_VALUES" in model
    assert "CONSULTIVE_PROTOCOL_DEPTH_VALUES" in model
    assert "resolve_protocol" in service
    assert "upsert_protocol" in service
    assert "DEFAULT_PROTOCOL_CATALOG" in service
    assert "SUBPHASE_ALIASES" in service
    assert "pesquisa profunda" in service
    assert "simule aderência" in service
    for key in (
        "mission",
        "vision",
        "values",
        "positioning",
        "org_chart",
        "architecture",
        "modeling",
        "implantation",
        "stabilization",
        "audit",
        "structured",
        "connected",
        "deployed",
        "linked_to_management",
        "indicators",
        "cycles",
        "incentives",
        "connection_web",
    ):
        assert key in service
    assert "CREATE TABLE IF NOT EXISTS public.consultive_protocols" in migration
    assert "ix_consultive_protocols_resolution" in migration


def test_consultive_protocol_tools_and_ui_replace_static_prompt_contract():
    catalog_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "src", "intelligence", "tool_catalog.py")
    )
    tools_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "src", "core", "mcp_consultive_assisted_analysis_tools.py")
    )
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "structural_front.html",
        )
    )
    with open(catalog_path, "r", encoding="utf-8") as handle:
        catalog = handle.read()
    with open(tools_path, "r", encoding="utf-8") as handle:
        tools = handle.read()
    with open(template_path, "r", encoding="utf-8") as handle:
        template = handle.read()

    assert "consultive_resolve_protocol" in catalog
    assert "consultive_upsert_protocol" in catalog
    assert "ConsultiveProtocolService.resolve_protocol" in tools
    assert "ConsultiveProtocolService.upsert_protocol" in tools
    assert "active_protocol" in tools
    assert "let activeProtocol" in template
    assert "/protocol?audience=ai_cli" in template
    assert "Protocolo ativo:" in template
    assert "consultive_resolve_protocol" in template


def test_consultive_protocol_service_resolves_base_protocol_for_all_cockpit_subphases():
    from services.consultive_protocol_service import ConsultiveProtocolService

    expected = {
        "identity": ["mission", "vision", "values", "positioning", "org_chart"],
        "processes": ["architecture", "modeling", "implantation", "stabilization", "audit"],
        "growth_plan": ["structured", "connected", "deployed", "linked_to_management"],
        "strategic_management": ["indicators", "cycles", "incentives", "connection_web"],
    }

    resolved = []
    for front_key, subphases in expected.items():
        for subphase_key in subphases:
            protocol = ConsultiveProtocolService.resolve_protocol(
                company_id=42,
                front_key=front_key,
                subphase_key=subphase_key,
                audience="ai_cli",
            )
            resolved.append((front_key, subphase_key))
            assert protocol["source"] == "fallback"
            assert protocol["front_key"] == front_key
            assert protocol["subphase_key"] == subphase_key
            assert protocol["status"] == "active"
            assert protocol["protocol_version"] == "fallback-v1"
            assert protocol["title"].startswith("Protocolo")
            assert "MCP First" in protocol["prompt_markdown"]
            assert "não tome decisão final" in protocol["prompt_markdown"].lower()
            assert protocol["protocol"]["required_questions"]

    assert len(resolved) == 18


def test_consultive_protocol_catalog_lists_all_cockpit_subphases():
    from services.consultive_protocol_service import ConsultiveProtocolService

    catalog = ConsultiveProtocolService.list_protocol_catalog(company_id=42, audience="ai_cli")

    assert catalog["company_id"] == 42
    assert catalog["audience"] == "ai_cli"
    assert catalog["total"] == 18
    assert len(catalog["items"]) == 18
    assert {item["front_key"] for item in catalog["items"]} == {
        "identity",
        "processes",
        "growth_plan",
        "strategic_management",
    }
    assert all(item["active_protocol"]["status"] == "active" for item in catalog["items"])


def test_consultive_protocols_template_exposes_management_ui_contract():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "protocols.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert '{% extends "layouts/workspace.html" %}' in body
    assert "Protocolos Consultivos" in body
    assert "cp-audience" in body
    assert "cp-search" in body
    assert "cp-modal" in body
    assert "tenant-owned" in body
    assert "prompt_markdown" in body
    assert "fetch(`/api/consultive/protocols?audience=" in body
    assert "fetch('/api/consultive/protocols'" in body
    assert "Criar/editar versão" in body


def test_consultive_assisted_analysis_spec_documents_evolutive_protocols():
    spec_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "docs",
            "spec",
            "contrato_tecnico_analise_assistida_mcp_v1.md",
        )
    )
    with open(spec_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "Protocolos Consultivos Evolutivos" in body
    assert "consultive_protocols" in body
    assert "consultive_resolve_protocol" in body
    assert "consultive_upsert_protocol" in body
    assert "pesquisa profunda" in body
    assert "evolução metodológica deve ocorrer preferencialmente por protocolo versionado" in body
    assert "Protocolos-base obrigatórios do Cockpit" in body
    assert "`mission`, `vision`, `values`, `positioning`, `org_chart`" in body
    assert "`architecture`, `modeling`, `implantation`, `stabilization`, `audit`" in body
    assert "`indicators`, `cycles`, `incentives`, `connection_web`" in body


def test_consultive_structural_front_template_has_process_subphases_contract():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "structural_front.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "cf-process-subphases" in body
    assert "Maturação de Processos" in body
    assert "Arquitetura" in body
    assert "Modelagem" in body
    assert "Implantação" in body
    assert "Estabilização" in body
    assert "Auditoria" in body
    assert "projeto associado" in body
    assert "3 ciclos dentro das faixas de controle" in body
    assert "rol de auditoria interna" in body
    assert "findEvidence(evidence, 'Processos com fluxo/modelagem')" in body
    assert "findEvidence(evidence, 'SPEC/contratos de execução')" in body
    assert "frontKey !== 'processes'" in body


def test_consultive_structural_front_template_has_identity_subphases_contract():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "structural_front.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "cf-identity-subphases" in body
    assert "Base organizacional da empresa" in body
    assert "empresa estar “na mão”" in body
    assert "Missão" in body
    assert "Visão" in body
    assert "Valores" in body
    assert "Posicionamento" in body
    assert "Organograma" in body
    assert "renderIdentitySubphases" in body
    assert "evidenceStatus(evidence, 'Missão')" in body
    assert "evidenceStatus(evidence, 'Visão')" in body
    assert "evidenceStatus(evidence, 'Valores')" in body
    assert "evidenceStatus(evidence, 'Posicionamento')" in body
    assert "evidenceStatus(evidence, 'Organograma')" in body
    assert "frontKey !== 'identity'" in body


def test_consultive_structural_front_template_has_growth_plan_subphases_contract():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "structural_front.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "cf-growth-plan-subphases" in body
    assert "Evolução consultiva do plano de crescimento" in body
    assert "não basta existir um plano" in body
    assert "Estruturado" in body
    assert "Conectado" in body
    assert "Desdobrado" in body
    assert "Vinculado à gestão" in body
    assert "Planejamento de crescimento" in body
    assert "Direcionadores estratégicos" in body
    assert "OKRs globais" in body
    assert "Projetos vinculados" in body
    assert "Conexão com processos" in body
    assert "renderGrowthPlanSubphases" in body
    assert "frontKey !== 'growth_plan'" in body
    assert "Gerenciamento Estratégico para decisão, acompanhamento e aprendizado" in body


def test_consultive_structural_front_template_has_strategic_management_subphases_contract():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "structural_front.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "cf-strategic-management-subphases" in body
    assert "Gestão por fatos, incentivos e conexões" in body
    assert "decide com base em fatos" in body
    assert "Indicadores" in body
    assert "Ciclos" in body
    assert "Incentivos" in body
    assert "Teia de Conexões" in body
    assert "Responsável" not in body or "responsável" in body
    assert "findEvidence(evidence, 'Indicadores')" in body
    assert "findEvidence(evidence, 'Ciclos de gestão')" in body
    assert "findEvidence(evidence, 'Gestão de Incentivos')" in body
    assert "findEvidence(evidence, 'Teia de Conexões')" in body
    assert "renderStrategicManagementSubphases" in body
    assert "frontKey !== 'strategic_management'" in body
    assert "estratégia, processos, projetos, pessoas e indicadores" in body


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
    assert "/consultive/cockpit/fronts/${encodeURIComponent(frontKey)}" in body
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


def test_standard_sidebar_preserves_consultive_and_uses_approved_macro_navigation():
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

    assert "_strategic_planning.html" in body
    assert "_strategic_management.html" in body
    assert "Consultivo" in body
    assert "/consultive/cockpit" in body
    assert "Cockpit do Consultor" in body
    assert "/structuring-journey/client" in body
    assert "Jornada do Cliente" in body
    assert "/consultive/protocols" in body
    assert "Protocolos Consultivos" in body
    assert "Módulos" not in body
    assert body.index("Consultivo") < body.index("_strategic_planning.html")
    assert body.index("_strategic_planning.html") < body.index("_strategic_management.html")
    assert body.index("_strategic_management.html") < body.index("Gestão Comercial")


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
    assert "Fases da Estruturação Empresarial" in body
    assert "Base Organizacional / empresa na mão" in body
    assert "Validar missão, visão, valores, posicionamento e organograma" in body
    assert "Trilha de Estruturação" in body
    assert "/structuring-journey/consultant" in body
    assert body.index('id="cc-maturity-track"') < body.index('id="cc-structural-list"')


def test_structuring_journey_consultant_is_positioned_as_structuring_track():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "strategy",
            "structuring_journey.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "Trilha de Estruturação" in body
    assert "Trilha metodológica acionada pelo Cockpit" in body
    assert "Pré-analisar" in body
    assert "Abrir etapa" in body
    assert "Etapa da trilha" in body
    assert "Voltar ao Cockpit" in body


def test_structuring_journey_identity_block_uses_canonical_five_items():
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "structuring_journey_service.py")
    )
    with open(service_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert '("mission", "Missão", "essential")' in body
    assert '("vision", "Visão", "essential")' in body
    assert '("values", "Valores", "essential")' in body
    assert '("positioning", "Posicionamento", "essential")' in body
    assert '("org_chart", "Organograma", "essential")' in body
    assert '("value_propositions", "Proposta de Valor", "essential")' not in body
    assert '("objectives_pillars", "Objetivos/Pilares", "essential")' not in body
    assert '("purpose", "Propósito", "recommended")' not in body
    assert '("differentials", "Diferenciais", "recommended")' not in body
    assert '("essential_competencies", "Competências", "recommended")' not in body
    assert '("segments_icp", "ICP/Segmentos", "recommended")' not in body
    assert '("policies", "Políticas", "optional")' not in body
    assert '("stakeholders", "Stakeholders", "optional")' not in body
    assert '("swot", "SWOT", "optional")' not in body


def test_assisted_analysis_persists_protocol_snapshot_contract():
    model_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "models", "consultive_assisted_analysis.py")
    )
    service_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "services", "consultive_assisted_analysis_service.py")
    )
    migration_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "versions",
            "20260701_1045_link_assisted_analysis_protocols.py",
        )
    )
    with open(model_path, "r", encoding="utf-8") as handle:
        model_body = handle.read()
    with open(service_path, "r", encoding="utf-8") as handle:
        service_body = handle.read()
    with open(migration_path, "r", encoding="utf-8") as handle:
        migration_body = handle.read()

    assert "protocol_id" in model_body
    assert "protocol_version" in model_body
    assert "protocol_source" in model_body
    assert "protocol_title" in model_body
    assert "protocol_snapshot_json" in model_body
    assert "ConsultiveProtocolService.resolve_protocol" in service_body
    assert "protocol_snapshot" in service_body
    assert "_serialize_analysis" in service_body
    assert "latest_decision" in service_body
    assert "ADD COLUMN IF NOT EXISTS protocol_snapshot_json" in migration_body
    assert "fk_consultive_assisted_analyses_protocol_id" in migration_body


def test_structural_front_has_consultant_friendly_analysis_history_ui():
    template_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "modules",
            "consultive",
            "structural_front.html",
        )
    )
    with open(template_path, "r", encoding="utf-8") as handle:
        body = handle.read()

    assert "Histórico de análises assistidas" in body
    assert 'id="cf-analysis-history"' in body
    assert "Memória consultiva" in body
    assert "data-cf-refresh-history" in body
    assert "data-cf-use-analysis" in body
    assert "function renderAnalysisHistory" in body
    assert "function loadAssistedAnalyses" in body
    assert "payload.protocol_snapshot = activeProtocol" in body
    assert 'id="cf-active-protocol"' in body
    assert "function updateActiveProtocolBadge" in body
    assert "Análise selecionada" in body
    assert "Clique em Decidir no histórico" in body
    assert "Protocolo" in body
    assert "Squads" in body
    assert "Decisão" in body


def test_mcp_surface_exposes_assisted_analysis_history_tool():
    mcp_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "src", "core", "mcp_consultive_assisted_analysis_tools.py")
    )
    catalog_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "src", "intelligence", "tool_catalog.py")
    )
    with open(mcp_path, "r", encoding="utf-8") as handle:
        mcp_body = handle.read()
    with open(catalog_path, "r", encoding="utf-8") as handle:
        catalog_body = handle.read()

    assert "def consultive_list_assisted_analyses" in mcp_body
    assert "ConsultiveAssistedAnalysisService.list_analyses" in mcp_body
    assert "assisted_analysis.list" in mcp_body
    assert "consultive_list_assisted_analyses" in catalog_body

def test_official_mission_protocol_library_contract_is_seeded_without_fixed_tenant_id():
    migration_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "versions",
            "20260721_0900_seed_official_mission_protocol.py",
        )
    )
    with open(migration_path, "r", encoding="utf-8") as handle:
        migration_body = handle.read()

    assert "mission-official-v1.0" in migration_body
    assert "seed:mission-official-v1.0:global" in migration_body
    assert "seed:mission-official-v1.0:tenant-aa" in migration_body
    assert "client_code = 'AA'" in migration_body
    assert "company_id IS NOT DISTINCT FROM CAST(:company_id AS INTEGER)" in migration_body
    assert "company_id=9" not in migration_body.replace(" ", "")
