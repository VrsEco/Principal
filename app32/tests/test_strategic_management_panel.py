import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import processes as processes_route
from services.efficiency_collaborators_service import build_team_efficiency_summary
from services.strategic_management_panel_service import GROUP_DEFINITIONS, _evaluate_indicator_status, _resolve_period


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
    )
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return None

    app.register_blueprint(processes_route.processes_bp)
    return app


def _panel_payload(company_id=9):
    return {
        "company_id": company_id,
        "period": {"key": "month", "label": "Junho/2026", "start": "2026-06-01", "end": "2026-06-30"},
        "groups": [
            {
                "key": "strategic",
                "label": "Indicadores Estratégicos",
                "short_label": "Estratégicos",
                "subtitle": "Resultado e direção",
                "color": "#ef4444",
                "total": 1,
                "alerts_count": 1,
                "semaphore": {"green": 0, "yellow": 0, "red": 1, "blue": 0, "gray": 0},
                "subgroups": [],
            }
        ],
        "meetings": [],
        "actions": {},
        "generated_at": "2026-06-14T00:00:00",
    }


def test_strategic_management_panel_api_is_tenant_scoped(monkeypatch):
    app = _build_app()

    monkeypatch.setattr("utils.permissions.has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        processes_route,
        "build_strategic_management_panel",
        lambda company_id, period=None: _panel_payload(company_id),
    )

    response = app.test_client().get("/api/companies/9/process-portal/strategic-management?period=month")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["company_id"] == 9
    assert payload["data"]["groups"][0]["key"] == "strategic"


def test_strategic_management_panel_short_route_redirects_to_active_company(monkeypatch):
    app = _build_app()

    monkeypatch.setattr("utils.permissions.has_permission", lambda company_id, resource, action: True)

    client = app.test_client()
    with client.session_transaction() as session:
        session["active_company_id"] = 9

    response = client.get("/process-portal/strategic-management", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/companies/9/process-portal/strategic-management")


def test_strategic_management_panel_page_uses_executive_template(monkeypatch):
    app = _build_app()

    monkeypatch.setattr("utils.permissions.has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        processes_route,
        "Company",
        SimpleNamespace(query=SimpleNamespace(get_or_404=lambda company_id: SimpleNamespace(id=company_id, name="Empresa Teste"))),
    )
    monkeypatch.setattr(processes_route, "build_strategic_management_panel", lambda company_id, period=None: _panel_payload(company_id))
    monkeypatch.setattr(
        processes_route,
        "render_template",
        lambda template_name, **context: f"{template_name}|{context['company_id']}|{context['panel']['groups'][0]['short_label']}",
    )

    response = app.test_client().get("/companies/9/process-portal/strategic-management")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "modules/processes/strategic_management_panel.html" in body
    assert "|9|" in body
    assert "Estratégicos" in body


def test_period_resolution_keeps_context_as_filter_not_cadastro():
    period = _resolve_period("quarter")

    assert period["key"] == "quarter"
    assert period["start"] <= period["end"]
    assert "trimestre" in period["label"]


def test_indicator_status_requires_corrective_action_when_red():
    indicator = SimpleNamespace(polarity="positive")
    latest = SimpleNamespace(measured_value=70)
    goal = SimpleNamespace(goal_value=100)

    status = _evaluate_indicator_status(indicator, latest, goal)

    assert status["semaphore"] == "red"
    assert "ação corretiva governada" in status["detail"]


def test_process_portal_has_strategic_management_quick_access():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "processes", "process_portal_compact.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "Painel de Gestão Estratégica" in content
    assert "strategic_management_panel_page" in content
    assert "Acesso Rápido" in content


def test_strategic_management_panel_action_modal_links_indicator_to_project_or_activity():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "processes", "strategic_management_panel.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "Nova atividade / projeto" in content
    assert "Escolha se a correção será um novo projeto ou uma atividade" in content
    assert "indicator_id" in content
    assert "process_id" in content
    assert "/api/projects/${projectId}/tasks" in content


def test_strategic_management_panel_header_has_process_meeting_and_action_buttons():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "processes", "strategic_management_panel.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "smp-navbar-actions" in content
    assert "toggleSidebar('right')" in content
    assert "Filtros" in content
    assert "Portal de Processos" in content
    assert "meetings.meetings_company_manage" in content
    assert "Nova reunião" in content
    assert "data-open-action-modal" in content
    assert "Nova atividade / projeto" in content
    assert "http://127.0.0.1:5032/meetings/company/9" not in content


def test_strategic_management_panel_period_filter_lives_in_right_sidebar():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "processes", "strategic_management_panel.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    sidebar_start = content.index("{% block sidebar_right %}")
    workspace_start = content.index("{% block workspace_content %}")
    sidebar_content = content[sidebar_start:workspace_start]
    hero_content = content[workspace_start:content.index('<section class="smp-card">')]

    assert "smp-filter-sidebar" in sidebar_content
    assert '<label for="period">Período</label>' in sidebar_content
    assert 'name="period"' in sidebar_content
    assert "Aplicar filtro" in sidebar_content
    assert "smp-period-form" not in hero_content


def test_strategic_management_panel_removes_intro_hero_to_prioritize_data():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "processes", "strategic_management_panel.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert 'class="smp-hero"' not in content
    assert "Portal de Processos / Acesso Rápido" not in content
    assert "Visão executiva de indicadores" not in content


def test_project_form_warns_to_create_activities_when_project_is_indicator_corrective():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "projects", "project_form_v2.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "Projeto corretivo vinculado ao indicador" in content
    assert "Após criar o projeto, crie as atividades corretivas" in content
    assert "data.indicator_id" in content


def test_standard_sidebar_has_strategic_management_quick_access():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "partials", "sidebar_standard.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "/process-portal/strategic-management" in content
    assert "Painel de Gestão Estratégica" in content


def test_strategic_management_panel_has_team_efficiency_group_contract():
    assert "team_efficiency" in GROUP_DEFINITIONS
    assert GROUP_DEFINITIONS["team_efficiency"]["short_label"] == "Equipe"
    assert "Eficiência" in GROUP_DEFINITIONS["team_efficiency"]["label"]


def test_strategic_management_panel_template_supports_five_cards_and_value_label():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "processes", "strategic_management_panel.html")
    )

    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "repeat(5,minmax(0,1fr))" in content
    assert "group.value_label or group.total" in content
    assert "group.card_title or group.short_label" in content
    assert "group.alert_label" in content
    assert "data-team-member" in content
    assert "Total Geral / Máx" in content
    assert "Pontuação: Conseguidas | Possíveis" in content
    assert "Quantidade: Total | Aberta | Finalizada" in content
    assert "Horas: Realizadas | Previstas | Capacidade Operacional" in content
    assert "Ocorrências: Positivas | Negativas" in content
    assert "smp-team-summary" in content
    assert "smp-team-section" in content
    assert "counts_label" in content
    assert "Sobrecarregado" in content
    assert "Ocioso" in content
    assert "team_efficiency" in content
    assert "closeTopLayer" in content
    assert "closeLayer(level)" in content
    assert "position:absolute; inset:0; width:100%; min-height:100%" in content
    assert "smp-group-card__content" in content
    assert "smp-group-card__value" in content
    assert "grid-template-areas:" in content
    assert ".workspace-navbar .navbar-breadcrumb{display:none;}" in content
    assert "smp-mobile-actions-toggle" in content
    assert "smp-navbar-actions__menu" in content
    assert "setMobileActionsOpen" in content


