from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = BASE_DIR / "templates"


class _DummyUser:
    name = "QA"


class _DummyRequest:
    path = "/qa/robot-tests"
    args = {}


def test_robot_tests_center_template_renders_new_functional_layout():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.globals.update(
        url_for=lambda endpoint, **kwargs: f"/{endpoint.replace('.', '/')}",
        has_permission=lambda *_args, **_kwargs: True,
        is_platform_admin=lambda: True,
        current_user=_DummyUser(),
        request=_DummyRequest(),
        session={},
        static_asset_version=lambda *_args, **_kwargs: "test",
        get_flashed_messages=lambda **_kwargs: [],
    )

    template = env.get_template("modules/operations/robot_tests_center.html")
    html = template.render(
        active_company=SimpleNamespace(name="M1 - Empresa de Testes Versus"),
        state={
            "company": {"id": 9, "name": "M1 - Empresa de Testes Versus", "client_code": "M1"},
            "summary_cards": [
                {"label": "Último teste", "value": "2026-06-14", "hint": "Tudo certo", "tone": "success"},
                {"label": "Áreas verificadas", "value": 4, "hint": "Por área", "tone": "neutral"},
                {"label": "Erros abertos", "value": 1, "hint": "Aguardando", "tone": "danger"},
                {"label": "Áreas com atenção", "value": 1, "hint": "Financeiro", "tone": "warning"},
            ],
            "test_packages": [
                {"key": "complete", "label": "Teste completo", "description": "Tudo", "highlight": True, "available": True, "group": "main"},
                {"key": "smoke", "label": "Teste rápido", "description": "Rápido", "highlight": False, "available": True, "group": "main"},
                {"key": "financial", "label": "Gestão financeira", "description": "Financeiro", "highlight": False, "available": True, "group": "area"},
                {"key": "drift", "label": "Deriva de cobertura", "description": "Avançado", "highlight": False, "available": True, "group": "advanced"},
                {"key": "coverage_audit", "label": "Auditoria de cobertura total", "description": "Tudo mapeado", "highlight": True, "available": True, "group": "advanced"},
            ],
            "execution_packages": [
                {"key": "complete", "label": "Rodar teste completo", "description": "Tudo", "highlight": True, "available": True},
                {"key": "inventory_update", "label": "Atualizar inventário", "description": "Telas, campos, botões, links e rotas", "highlight": False, "available": True},
                {"key": "post_deploy", "label": "Rodar pós-deploy", "description": "Rápido", "highlight": False, "available": True},
                {"key": "previous_failures", "label": "Rodar falhas anteriores", "description": "Falhas", "highlight": False, "available": True},
                {"key": "coverage_audit", "label": "Rodar auditoria de cobertura", "description": "Lacunas", "highlight": False, "available": True},
            ],
            "test_categories": [
                {
                    "key": "system_health",
                    "label": "Saúde do Sistema",
                    "summary": "Confere a base operacional.",
                    "suite_id": "smoke_real_navigation",
                    "items": ["login", "app online", "MCP health", "Sapiens"],
                    "items_count": 4,
                    "available": True,
                },
                {
                    "key": "coverage_drift",
                    "label": "Deriva de Cobertura",
                    "summary": "Descobre lacunas.",
                    "suite_id": "drift_detection",
                    "items": ["tela nova sem contrato", "endpoint novo sem cobertura"],
                    "items_count": 2,
                    "available": True,
                },
                {
                    "key": "total_coverage_matrix",
                    "label": "Matriz de Cobertura Total",
                    "summary": "Cruza tudo.",
                    "suite_id": "ui_inventory_contract_scan",
                    "items": ["rotas Flask", "templates/telas", "tools MCP"],
                    "items_count": 3,
                    "available": True,
                },
                {
                    "key": "cleanup_reversal",
                    "label": "Cleanup / Reversão",
                    "summary": "Desfaz movimentos.",
                    "suite_id": "full_system_validation",
                    "items": ["cancelar baixa", "cancelar faturamento"],
                    "items_count": 2,
                    "available": True,
                },
            ],
            "areas": [
                {
                    "area_id": "financial",
                    "label": "Gestão Financeira",
                    "status": "failed",
                    "status_label": "Atenção necessária",
                    "last_checked_at": "2026-06-14",
                    "errors_count": 1,
                    "run_id": "run-1",
                    "environment": "PROD_SAFE",
                    "summary": "Probe financeiro.",
                }
            ],
            "errors": [
                {
                    "error_id": "run-1-0",
                    "title": "Falha E2E: financial_functional_probe",
                    "area_id": "financial",
                    "area_label": "Gestão Financeira",
                    "severity": "Alta",
                    "message": "Resultado diferente do esperado.",
                    "expected_action": "Revisar regra funcional.",
                    "manifest_download_url": "/manifest",
                }
            ],
            "technical_center_url": "/qa/e2e",
            "history_url": "/qa/e2e",
            "reports_url": "/qa/e2e",
            "evidence_url": "/manifest",
        },
    )

    assert "Central do Robô de Testes" in html
    assert "Teste e inventário" in html
    assert "Modo padrão" in html
    assert "DEV_FULL — teste completo e inventário" in html
    assert "Rodar teste completo" in html
    assert "Atualizar inventário" in html
    assert "telas, campos, botões, links e rotas" in html
    assert "Resultado por área" in html
    assert "Erros encontrados e ações" in html
    assert "Disparar correção" in html
    assert "Suporte técnico" in html
    assert "Abrir tela técnica" in html
    assert "robotTestsRunMonitor" in html
    assert "O DEV_FULL continua rodando em segundo plano" in html
    assert "0% estimado" in html
    assert "Biblioteca de testes" not in html
    assert "Executar categoria" not in html
    assert "Rodar auditoria de cobertura" not in html
    assert "Rodar pós-deploy" not in html


def test_robot_tests_center_template_uses_robust_json_reader():
    template_source = (TEMPLATES_DIR / "modules" / "operations" / "robot_tests_center.html").read_text(encoding="utf-8")

    assert "function readRobotTestsJson(response)" in template_source
    assert "await response.text()" in template_source
    assert "'Accept': 'application/json'" in template_source
    assert "function startRunMonitor(execution)" in template_source
    assert "function estimateRunProgress(execution)" in template_source
    assert "RUN_MONITOR_EXPECTED_SECONDS = 600" in template_source
    assert "/api/configs/qa/e2e/executions/" in template_source
    assert "window.localStorage.setItem(RUN_MONITOR_STORAGE_KEY" in template_source
    assert "response.json()" not in template_source
