from __future__ import annotations

import os
from typing import Any

from services.e2e_operations_center_service import E2EOperationsCenterService

try:
    from app32.tests.e2e.core.e2e_supervised_execution_service import E2ESupervisedExecutionService
except ModuleNotFoundError:  # pragma: no cover - compatibilidade de import local
    from tests.e2e.core.e2e_supervised_execution_service import E2ESupervisedExecutionService


class RobotTestsCenterService:
    """Camada funcional/leiga da Central do Robô de Testes.

    A central nova não substitui o motor E2E: ela agrega, traduz e expõe os
    resultados em linguagem de negócio, sempre escopada pela empresa ativa.
    """

    TEST_PACKAGES = {
        "complete": {
            "label": "Teste completo",
            "suite_id": "full_system_validation",
            "description": "Use para checar se o sistema como um todo está saudável.",
            "highlight": True,
            "group": "main",
        },
        "mapping": {
            "label": "Mapear sistema",
            "suite_id": "inventory_system_scan",
            "description": "Avançado: procura telas/rotas novas e lacunas de cobertura.",
            "highlight": False,
            "group": "advanced",
        },
        "coverage_audit": {
            "label": "Auditoria de cobertura total",
            "suite_id": "full_coverage_autocorrect_audit",
            "description": "Confere rotas, telas, campos, botões, operações e tools; gera log de correções em AA.J.1.",
            "highlight": True,
            "group": "advanced",
        },
        "smoke": {
            "label": "Teste rápido",
            "suite_id": "smoke_real_navigation",
            "description": "Use depois de ajustes pequenos ou deploy: login e navegação principal.",
            "highlight": False,
            "group": "main",
        },
        "financial": {
            "label": "Gestão financeira",
            "suite_id": "financial_functional_probe",
            "description": "Testa as funcionalidades financeiras já mapeadas.",
            "highlight": False,
            "group": "area",
        },
        "reports": {
            "label": "Relatórios",
            "suite_id": "reports_functional_probe",
            "description": "Confere abertura, geração e exportação de relatórios.",
            "highlight": False,
            "group": "area",
        },
        "integrations": {
            "label": "MCP / Sapiens / IA",
            "suite_id": "integrations_functional_probe",
            "description": "Testa integrações e contratos básicos de IA.",
            "highlight": False,
            "group": "area",
        },
        "drift": {
            "label": "Deriva de cobertura",
            "suite_id": "drift_detection",
            "description": "Avançado: compara o sistema atual com o que o robô conhece.",
            "highlight": False,
            "group": "advanced",
        },
    }

    EXECUTION_PACKAGES = {
        "complete": {
            "label": "Fazer teste completo DEV_FULL",
            "suite_id": "full_system_validation",
            "description": "Executa tudo que o robô já consegue validar hoje.",
            "highlight": True,
            "forced_environment": "DEV_FULL",
        },
        "inventory_update": {
            "label": "Atualizar inventário",
            "suite_id": "ui_inventory_contract_scan",
            "description": "Atualiza telas, campos, botões, links e rotas que o robô conhece.",
            "highlight": False,
            "forced_environment": "DEV_FULL",
        },
        "post_deploy": {
            "label": "Rodar pós-deploy",
            "suite_id": "smoke_real_navigation",
            "description": "Checagem rápida de app online, login e navegação crítica.",
            "highlight": False,
        },
        "previous_failures": {
            "label": "Revisar pendências",
            "suite_id": "execution_diff",
            "description": "Reexecuta a revisão em cima das pendências e regressões encontradas.",
            "highlight": False,
            "forced_environment": "DEV_FULL",
        },
        "coverage_audit": {
            "label": "Cobrir tudo + AA.J.1",
            "suite_id": "full_coverage_autocorrect_audit",
            "description": "Um botão para auditar cobertura total e criar log/cards de correção automática em AA.J.1.",
            "highlight": True,
            "forced_environment": "DEV_FULL",
        },
        "safe_environment": {
            "label": "Rodar modo seguro",
            "suite_id": "full_system_validation",
            "description": "Executa em PROD_SAFE, sem ações destrutivas.",
            "highlight": False,
            "forced_environment": "PROD_SAFE",
        },
    }

    TEST_CATEGORIES = [
        {
            "key": "system_health",
            "label": "Saúde do Sistema",
            "summary": "Confere se a base operacional está viva antes de aprofundar os testes.",
            "suite_id": "smoke_real_navigation",
            "items": ["login", "app online", "MCP health", "Sapiens", "WhatsApp/webhook, quando aplicável"],
        },
        {
            "key": "coverage_drift",
            "label": "Deriva de Cobertura",
            "summary": "Descobre o que existe no sistema e ainda não está contratado no robô.",
            "suite_id": "drift_detection",
            "items": [
                "tela nova sem contrato",
                "Tool MCP nova sem contrato",
                "endpoint novo sem cobertura",
                "campo/select novo",
                "ação nova em tela existente",
                "capability/permissão nova",
                "jornada nova sem cleanup",
            ],
        },
        {
            "key": "total_coverage_matrix",
            "label": "Matriz de Cobertura Total",
            "summary": "Cruza superfície real versus contratos de teste para responder se tudo está contemplado.",
            "suite_id": "ui_inventory_contract_scan",
            "items": [
                "rotas Flask",
                "templates/telas",
                "campos input/select/textarea",
                "botões/links/actions",
                "endpoints consumidos por JS",
                "tools MCP e surfaces",
                "cenários sem contrato ou apenas em backlog",
            ],
        },
        {
            "key": "ui_screens",
            "label": "Telas / UI",
            "summary": "Valida experiência real do usuário em telas, botões, formulários e persistência.",
            "suite_id": "workspace_functional_probe",
            "items": [
                "abrir tela",
                "validar carregamento",
                "validar botões",
                "validar abas/modais",
                "validar selects/autocompletes",
                "preencher formulário",
                "salvar",
                "pesquisar",
                "reabrir",
                "validar persistência",
                "editar",
                "inativar/excluir/cancelar",
            ],
        },
        {
            "key": "critical_registries",
            "label": "Cadastros críticos",
            "summary": "Cobre cadastros mestres que sustentam os movimentos do sistema.",
            "suite_id": "financial_functional_probe",
            "items": [
                "favorecidos",
                "clientes",
                "produtos/serviços",
                "contas bancárias",
                "centros de custo",
                "plano de contas",
                "demais cadastros conforme matriz",
            ],
        },
        {
            "key": "movements_processing",
            "label": "Movimentos e processamentos",
            "summary": "Testa criação, processamento, efeitos derivados e cancelamentos.",
            "suite_id": "financial_functional_probe",
            "items": [
                "pedidos",
                "faturamento",
                "títulos financeiros",
                "baixas",
                "conciliação bancária",
                "cancelamentos",
                "efeitos derivados entre módulos",
            ],
        },
        {
            "key": "reports",
            "label": "Relatórios",
            "summary": "Garante que relatórios geram, exportam e respeitam filtros/tenant.",
            "suite_id": "reports_functional_probe",
            "items": [
                "abrir relatório",
                "aplicar filtros",
                "gerar",
                "exportar PDF/Excel/HTML, quando houver",
                "validar conteúdo mínimo",
                "validar tenant/período/filtros",
            ],
        },
        {
            "key": "mcp_tools",
            "label": "MCP / Tools",
            "summary": "Valida contratos técnicos, surfaces, permissões e bloqueios sensíveis.",
            "suite_id": "mcp_concurrency_probe",
            "items": [
                "registry de tools",
                "surface correta",
                "schema",
                "permissões",
                "execução da tool",
                "parâmetros obrigatórios",
                "resposta técnica esperada",
                "bloqueio de tool sensível em surface indevida",
            ],
        },
        {
            "key": "sapiens_ai",
            "label": "Sapiens / IA",
            "summary": "Confere intenção, domínio canônico, contexto, confirmação humana e resposta final.",
            "suite_id": "integrations_functional_probe",
            "items": [
                "classificação de intenção",
                "domínio canônico",
                "resolução de empresa",
                "contexto multi-turn",
                "resposta sem alucinação",
                "pedido de esclarecimento quando ambíguo",
                "confirmação humana antes de mutação",
                "resposta final coerente com tool/resultados",
            ],
        },
        {
            "key": "whatsapp",
            "label": "WhatsApp",
            "summary": "Valida entrada externa, identidade, roteamento e decisão humana sobre achados.",
            "suite_id": "integrations_functional_probe",
            "items": [
                "webhook",
                "identificação do usuário",
                "resolução de empresa",
                "roteamento para Sapiens",
                "resposta",
                "retry/idempotência",
                "decisão humana sobre achados",
            ],
        },
        {
            "key": "permissions",
            "label": "Permissões",
            "summary": "Garante que menus, rotas, botões, actions e MCP respeitam perfis.",
            "suite_id": "admin_functional_probe",
            "items": [
                "menus por perfil",
                "botões por perfil",
                "rotas por perfil",
                "actions por perfil",
                "MCP surfaces por perfil",
                "tentativa de acesso indevido",
            ],
        },
        {
            "key": "negative_scenarios",
            "label": "Cenários negativos",
            "summary": "Força erros esperados para validar proteção, mensagens e bloqueios.",
            "suite_id": "full_system_validation",
            "items": [
                "dados inválidos",
                "tenant incorreto",
                "registro inexistente",
                "valor divergente",
                "título já baixado",
                "ação duplicada",
                "prompt ambíguo/malicioso",
                "permissão insuficiente",
            ],
        },
        {
            "key": "idempotency_retry",
            "label": "Idempotência / Retry",
            "summary": "Verifica repetição segura de ações, webhooks e processamentos.",
            "suite_id": "full_system_validation",
            "items": [
                "duplo clique",
                "reenvio de webhook",
                "repetir faturamento",
                "repetir baixa",
                "repetir conciliação",
                "repetir criação via Sapiens/Tool",
            ],
        },
        {
            "key": "visual_regression",
            "label": "Regressão visual",
            "summary": "Detecta quebras visuais perceptíveis nas telas críticas.",
            "suite_id": "inventory_system_scan",
            "items": ["tela quebrada", "botão ausente", "modal cortado", "coluna invisível", "layout alterado", "snapshot visual de telas críticas"],
        },
        {
            "key": "perceived_performance",
            "label": "Performance percebida",
            "summary": "Mede tempos percebidos em abertura, selects, salvamento, relatórios e IA.",
            "suite_id": "report_filter_volume_probe",
            "items": ["tempo de abrir tela", "carregar selects", "salvar", "processar", "gerar relatório", "responder via Sapiens"],
        },
        {
            "key": "cross_channel",
            "label": "Cross-channel",
            "summary": "Compara consistência entre UI, MCP, Sapiens, WhatsApp e relatórios.",
            "suite_id": "integrations_functional_probe",
            "items": ["UI vs MCP", "UI vs Sapiens", "Sapiens Web vs WhatsApp", "relatórios vs dados operacionais", "mesma consulta com mesmo tenant/permissão"],
        },
        {
            "key": "cleanup_reversal",
            "label": "Cleanup / Reversão",
            "summary": "Garante que movimentos podem ser desfeitos na ordem correta sem resíduo ativo.",
            "suite_id": "full_system_validation",
            "items": ["desfazer conciliação", "cancelar baixa", "cancelar faturamento", "cancelar pedido", "inativar cadastros", "validar ausência de resíduo ativo"],
        },
        {
            "key": "final_report_incidents",
            "label": "Relatório final / Incidentes",
            "summary": "Consolida achados, severidade, evidências e abertura aprovada de incidentes/cards.",
            "suite_id": "execution_diff",
            "items": ["consolidar achados", "classificar severidade", "anexar evidências", "sugerir decisão", "enviar para Sapiens/WhatsApp", "abrir card/incidente quando aprovado"],
        },
    ]

    AREA_LABELS = {
        "auth": "Login e Acesso",
        "workspace": "Meu Trabalho",
        "meetings": "Reuniões",
        "integrations": "MCP / Sapiens / IA",
        "work_journey": "Rotina e Calendário",
        "processes": "Processos",
        "financial": "Gestão Financeira",
        "contracts": "Contratos e Fiscal",
        "reports": "Relatórios",
        "admin": "Administração",
        "governance": "Governança dos Testes",
        "smoke": "Navegação Crítica",
        "system": "Sistema Completo",
        "mcp": "MCP Runtime",
    }

    REVIEW_SUITE_BY_AREA = {
        "admin": "admin_functional_probe",
        "contracts": "contracts_functional_probe",
        "financial": "financial_functional_probe",
        "governance": "full_coverage_autocorrect_audit",
        "integrations": "integrations_functional_probe",
        "mcp": "mcp_concurrency_probe",
        "reports": "reports_functional_probe",
        "smoke": "smoke_real_navigation",
        "system": "full_system_validation",
        "workspace": "workspace_functional_probe",
    }

    STATUS_LABELS = {
        "passed": "Tudo certo",
        "failed": "Atenção necessária",
        "observed": "Não testado neste ciclo",
        "running": "Em execução",
    }

    @classmethod
    def build_overview_state(cls, *, active_company: Any, company_id: int) -> dict[str, Any]:
        e2e_state = E2EOperationsCenterService.build_frontend_state(active_company)
        areas = cls.list_area_latest(company_id=company_id, e2e_state=e2e_state)
        errors = cls.list_open_errors(company_id=company_id, e2e_state=e2e_state)
        latest_run = (e2e_state.get("latest_runs") or [None])[0]
        history = cls.list_recent_history(e2e_state=e2e_state)
        history_diff = cls.build_history_diff(e2e_state=e2e_state)
        coverage_summary = cls.build_coverage_summary(e2e_state=e2e_state)
        executive_summary = cls.build_executive_summary(
            latest_run=latest_run,
            errors=errors,
            history_diff=history_diff,
            coverage_summary=coverage_summary,
        )
        areas_with_error = sum(1 for area in areas if area.get("status") == "failed")

        return {
            "company": cls._serialize_company(active_company, company_id),
            "executive_summary": executive_summary,
            "coverage_summary": coverage_summary,
            "history_diff": history_diff,
            "summary_cards": [
                {
                    "label": "Último teste",
                    "value": cls._format_last_check(latest_run),
                    "hint": cls.STATUS_LABELS.get((latest_run or {}).get("status"), "Aguardando execução"),
                    "tone": cls._tone((latest_run or {}).get("status")),
                },
                {
                    "label": "Áreas verificadas",
                    "value": len(areas),
                    "hint": "Último resultado consolidado por área.",
                    "tone": "neutral",
                },
                {
                    "label": "Erros abertos",
                    "value": len(errors),
                    "hint": "Problemas aguardando correção ou decisão.",
                    "tone": "danger" if errors else "success",
                },
                {
                    "label": "Áreas com atenção",
                    "value": areas_with_error,
                    "hint": "Áreas cujo último teste encontrou falha.",
                    "tone": "warning" if areas_with_error else "success",
                },
            ],
            "execution_packages": cls.list_execution_packages(e2e_state=e2e_state),
            "test_categories": cls.list_test_categories(e2e_state=e2e_state),
            "test_packages": cls.list_test_packages(e2e_state=e2e_state),
            "areas": areas,
            "errors": errors,
            "history": history,
            "operational_view": e2e_state.get("operational_view") or {},
            "ui_inventory": e2e_state.get("ui_inventory"),
            "ui_contracts": e2e_state.get("ui_contracts"),
            "ui_safe_execution": e2e_state.get("ui_safe_execution"),
            "devfull_transactional": e2e_state.get("devfull_transactional"),
            "latest_run": latest_run,
            "technical_center_url": "/qa/robot-tests",
            "history_url": "/qa/robot-tests",
            "reports_url": "/qa/robot-tests",
            "evidence_url": (latest_run or {}).get("manifest_download_url"),
        }

    @classmethod
    def build_executive_summary(
        cls,
        *,
        latest_run: dict[str, Any] | None,
        errors: list[dict[str, Any]],
        history_diff: dict[str, Any],
        coverage_summary: dict[str, Any],
    ) -> dict[str, Any]:
        pending_total = len(errors)
        regressions_total = int(history_diff.get("regressions_total") or 0)
        recovered_total = int(history_diff.get("recovered_total") or 0)
        gaps_total = int(coverage_summary.get("coverage_gaps_total") or 0)
        latest_status = str((latest_run or {}).get("status") or "observed")
        if not latest_run:
            tone = "neutral"
            title = "Aguardando primeira verificação"
        elif pending_total or regressions_total or gaps_total:
            tone = "danger" if pending_total or regressions_total else "warning"
            title = "Requer atenção"
        elif latest_status == "passed":
            tone = "success"
            title = "Tudo certo"
        else:
            tone = cls._tone(latest_status)
            title = cls.STATUS_LABELS.get(latest_status, "Em análise")
        message = (
            f"{pending_total} pendência(s) aberta(s); "
            f"{regressions_total} regressão(ões) nova(s); "
            f"{recovered_total} correção(ões) detectada(s); "
            f"{gaps_total} gap(s) de cobertura."
        )
        return {
            "title": title,
            "message": message,
            "tone": tone,
            "latest_status": latest_status,
            "pending_total": pending_total,
            "regressions_total": regressions_total,
            "recovered_total": recovered_total,
            "coverage_gaps_total": gaps_total,
        }

    @classmethod
    def build_history_diff(cls, *, e2e_state: dict[str, Any] | None = None) -> dict[str, Any]:
        e2e_state = e2e_state or {}
        diff = e2e_state.get("latest_diff") or e2e_state.get("execution_diff") or {}
        regressions_total = cls._count_collection(diff, "regressions", "new_failures", "new_errors")
        recovered_total = cls._count_collection(diff, "recovered", "fixed", "resolved")
        new_journeys_total = cls._count_collection(diff, "new_journeys", "added_journeys")
        if regressions_total:
            summary = "Há regressões novas em relação à verificação anterior."
            tone = "danger"
        elif recovered_total:
            summary = "Há correções detectadas desde a última verificação."
            tone = "success"
        else:
            summary = "Sem regressões novas detectadas no comparativo disponível."
            tone = "neutral"
        return {
            "regressions_total": regressions_total,
            "recovered_total": recovered_total,
            "new_journeys_total": new_journeys_total,
            "summary": summary,
            "tone": tone,
        }

    @classmethod
    def build_coverage_summary(cls, *, e2e_state: dict[str, Any] | None = None) -> dict[str, Any]:
        e2e_state = e2e_state or {}
        inventory = e2e_state.get("ui_inventory") or {}
        screens_total = cls._first_int(inventory, "screens_total", "templates_total", "routes_rendered_total")
        fields_total = cls._first_int(inventory, "fields_total", "inputs_total", "form_fields_total")
        buttons_total = cls._first_int(inventory, "buttons_total", "actions_total")
        links_total = cls._first_int(inventory, "links_total")
        coverage_gaps_total = cls._first_int(inventory, "coverage_gaps_total", "gaps_total", "missing_contracts_total")
        covered_total = cls._first_int(inventory, "automatic_items_covered_total", "covered_items_total", "covered_total")
        return {
            "label": "Inventário de cobertura",
            "status": "updated" if inventory else "missing",
            "generated_at": inventory.get("generated_at") or inventory.get("run_id") or "Sem inventário",
            "screens_total": screens_total,
            "fields_total": fields_total,
            "buttons_total": buttons_total,
            "links_total": links_total,
            "coverage_gaps_total": coverage_gaps_total,
            "automatic_items_covered_total": covered_total,
            "tone": "success" if inventory and coverage_gaps_total == 0 else ("warning" if inventory else "neutral"),
        }

    @classmethod
    def list_recent_history(cls, *, e2e_state: dict[str, Any] | None = None, limit: int = 8) -> list[dict[str, Any]]:
        e2e_state = e2e_state or E2EOperationsCenterService.build_frontend_state(None)
        history: list[dict[str, Any]] = []
        for run in (e2e_state.get("latest_runs") or [])[:limit]:
            history.append(
                {
                    "run_id": run.get("run_id"),
                    "generated_at": run.get("generated_at") or "Sem data",
                    "environment": run.get("environment") or "-",
                    "status": run.get("status") or "observed",
                    "status_label": cls.STATUS_LABELS.get(run.get("status"), "Em análise"),
                    "journeys_total": int(run.get("journeys_total") or 0),
                    "journeys_failed": int(run.get("journeys_failed") or 0),
                    "manifest_download_url": run.get("manifest_download_url"),
                }
            )
        return history

    @classmethod
    def list_area_latest(cls, *, company_id: int, e2e_state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        e2e_state = e2e_state or E2EOperationsCenterService.build_frontend_state(None)
        suite_catalog = e2e_state.get("suite_catalog") or []
        latest_runs = e2e_state.get("latest_runs") or []
        fallback_run = latest_runs[0] if latest_runs else None
        items: list[dict[str, Any]] = []

        seen_domains: set[str] = set()
        for suite in suite_catalog:
            domain = str(suite.get("domain") or "system")
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            area_runs = cls._runs_for_area(latest_runs, domain)
            latest = area_runs[0] if area_runs else fallback_run
            failed_names = cls._failed_names([latest] if latest else [])
            status = cls._area_status(domain, latest, failed_names, has_area_run=bool(area_runs))
            items.append(cls._build_area_record(domain=domain, status=status, latest=latest, suite=suite, company_id=company_id))

        preferred_order = ["system", "smoke", "financial", "reports", "integrations", "workspace", "processes", "contracts", "admin", "governance"]
        items.sort(key=lambda item: preferred_order.index(item["area_id"]) if item["area_id"] in preferred_order else 99)
        return items

    @classmethod
    def get_area_latest(cls, *, area_id: str, company_id: int) -> dict[str, Any]:
        areas = cls.list_area_latest(company_id=company_id)
        for area in areas:
            if area["area_id"] == area_id:
                return area
        raise KeyError(area_id)

    @classmethod
    def list_open_errors(cls, *, company_id: int, e2e_state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        e2e_state = e2e_state or E2EOperationsCenterService.build_frontend_state(None)
        candidates = e2e_state.get("backlog_candidates") or []
        errors: list[dict[str, Any]] = []
        for index, candidate in enumerate(candidates):
            candidate_company_id = candidate.get("company_id")
            if candidate_company_id and int(candidate_company_id) != int(company_id):
                continue
            error_id = cls._build_error_id(candidate, index)
            area_id = cls._infer_area_from_candidate(candidate)
            errors.append(
                {
                    "error_id": error_id,
                    "title": candidate.get("title") or "Falha detectada pelo robô",
                    "error_signature": cls._build_error_signature(candidate),
                    "area_id": area_id,
                    "area_label": cls.AREA_LABELS.get(area_id, "Área não classificada"),
                    "review_suite_id": cls.REVIEW_SUITE_BY_AREA.get(area_id, "execution_diff"),
                    "severity": "Alta" if candidate.get("environment") == "PROD_SAFE" else "Média",
                    "message": E2EOperationsCenterService._humanize_failure(
                        str(candidate.get("failure_type") or "unknown"),
                        candidate.get("failed_step"),
                    ),
                    "expected_action": E2EOperationsCenterService.FAILURE_SUGGESTIONS.get(
                        str(candidate.get("failure_type") or "unknown"),
                        E2EOperationsCenterService.FAILURE_SUGGESTIONS["unknown"],
                    ),
                    "run_id": candidate.get("run_id"),
                    "environment": candidate.get("environment"),
                    "failure_type": candidate.get("failure_type"),
                    "failed_step": candidate.get("failed_step"),
                    "manifest_download_url": candidate.get("manifest_download_url"),
                    "backlog_sync_url": candidate.get("backlog_sync_url"),
                    "status": "open",
                    "company_id": company_id,
                }
            )
        for error in errors:
            error["squad_prompt"] = cls._build_error_squad_prompt(error)
        cls._attach_existing_error_cards(errors)
        return errors

    @classmethod
    def start_run(
        cls,
        *,
        package_key: str | None,
        suite_id: str | None,
        environment: str,
        company_id: int,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        package = cls._find_execution_target(str(package_key or ""))
        selected_suite = suite_id or package.get("suite_id")
        review_scope: dict[str, Any] | None = None
        if str(package_key or "") == "previous_failures" and not suite_id:
            selected_suite, review_scope = cls._select_pending_review_suite(company_id=company_id)
        if not selected_suite:
            raise ValueError("Selecione um teste válido.")
        environment = str(package.get("forced_environment") or environment).upper()
        if environment not in {"DEV_FULL", "PROD_SAFE"}:
            raise ValueError("Ambiente inválido. Use DEV_FULL ou PROD_SAFE.")
        execution_user_id = cls._resolve_dev_full_robot_user_id(
            environment=environment,
            suite_id=str(selected_suite),
            fallback_user_id=user_id,
        )
        execution = E2ESupervisedExecutionService.start_execution(
            suite_id=selected_suite,
            environment=environment,
            company_id=company_id,
            user_id=execution_user_id,
        )
        payload = {
            "company_id": company_id,
            "package_key": package_key,
            "suite_id": selected_suite,
            "environment": environment,
            "execution": execution,
        }
        if review_scope:
            payload["review_scope"] = review_scope
        return payload

    @classmethod
    def _select_pending_review_suite(cls, *, company_id: int) -> tuple[str, dict[str, Any]]:
        errors = cls.list_open_errors(company_id=company_id)
        if not errors:
            return "execution_diff", {
                "mode": "no_open_errors",
                "areas": [],
                "message": "Sem pendências abertas; usando comparativo geral.",
            }
        areas = sorted({str(error.get("area_id") or "system") for error in errors})
        if len(areas) == 1:
            area_id = areas[0]
            suite_id = cls.REVIEW_SUITE_BY_AREA.get(area_id, "execution_diff")
            return suite_id, {
                "mode": "single_area",
                "areas": areas,
                "message": f"Revisão focada em {cls.AREA_LABELS.get(area_id, area_id)}.",
            }
        return "full_system_validation", {
            "mode": "multi_area",
            "areas": areas,
            "message": "Pendências em múltiplas áreas; usando DEV_FULL completo.",
        }

    @classmethod
    def _resolve_dev_full_robot_user_id(
        cls,
        *,
        environment: str,
        suite_id: str,
        fallback_user_id: int | None,
    ) -> int | None:
        """Usa ator admin/robô para DEV_FULL de cobertura total.

        O botão da Central pode ser acionado por usuário com acesso à tela, mas
        sem permissão em todas as superfícies que o DEV_FULL precisa percorrer.
        Para evitar falsos 403, o robô executa os pacotes globais de DEV com um
        usuário técnico/admin ativo. PROD_SAFE preserva o usuário chamador.
        """
        if str(environment or "").upper() != "DEV_FULL":
            return fallback_user_id
        if suite_id not in {
            "full_system_validation",
            "full_coverage_autocorrect_audit",
            "devfull_full_app_validation",
            "ui_inventory_contract_scan",
            "inventory_system_scan",
        }:
            return fallback_user_id

        configured = str(os.environ.get("APP32_E2E_DEV_USER_ID") or "").strip()
        if configured.isdigit():
            return int(configured)

        try:
            from models.user import User
        except Exception:
            return fallback_user_id

        preferred_emails = (
            "admin@gestaoversus.com.br",
            "teste@gestaoversus.com.br",
            "mff2000@gmail.com",
        )
        preferred = (
            User.query.filter(
                User.email.in_(preferred_emails),
                User.role == "admin",
                User.is_active.is_(True),
            )
            .order_by(User.id.asc())
            .first()
        )
        if preferred:
            return int(preferred.id)
        active_admin = User.query.filter_by(role="admin", is_active=True).order_by(User.id.asc()).first()
        return int(active_admin.id) if active_admin else fallback_user_id

    @classmethod
    def handle_error_action(cls, *, error_id: str, action: str, company_id: int, user_id: int | None, create_task_fn) -> dict[str, Any]:
        errors = cls.list_open_errors(company_id=company_id)
        error = next((item for item in errors if item["error_id"] == error_id), None)
        if not error:
            raise KeyError(error_id)
        if action == "create_backlog":
            if error.get("task_id"):
                return {
                    "created": [],
                    "existing": [cls._serialize_error_task(error)],
                    "requested": 1,
                    "error": error,
                }
            task, task_error = create_task_fn(
                source_type="e2e_failure",
                title=error["title"],
                description=cls._build_error_backlog_description(error),
                user_id=user_id,
                company_id=company_id,
                metadata=cls._build_error_backlog_metadata(error),
                priority="high",
            )
            if task_error:
                raise ValueError(str(task_error))
            linked = cls._serialize_task_link(task)
            return {"created": [linked], "existing": [], "requested": 1, "error": {**error, **linked}}
        if action == "details":
            return {"error": error, "technical_center_url": "/qa/e2e"}
        raise ValueError("Ação inválida para o erro.")

    @classmethod
    def _build_error_backlog_description(cls, error: dict[str, Any]) -> str:
        return (
            "Falha detectada pela Central do Robô de Testes.\n"
            f"Erro do robô: {error.get('error_id')}\n"
            f"Área: {error.get('area_label')} ({error.get('area_id')})\n"
            f"Run: {error.get('run_id')}\n"
            f"Ambiente: {error.get('environment')}\n"
            f"Mensagem: {error.get('message')}\n"
            f"Ação esperada: {error.get('expected_action')}\n"
            f"Suite sugerida: {error.get('review_suite_id')}\n"
            f"Evidência: {error.get('manifest_download_url') or 'Não informada'}"
        )

    @classmethod
    def _build_error_backlog_metadata(cls, error: dict[str, Any]) -> dict[str, Any]:
        return {
            "robot_error_signature": error.get("error_signature"),
            "robot_error_id": error.get("error_id"),
            "run_id": error.get("run_id"),
            "environment": error.get("environment"),
            "area_id": error.get("area_id"),
            "area_label": error.get("area_label"),
            "review_suite_id": error.get("review_suite_id"),
            "failure_type": error.get("failure_type"),
            "failed_step": error.get("failed_step"),
            "manifest_download_url": error.get("manifest_download_url"),
            "squad_prompt": error.get("squad_prompt"),
        }

    @classmethod
    def _attach_existing_error_cards(cls, errors: list[dict[str, Any]]) -> None:
        if not errors:
            return
        try:
            from models.project import Project, ProjectTask
        except Exception:
            return
        try:
            from services.agent_backlog_service import DEFAULT_ROBOT_FAILURE_PROJECT_CODE

            project = Project.query.filter_by(code=DEFAULT_ROBOT_FAILURE_PROJECT_CODE).first()
            if not project:
                return
            tasks = (
                ProjectTask.query.filter_by(project_id=project.id, is_deleted=False)
                .order_by(ProjectTask.created_at.desc())
                .limit(200)
                .all()
            )
        except Exception:
            return
        for error in errors:
            signature_marker = f"robot_error_signature: {error.get('error_signature')}"
            marker = f"robot_error_id: {error.get('error_id')}"
            fallback = f"Run: {error.get('run_id')}"
            matched = None
            for task in tasks:
                notes = str(getattr(task, "notes", None) or "")
                how = str(getattr(task, "how", None) or "")
                haystack = f"{notes}\n{how}"
                if signature_marker in haystack or marker in haystack or (error.get("run_id") and fallback in haystack and str(error.get("title") or "") in haystack):
                    matched = task
                    break
            if matched:
                error.update(cls._serialize_task_link(matched))

    @staticmethod
    def _serialize_task_link(task: Any) -> dict[str, Any]:
        task_id = getattr(task, "id", None)
        project_id = getattr(task, "project_id", None)
        task_code = getattr(task, "code", None) or getattr(task, "task_code", None)
        task_url = f"/projects/{project_id}/manage?task_id={task_id}" if project_id and task_id else None
        task_status = getattr(task, "status", None)
        task_stage = getattr(task, "stage", None)
        is_completed = str(task_status or "").lower() == "completed" or str(task_stage or "").lower() == "completed"
        return {
            "task_id": task_id,
            "task_code": task_code,
            "task_url": task_url,
            "task_status": task_status,
            "task_stage": task_stage,
            "card_treatment_status": "treated_pending_revalidation" if is_completed else "open_card",
            "card_treatment_label": "Tratada aguardando revalidação" if is_completed else "Card aberto",
        }

    @staticmethod
    def _serialize_error_task(error: dict[str, Any]) -> dict[str, Any]:
        return {
            "task_id": error.get("task_id"),
            "task_code": error.get("task_code"),
            "task_url": error.get("task_url"),
            "task_status": error.get("task_status"),
            "task_stage": error.get("task_stage"),
            "card_treatment_status": error.get("card_treatment_status"),
            "card_treatment_label": error.get("card_treatment_label"),
        }

    @classmethod
    def _build_error_squad_prompt(cls, error: dict[str, Any]) -> str:
        try:
            from services.agent_backlog_service import build_robot_failure_prompt
        except Exception:
            return cls._build_error_backlog_description(error)
        return build_robot_failure_prompt(
            title=str(error.get("title") or "Falha detectada pelo robô"),
            description=cls._build_error_backlog_description(error),
            metadata=cls._build_error_backlog_metadata({**error, "squad_prompt": None}),
        )

    @classmethod
    def _build_error_signature(cls, candidate: dict[str, Any]) -> str:
        raw = "|".join(
            str(candidate.get(key) or "").strip().lower()
            for key in ("title", "failure_type", "failed_step", "journey", "suite_id")
        )
        return raw or cls._build_error_id(candidate, 0)

    @classmethod
    def list_test_packages(cls, *, e2e_state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        e2e_state = e2e_state or {}
        available = {item.get("suite_id") for item in e2e_state.get("suite_catalog") or []}
        packages = []
        for key, item in cls.TEST_PACKAGES.items():
            package = dict(item)
            package["key"] = key
            package["available"] = not available or package["suite_id"] in available
            packages.append(package)
        return packages

    @classmethod
    def list_execution_packages(cls, *, e2e_state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return cls._serialize_catalog(cls.EXECUTION_PACKAGES, e2e_state=e2e_state)

    @classmethod
    def list_test_categories(cls, *, e2e_state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        e2e_state = e2e_state or {}
        available = {item.get("suite_id") for item in e2e_state.get("suite_catalog") or []}
        categories: list[dict[str, Any]] = []
        for category in cls.TEST_CATEGORIES:
            item = dict(category)
            item["available"] = not available or item["suite_id"] in available
            item["items_count"] = len(item.get("items") or [])
            categories.append(item)
        return categories

    @classmethod
    def _serialize_catalog(cls, catalog: dict[str, dict[str, Any]], *, e2e_state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        e2e_state = e2e_state or {}
        available = {item.get("suite_id") for item in e2e_state.get("suite_catalog") or []}
        items = []
        for key, value in catalog.items():
            item = dict(value)
            item["key"] = key
            item["available"] = not available or item["suite_id"] in available
            items.append(item)
        return items

    @classmethod
    def _find_execution_target(cls, package_key: str) -> dict[str, Any]:
        if package_key in cls.EXECUTION_PACKAGES:
            return cls.EXECUTION_PACKAGES[package_key]
        if package_key in cls.TEST_PACKAGES:
            return cls.TEST_PACKAGES[package_key]
        for category in cls.TEST_CATEGORIES:
            if category["key"] == package_key:
                return category
        return {}

    @staticmethod
    def _serialize_company(active_company: Any, company_id: int) -> dict[str, Any]:
        return {
            "id": company_id,
            "name": getattr(active_company, "name", None),
            "client_code": getattr(active_company, "client_code", None),
        }

    @staticmethod
    def _format_last_check(run: dict[str, Any] | None) -> str:
        if not run:
            return "Sem histórico"
        return str(run.get("generated_at") or run.get("run_id") or "Registrado")

    @staticmethod
    def _tone(status: str | None) -> str:
        if status == "passed":
            return "success"
        if status == "failed":
            return "danger"
        if status == "running":
            return "warning"
        return "neutral"

    @classmethod
    def _build_area_record(cls, *, domain: str, status: str, latest: dict[str, Any] | None, suite: dict[str, Any], company_id: int) -> dict[str, Any]:
        return {
            "area_id": domain,
            "label": cls.AREA_LABELS.get(domain, domain.replace("_", " ").title()),
            "status": status,
            "status_label": cls.STATUS_LABELS.get(status, "Não testado neste ciclo"),
            "last_checked_at": (latest or {}).get("generated_at") or "Sem execução",
            "errors_count": int((latest or {}).get("journeys_failed") or 0) if status == "failed" else 0,
            "run_id": (latest or {}).get("run_id"),
            "environment": (latest or {}).get("environment"),
            "summary": suite.get("summary") or "Área acompanhada pelo robô de testes.",
            "company_id": company_id,
            "manifest_download_url": (latest or {}).get("manifest_download_url"),
        }

    @staticmethod
    def _runs_for_area(runs: list[dict[str, Any]], domain: str) -> list[dict[str, Any]]:
        normalized = domain.lower()
        if normalized == "system":
            return [
                run
                for run in runs
                if "full_system" in str(run.get("root_dir") or run.get("manifest_path") or "").lower()
                or "devfull_full_app" in str(run.get("root_dir") or run.get("manifest_path") or "").lower()
                or any("full_system_validation" in str(name or "").lower() for name in (run.get("journey_names") or []))
                or any("devfull_full_app_validation" in str(name or "").lower() for name in (run.get("journey_names") or []))
            ]
        if normalized == "reporting":
            normalized = "reports"
        return [
            run
            for run in runs
            if normalized in " ".join(str(name or "").lower() for name in (run.get("journey_names") or []))
            or normalized in str(run.get("run_id") or "").lower()
        ]

    @staticmethod
    def _failed_names(runs: list[dict[str, Any]]) -> str:
        names: list[str] = []
        for run in runs:
            names.extend(str(item or "") for item in (run.get("failed_journey_names") or []))
        return " ".join(names).lower()

    @staticmethod
    def _area_status(domain: str, latest: dict[str, Any] | None, failed_names: str, *, has_area_run: bool = True) -> str:
        if not latest or not has_area_run:
            return "observed"
        if domain.lower() in failed_names:
            return "failed"
        if str(latest.get("status") or "") == "failed":
            return "passed"
        return str(latest.get("status") or "observed")

    @staticmethod
    def _build_error_id(candidate: dict[str, Any], index: int) -> str:
        return f"{candidate.get('run_id') or 'run'}-{index}"

    @staticmethod
    def _count_collection(payload: dict[str, Any], *keys: str) -> int:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            if isinstance(value, int):
                return value
            if isinstance(value, (list, tuple, set, dict)):
                return len(value)
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return 0

    @classmethod
    def _first_int(cls, payload: dict[str, Any], *keys: str) -> int:
        candidates = [payload]
        summary = payload.get("summary")
        if isinstance(summary, dict):
            candidates.append(summary)
        metrics = payload.get("metrics")
        if isinstance(metrics, dict):
            candidates.append(metrics)
        for candidate in candidates:
            for key in keys:
                value = candidate.get(key)
                if value is None:
                    continue
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
        return 0

    @staticmethod
    def _infer_area_from_candidate(candidate: dict[str, Any]) -> str:
        haystack = " ".join(
            str(candidate.get(key) or "")
            for key in ("title", "failed_step", "journey_name", "suite_id", "domain", "area_id")
        ).lower()
        for area in ("financial", "reports", "integrations", "mcp", "workspace", "meetings", "processes", "contracts", "admin", "smoke"):
            if area in haystack:
                return area
        return "system"
