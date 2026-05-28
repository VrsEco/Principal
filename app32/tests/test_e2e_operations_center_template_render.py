from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = BASE_DIR / "templates"


class _DummyUser:
    name = "QA"


class _DummyRequest:
    path = "/qa/e2e"
    args = {}


def test_e2e_center_template_renders_operational_and_technical_tabs():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.globals.update(
        url_for=lambda endpoint, **kwargs: f"/{endpoint.replace('.', '/')}",
        has_permission=lambda *_args, **_kwargs: True,
        is_platform_admin=lambda: True,
        current_user=_DummyUser(),
        request=_DummyRequest(),
        session={},
        static_asset_version=lambda *_args, **_kwargs: "test",
    )

    template = env.get_template("modules/operations/e2e_center.html")
    html = template.render(
        state={
            "summary": {"total_runs": 3, "failed_runs": 1},
            "active_company": {"client_code": "VRS", "name": "Versus"},
            "execution_modes": [
                {"key": "DEV_FULL", "label": "DEV_FULL"},
                {"key": "PROD_SAFE", "label": "PROD_SAFE"},
            ],
            "operational_view": {
                "tab_labels": {"operational": "Visão Operacional", "technical": "Visão Técnica"},
                "coverage": {
                    "cards": [{"label": "Itens mapeados", "value": 12, "hint": "Itens já reconhecidos."}],
                    "modules": [{"module_label": "Meu Trabalho", "elements": 4, "actions": 6, "reports": 1, "criticality": "alta"}],
                    "matrix": [
                        {
                            "item": "Telas e páginas",
                            "system_total": 12,
                            "covered_total": 10,
                            "system_description": "Telas existentes.",
                            "coverage_description": "Telas cobertas.",
                        }
                    ],
                },
                "execution": {
                    "cards": [{"label": "Rodadas analisadas", "value": 3, "hint": "Histórico recente."}],
                    "matrix": [
                        {
                            "item": "Rodadas executadas",
                            "system_description": "Últimas execuções registradas.",
                            "coverage_description": "3 rodadas analisadas.",
                        }
                    ],
                    "latest_scope": [{"run_id": "run_1", "environment": "DEV_FULL", "tested": ["smoke"], "approved": 1, "reproved": 0, "status": "passed", "status_label": "Passou"}],
                },
                "issues": {
                    "matrix": [{"item": "Falha E2E: smoke", "system_description": "O fluxo falhou.", "coverage_description": "Revisar fluxo.", "severity": "alta", "severity_label": "Alta prioridade", "impact": "Afeta acesso.", "environment": "DEV_FULL", "manifest_download_url": "/manifest", "backlog_sync_url": "/sync"}],
                    "items": [{"element": "Falha E2E: smoke", "issue": "O fluxo falhou.", "severity": "alta", "severity_label": "Alta prioridade", "impact": "Afeta acesso.", "suggestion": "Revisar fluxo.", "environment": "DEV_FULL", "manifest_download_url": "/manifest", "backlog_sync_url": "/sync"}],
                    "empty_message": "Nenhum problema.",
                },
            },
            "filters": {"environments": ["ALL", "DEV_FULL"], "statuses": ["ALL", "passed"], "suites": ["ALL", "smoke_real_navigation"]},
            "latest_diff": {"status": "stable", "regressions": [], "recovered": [], "new_journeys": []},
            "latest_by_mode": [],
            "latest_runs": [],
            "suite_catalog": [{"suite_id": "smoke_real_navigation", "label": "Smoke principal", "domain": "core"}],
            "supervised_executions": [],
            "runbooks": [],
            "commands": [],
        }
    )

    assert "Executar teste agora" in html
    assert "Iniciar teste" in html
    assert "Visão Operacional" in html
    assert "Visão Técnica" in html
    assert "O que o robô já cobre" in html
    assert "O que existe no sistema" in html
    assert "O que o teste cobre" in html
    assert "O que foi executado" in html
    assert "O que o teste mostrou" in html
    assert "O que precisa corrigir agora" in html
    assert "O que está errado" in html
    assert "Como o Squad pode corrigir" in html