def test_team_efficiency_summary_uses_total_score_contract(monkeypatch):
    sample = [
        {
            "employee_id": 7,
            "employee_name": "Fabiano",
            "role_title": "Gerente Adm/Fin",
            "period_hours": {
                "contracted": 40,
                "worked_total": 0,
                "free_capacity": 40,
                "utilization_percent": 0,
            },
            "in_progress": {"total": 1, "late": 0},
            "completed": {"total": 0, "late": 0},
            "positive_occurrences": {"count": 2, "score": 11},
            "negative_occurrences": {"count": 0, "score": 0},
            "delivery_scores": {
                "project": {"total": 5, "assigned": 5, "assigned_count": 1},
                "process": {"total": 0, "assigned": 0, "assigned_count": 2},
                "overall": {"assigned": 5, "assigned_count": 3},
            },
        }
    ]

    monkeypatch.setattr(
        "services.efficiency_collaborators_service.get_efficiency_collaborators",
        lambda **kwargs: sample,
    )

    payload = build_team_efficiency_summary(company_id=9)
    item = payload["items"][0]["efficiency"]

    assert payload["card_title"] == "Equipe"
    assert payload["value_label"] == "16,00 / 5,00"
    assert payload["card_subtitle"] == "Eficiência global do time da empresa"
    assert payload["summary"]["activity_count"] == 1
    assert payload["summary"]["instance_count"] == 2
    assert payload["summary"]["occurrence_count"] == 2
    assert payload["summary"]["counts_label"] == "1 atividades | 2 instâncias | 2 Ocorrências"
    assert item["role_title"] == "Gerente Adm/Fin"
    assert item["activity_count"] == 1
    assert item["instance_count"] == 2
    assert item["occurrence_count"] == 2
    assert item["score_total_label"] == "16,00"
    assert item["score_max_label"] == "5,00"
    assert item["project_score_label"] == "5,00"
    assert item["process_score_label"] == "0,00"
    assert item["occurrence_score_label"] == "11,00"
    assert item["project_quantity"] == {"total": 1, "open": 1, "finished": 0}
    assert item["process_quantity"] == {"total": 2, "open": 2, "finished": 0}
    assert item["project_hours"]["realized_label"] == "0,00h"
    assert item["process_hours"]["realized_label"] == "0,00h"
    assert item["occurrences"]["positive_count"] == 2
    assert item["occurrences"]["negative_count"] == 0
    assert item["contracted_hours_label"] == "40,00h"
    assert item["worked_hours_label"] == "0,00h"
    assert item["free_capacity_label"] == "40,00h"
    assert item["status_label"] == "Ocioso"


def test_efficiency_analysis_has_company_aware_route_and_sidebar_link():
    main_route_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "api", "routes", "main.py")
    )
    sidebar_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "partials", "sidebar", "_routine_management.html")
    )

    with open(main_route_path, encoding="utf-8") as handle:
        main_content = handle.read()
    with open(sidebar_path, encoding="utf-8") as handle:
        sidebar_content = handle.read()

    assert "/companies/<int:company_id>/efficiency-analysis" in main_content
    assert "efficiency_analysis_company" in main_content
    assert "_can_access_company_efficiency" in main_content
    assert "main.efficiency_analysis_company" in sidebar_content
