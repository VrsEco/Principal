import html as html_module
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, render_template_string
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import configs as configs_route


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

    app.register_blueprint(configs_route.configs_bp)
    return app


def _fake_active_company():
    return SimpleNamespace(id=31, name="Empresa MCP", client_code="MCP")


def _fake_console_state():
    return {
        "summary": {
            "profiles": 4,
            "surfaces": 4,
            "domains": 12,
            "permission_matrices": 4,
            "catalog_tools": 18,
            "human_gate_tools": 6,
            "critical_tools": 2,
            "release_checks": 7,
            "release_smokes": 4,
            "freeze_triggers": 5,
            "onboarding_steps": 5,
            "readiness_gates": 5,
            "dashboard_panels": 6,
        },
        "profiles": [],
        "surfaces": [],
        "domains": [],
        "permissions": [],
        "catalog": {
            "manifest_version": "test",
            "tools": [],
            "domain_distribution": [],
            "risk_distribution": [],
            "surfaces": [],
        },
        "onboarding": {"steps": [], "surface_access_rules": []},
        "release": {"checklist": [], "smokes": []},
        "freeze": {"triggers": []},
        "dashboard": {"panels": []},
        "readiness": {"gates": [], "opening_criteria": [], "blocking_conditions": []},
        "readiness_by_phase": [],
        "configuration_links": [],
        "registration_links": [],
        "operational_links": [],
        "wizard_steps": [
            {
                "step": 1,
                "id": "profile",
                "title": "Quem vai usar?",
                "question": "Escolha o perfil que mais se aproxima de quem vai operar agora.",
                "options": [
                    {
                        "label": "Colaborador",
                        "description": "Para execução assistida de rotina, projetos, reuniões e autoatendimento.",
                        "target_tab": "profiles",
                        "target_selector": "colaborador",
                    },
                    {
                        "label": "Cliente",
                        "description": "Para consulta, acompanhamento e análises guiadas com menor privilégio.",
                        "target_tab": "profiles",
                        "target_selector": "cliente",
                    },
                ],
            },
            {
                "step": 2,
                "id": "intent",
                "title": "O que você quer fazer?",
                "question": "Selecione sua intenção principal para o console te levar à área certa.",
                "options": [
                    {
                        "label": "Configurar",
                        "description": "Ajustar integrações, parâmetros, perfis ou cadastros-base.",
                        "target_tab": "onboarding",
                        "target_selector": "configurar",
                    },
                    {
                        "label": "Analisar",
                        "description": "Consultar dashboard, readiness, métricas e cruzamentos permitidos.",
                        "target_tab": "dashboard",
                        "target_selector": "analisar",
                    },
                ],
            },
            {
                "step": 3,
                "id": "scope",
                "title": "Qual área você vai usar?",
                "question": "Escolha o contexto principal para receber atalhos imediatos.",
                "options": [
                    {
                        "label": "Rotina / Projetos / Reuniões",
                        "description": "Uso operacional do dia a dia com surface user e playbooks funcionais.",
                        "target_tab": "surfaces",
                        "target_selector": "routine projects meetings",
                    },
                    {
                        "label": "Finanças / Governança",
                        "description": "Uso sensível com permissões administrativas e gates humanos.",
                        "target_tab": "release",
                        "target_selector": "finance governance",
                    },
                ],
            },
        ],
        "quick_assistant": [
            {
                "label": "Quero configurar primeiro",
                "description": "Vai para integrações, parâmetros gerais e onboarding guiado.",
                "target_tab": "onboarding",
                "query": "configurar",
            },
            {
                "label": "Quero entender permissões",
                "description": "Mostra perfil, surface e o que é permitido ou bloqueado.",
                "target_tab": "profiles",
                "query": "permissões perfil surface",
            },
            {
                "label": "Quero analisar dados",
                "description": "Leva para dashboard, readiness e blocos analíticos do console.",
                "target_tab": "dashboard",
                "query": "analytics dashboard readiness",
            },
        ],
        "contextual_help": [
            {
                "title": "Se você está começando agora",
                "body": "Use o wizard no topo. Ele reduz a complexidade e te leva para a seção certa sem exigir que você conheça MCP, surfaces ou contratos.",
            },
            {
                "title": "Se precisa só configurar",
                "body": "Comece por Onboarding & Cadastros. Lá estão integrações, usuários, parâmetros gerais e entradas de configuração do ecossistema.",
            },
            {
                "title": "Se quer apenas usar no dia a dia",
                "body": "Olhe Perfis & Permissões e depois Surfaces & Domínios. Isso responde rapidamente o que pode ou não pode ser feito.",
            },
        ],
    }


