from __future__ import annotations

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
            "label": "Rodar teste completo",
            "suite_id": "full_system_validation",
            "description": "Executa tudo que o robô já consegue validar hoje.",
            "highlight": True,
        },
        "post_deploy": {
            "label": "Rodar pós-deploy",
            "suite_id": "smoke_real_navigation",
            "description": "Checagem rápida de app online, login e navegação crítica.",
            "highlight": False,
        },
        "previous_failures": {
            "label": "Rodar falhas anteriores",
            "suite_id": "execution_diff",
            "description": "Reavalia regressões e mudanças recentes detectadas pelo robô.",
            "highlight": False,
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
        areas_with_error = sum(1 for area in areas if area.get("status") == "failed")

        return {
            "company": cls._serialize_company(active_company, company_id),
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
            "latest_run": latest_run,
            "technical_center_url": "/qa/e2e",
            "history_url": "/qa/e2e",
            "reports_url": "/qa/e2e",
            "evidence_url": (latest_run or {}).get("manifest_download_url"),
        }

    @classmethod
    def list_area_latest(cls, *, company_id: int, e2e_state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        e2e_state = e2e_state or E2EOperationsCenterService.build_frontend_state(None)
        suite_catalog = e2e_state.get("suite_catalog") or []
        latest_runs = e2e_state.get("latest_runs") or []
        fallback_run = latest_runs[0] if latest_runs else None
        failed_names = cls._failed_names(latest_runs)
        items: list[dict[str, Any]] = []

        seen_domains: set[str] = set()
        for suite in suite_catalog:
            domain = str(suite.get("domain") or "system")
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            area_runs = cls._runs_for_area(latest_runs, domain)
            latest = area_runs[0] if area_runs else fallback_run
            status = cls._area_status(domain, latest, failed_names)
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
            errors.append(
                {
                    "error_id": error_id,
                    "title": candidate.get("title") or "Falha detectada pelo robô",
                    "area_id": cls._infer_area_from_candidate(candidate),
                    "area_label": cls.AREA_LABELS.get(cls._infer_area_from_candidate(candidate), "Área não classificada"),
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
                    "manifest_download_url": candidate.get("manifest_download_url"),
                    "backlog_sync_url": candidate.get("backlog_sync_url"),
                    "status": "open",
                    "company_id": company_id,
                }
            )
        return errors

    @classmethod
    def start_run(cls, *, package_key: str | None, suite_id: str | None, environment: str, company_id: int) -> dict[str, Any]:
        package = cls._find_execution_target(str(package_key or ""))
        selected_suite = suite_id or package.get("suite_id")
        if not selected_suite:
            raise ValueError("Selecione um teste válido.")
        environment = str(package.get("forced_environment") or environment).upper()
        if environment not in {"DEV_FULL", "PROD_SAFE"}:
            raise ValueError("Ambiente inválido. Use DEV_FULL ou PROD_SAFE.")
        execution = E2ESupervisedExecutionService.start_execution(suite_id=selected_suite, environment=environment)
        return {
            "company_id": company_id,
            "package_key": package_key,
            "suite_id": selected_suite,
            "environment": environment,
            "execution": execution,
        }

    @classmethod
    def handle_error_action(cls, *, error_id: str, action: str, company_id: int, user_id: int | None, create_task_fn) -> dict[str, Any]:
        errors = cls.list_open_errors(company_id=company_id)
        error = next((item for item in errors if item["error_id"] == error_id), None)
        if not error:
            raise KeyError(error_id)
        if action == "create_backlog":
            run_id = error.get("run_id")
            if not run_id:
                raise ValueError("Erro sem run_id para sincronização com backlog.")
            return E2EOperationsCenterService.sync_backlog_candidates(
                str(run_id),
                user_id=user_id,
                company_id=company_id,
                create_task_fn=create_task_fn,
            )
        if action == "details":
            return {"error": error, "technical_center_url": "/qa/e2e"}
        raise ValueError("Ação inválida para o erro.")

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
    def _area_status(domain: str, latest: dict[str, Any] | None, failed_names: str) -> str:
        if not latest:
            return "observed"
        if domain.lower() in failed_names:
            return "failed"
        return str(latest.get("status") or "observed")

    @staticmethod
    def _build_error_id(candidate: dict[str, Any], index: int) -> str:
        return f"{candidate.get('run_id') or 'run'}-{index}"

    @staticmethod
    def _infer_area_from_candidate(candidate: dict[str, Any]) -> str:
        haystack = f"{candidate.get('title') or ''} {candidate.get('failed_step') or ''}".lower()
        for area in ("financial", "reports", "integrations", "workspace", "meetings", "processes", "contracts", "admin", "smoke"):
            if area in haystack:
                return area
        return "system"