def test_ai_mcp_console_wizard_route_exposes_guided_entry_contract(monkeypatch):
    app = _build_app()
    captured = {}
    active_company = _fake_active_company()
    fake_console = _fake_console_state()

    monkeypatch.setattr(configs_route, "_resolve_active_company", lambda: active_company)
    monkeypatch.setattr(configs_route, "_can_access_ai_mcp_console", lambda company_id=None: True)
    monkeypatch.setattr(configs_route.AIMCPConsoleService, "build_frontend_state", lambda company=None: fake_console)
    monkeypatch.setattr(
        configs_route,
        "render_template",
        lambda template_name, **context: captured.update({"template_name": template_name, "context": context}) or "ok",
    )

    response = app.test_client().get("/configs/ai/mcp")

    assert response.status_code == 200
    assert captured["template_name"] == "modules/operations/ai_mcp_console.html"

    context = captured["context"]
    assert context["active_company"].id == 31
    assert context["active_company"].name == "Empresa MCP"
    assert context["active_company"].client_code == "MCP"

    console = context["console"]
    assert [step["title"] for step in console["wizard_steps"]] == [
        "Quem vai usar?",
        "O que você quer fazer?",
        "Qual área você vai usar?",
    ]
    assert [item["label"] for item in console["quick_assistant"]] == [
        "Quero configurar primeiro",
        "Quero entender permissões",
        "Quero analisar dados",
    ]
    assert [item["title"] for item in console["contextual_help"]] == [
        "Se você está começando agora",
        "Se precisa só configurar",
        "Se quer apenas usar no dia a dia",
    ]


def test_ai_mcp_console_template_renders_wizard_steps_ctas_and_contextual_help():
    app = _build_app()
    fake_console = _fake_console_state()

    with app.test_request_context("/configs/ai/mcp"):
        rendered_html = render_template_string(
            '{% extends "modules/operations/ai_mcp_console.html" %}{% block sidebar_left %}{% endblock %}',
            active_company=_fake_active_company(),
            console=fake_console,
        )

    html = html_module.unescape(rendered_html)

    assert "Assistente inicial" in html
    assert "Comece pelo caminho certo, sem precisar decorar a arquitetura." in html
    assert "1. Entenda" in html
    assert "2. Configure" in html
    assert "3. Teste" in html

    for expected in [
        "Quem vai usar?",
        "O que você quer fazer?",
        "Qual área você vai usar?",
        "Colaborador",
        "Cliente",
        "Configurar",
        "Analisar",
        "Rotina / Projetos / Reuniões",
        "Finanças / Governança",
    ]:
        assert expected in html

    for expected_cta in [
        "Ir para Onboarding",
        "Ver Perfis & Permissões",
        "Explorar Surfaces",
        "Validar Release",
        "Abrir Dashboard",
    ]:
        assert expected_cta in html

    assert 'data-console-go-tab="onboarding"' in html
    assert 'data-console-go-tab="profiles"' in html
    assert 'data-console-go-tab="surfaces"' in html
    assert 'data-console-go-tab="release"' in html
    assert 'data-console-go-tab="dashboard"' in html

    assert "Assistente rápido" in html
    assert "Quero configurar primeiro" in html
    assert "Quero entender permissões" in html
    assert "Quero analisar dados" in html
    assert 'data-assistant-action' in html
    assert 'data-target-tab="onboarding"' in html
    assert 'data-target-tab="profiles"' in html
    assert 'data-target-tab="dashboard"' in html

    assert "Ajuda contextual" in html
    assert "Se você está começando agora" in html
    assert "Use o wizard no topo." in html
    assert "Se precisa só configurar" in html
    assert "Comece por Onboarding & Cadastros." in html
    assert "Se quer apenas usar no dia a dia" in html
    assert "Perfis & Permissões" in html
    assert "Surfaces & Domínios" in html
    assert 'id="aiMcpContextHelp"' in html
    assert 'id="aiMcpContextHelpTitle"' in html
    assert 'id="aiMcpContextHelpBody"' in html
    assert 'id="aiMcpContextHelpSteps"' in html
