from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from app32.tests.e2e.catalog.inventory import iter_inventory_items
    from app32.tests.e2e.catalog.suite_catalog import list_suite_catalog
    from app32.tests.e2e.core.e2e_supervised_execution_service import E2ESupervisedExecutionService
    from app32.tests.e2e.core.execution_history import compare_manifests, latest_manifests, load_manifest
    from app32.tests.e2e.core.failure_governance import build_backlog_candidates
except ModuleNotFoundError:  # pragma: no cover - compatibilidade de import local
    from tests.e2e.catalog.inventory import iter_inventory_items
    from tests.e2e.catalog.suite_catalog import list_suite_catalog
    from tests.e2e.core.e2e_supervised_execution_service import E2ESupervisedExecutionService
    from tests.e2e.core.execution_history import compare_manifests, latest_manifests, load_manifest
    from tests.e2e.core.failure_governance import build_backlog_candidates


class E2EOperationsCenterService:
    """Monta a visão operacional da Central de Testes E2E sem acoplar execução à UI."""

    SYSTEM_ACTION_SUITES = {"inventory_system_scan", "full_system_validation"}
    OPERATIONAL_ENVIRONMENTS = {"DEV_FULL", "PROD_SAFE"}

    FAILURE_SUGGESTIONS = {
        "timeout": "Revisar carregamento assíncrono, tempos de espera e seletor de prontidão do fluxo afetado.",
        "assertion": "Revisar a regra funcional esperada e alinhar contrato da tela/API com a automação.",
        "http": "Validar status HTTP, payload, autenticação e escopo por company_id no endpoint afetado.",
        "runtime": "Inspecionar a exceção em service/backend e estabilizar o fluxo antes de reexecutar.",
        "unknown": "Inspecionar evidências técnicas, reproduzir o caso e fechar o contrato funcional do cenário.",
    }
    STATUS_LABELS = {
        "passed": "Passou",
        "failed": "Falhou",
        "observed": "Em análise",
    }
    MODULE_LABELS = {
        "auth": "Login e acesso",
        "workspace": "Meu Trabalho",
        "meetings": "Reuniões",
        "integrations": "Integrações",
        "work_journey": "Calendário e rotina",
        "processes": "Processos",
        "financial": "Financeiro",
        "contracts": "Contratos e fiscal",
        "reports": "Relatórios",
        "admin": "Administração",
    }
    COVERAGE_TYPE_LABELS = {
        "screen": "Telas e páginas",
        "route": "Caminhos do sistema",
        "action": "Botões e ações",
        "report": "Relatórios",
        "integration": "Integrações e automações",
    }

    @classmethod
    def build_frontend_state(cls, active_company: Any | None = None) -> dict[str, Any]:
        repo_root = cls.get_repo_root()
        outputs_root = cls.get_outputs_root()
        runbooks_root = cls.get_runbooks_root()

        inventory_items = iter_inventory_items()
        runs = cls._collect_runs(outputs_root)
        latest_by_mode = cls._build_latest_by_mode(runs)
        latest_diff = cls._build_latest_diff(outputs_root)
        backlog_candidates = cls._collect_backlog_candidates(runs)
        suite_catalog = [item.to_dict() for item in list_suite_catalog()]
        quick_actions = cls._build_system_actions(suite_catalog)
        partial_suites = [item for item in suite_catalog if item["suite_id"] not in cls.SYSTEM_ACTION_SUITES]
        supervised_executions = E2ESupervisedExecutionService.list_executions()[:12]
        ui_inventory = cls._latest_ui_inventory_summary(outputs_root)
        ui_contracts = cls._latest_ui_contracts_summary(outputs_root)
        ui_safe_execution = cls._latest_ui_safe_execution_summary(outputs_root)
        devfull_transactional = cls._latest_devfull_transactional_summary(outputs_root)
        operational_view = cls._build_operational_view(
            inventory_items,
            runs,
            backlog_candidates,
            ui_inventory=ui_inventory,
            ui_contracts=ui_contracts,
            ui_safe_execution=ui_safe_execution,
            devfull_transactional=devfull_transactional,
        )

        return {
            "summary": {
                "total_runs": len(runs),
                "environments": sorted({str(run.get("environment") or "unknown") for run in runs}),
                "failed_runs": sum(1 for run in runs if run.get("status") == "failed"),
                "company_id": getattr(active_company, "id", None),
                "backlog_candidates": len(backlog_candidates),
            },
            "active_company": {
                "id": getattr(active_company, "id", None),
                "name": getattr(active_company, "name", None),
                "client_code": getattr(active_company, "client_code", None),
            },
            "execution_modes": [
                {
                    "key": "DEV_FULL",
                    "label": "DEV_FULL",
                    "description": "Execução destrutiva controlada com CRUD, processamentos, volume e concorrência.",
                    "destructive": True,
                },
                {
                    "key": "PROD_SAFE",
                    "label": "PROD_SAFE",
                    "description": "Execução segura com smoke, navegação, relatórios e validações não destrutivas.",
                    "destructive": False,
                },
            ],
            "filters": {
                "environments": ["ALL", *sorted({str(run.get("environment") or "unknown") for run in runs})],
                "statuses": ["ALL", "passed", "failed", "observed"],
                "suites": ["ALL", *sorted(item["suite_id"] for item in suite_catalog)],
            },
            "system_actions": quick_actions,
            "operational_view": operational_view,
            "ui_inventory": ui_inventory,
            "ui_contracts": ui_contracts,
            "ui_safe_execution": ui_safe_execution,
            "devfull_transactional": devfull_transactional,
            "latest_runs": runs[:20],
            "latest_by_mode": latest_by_mode,
            "latest_diff": latest_diff,
            "backlog_candidates": backlog_candidates[:20],
            "suite_catalog": suite_catalog,
            "partial_suite_catalog": partial_suites,
            "supervised_executions": supervised_executions,
            "runbooks": cls._build_runbooks(runbooks_root),
            "commands": cls._build_commands(repo_root),
        }

    @classmethod
    def get_repo_root(cls) -> Path:
        return Path(__file__).resolve().parents[2]

    @classmethod
    def get_outputs_root(cls) -> Path:
        return cls.get_repo_root() / "app32" / "tests" / "e2e" / "outputs"

    @classmethod
    def get_runbooks_root(cls) -> Path:
        return cls.get_repo_root() / "app32" / "docs" / "runbooks"

    @classmethod
    def get_run_detail(cls, run_id: str) -> dict[str, Any]:
        outputs_root = cls.get_outputs_root()
        for manifest_path in outputs_root.glob("**/reports/manifest.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(manifest.get("run_id") or manifest_path.parents[1].name) == str(run_id):
                return cls._build_run_record(outputs_root, manifest_path, manifest)
        raise FileNotFoundError(run_id)

    @classmethod
    def resolve_run_file(cls, run_id: str, kind: str, artifact_index: int | None = None) -> Path:
        detail = cls.get_run_detail(run_id)
        if kind == "manifest":
            return Path(detail["manifest_path"]).resolve()
        if kind == "backlog_candidates":
            return Path(detail["backlog_candidates_path"]).resolve()
        if kind == "artifact":
            artifacts = detail.get("artifacts") or []
            if artifact_index is None or artifact_index < 0 or artifact_index >= len(artifacts):
                raise FileNotFoundError(f"artifact:{artifact_index}")
            return Path(artifacts[artifact_index]["path"]).resolve()
        raise FileNotFoundError(kind)

    @classmethod
    def sync_backlog_candidates(cls, run_id: str, *, user_id: int | None, company_id: int | None, create_task_fn) -> dict[str, Any]:
        detail = cls.get_run_detail(run_id)
        created: list[dict[str, Any]] = []
        errors: list[str] = []
        for candidate in detail.get("backlog_candidates") or []:
            task, error = create_task_fn(
                source_type="e2e_failure",
                title=candidate["title"],
                description=cls._build_backlog_description(detail=detail, candidate=candidate),
                user_id=user_id,
                company_id=company_id or candidate.get("company_id"),
                metadata={
                    "run_id": detail.get("run_id"),
                    "environment": detail.get("environment"),
                    "failed_step": candidate.get("failed_step"),
                    "failure_type": candidate.get("failure_type"),
                },
                priority="high",
            )
            if error:
                errors.append(str(error))
                continue
            created.append(
                {
                    "title": candidate["title"],
                    "task_id": getattr(task, "id", None),
                    "task_code": getattr(task, "task_code", None),
                }
            )
        return {"created": created, "errors": errors, "requested": len(detail.get("backlog_candidates") or [])}

    @staticmethod
    def _build_backlog_description(*, detail: dict[str, Any], candidate: dict[str, Any]) -> str:
        return (
            f"Falha detectada pela suíte E2E.\n"
            f"Run: {detail.get('run_id')}\n"
            f"Ambiente: {detail.get('environment')}\n"
            f"Jornada: {candidate.get('journey')}\n"
            f"Passo: {candidate.get('failed_step')}\n"
            f"Tipo: {candidate.get('failure_type')}\n"
            f"Manifesto: {detail.get('manifest_path')}"
        )


    @classmethod
    def _collect_runs(cls, outputs_root: Path) -> list[dict[str, Any]]:
        if not outputs_root.exists():
            return []
        manifests = sorted(outputs_root.glob("**/reports/manifest.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        runs: list[dict[str, Any]] = []
        for manifest_path in manifests:
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            manifest_environment = str(manifest.get("environment") or "").upper()
            environment = (
                manifest_environment
                if manifest_environment in cls.OPERATIONAL_ENVIRONMENTS
                else cls._infer_environment(outputs_root, manifest_path)
            )
            if environment not in cls.OPERATIONAL_ENVIRONMENTS:
                continue
            runs.append(cls._build_run_record(outputs_root, manifest_path, manifest, environment=environment))
        return runs

    @classmethod
    def _build_run_record(cls, outputs_root: Path, manifest_path: Path, manifest: dict[str, Any], *, environment: str | None = None) -> dict[str, Any]:
        root_dir = manifest_path.parents[1]
        environment = environment or cls._infer_environment(outputs_root, manifest_path)
        journeys = manifest.get("journeys") or []
        failed_journeys = [item for item in journeys if item.get("status") == "failed"]
        status = "failed" if failed_journeys else ("passed" if journeys else "observed")
        artifacts = cls._serialize_artifacts(manifest.get("artifacts") or [])
        backlog_candidates = build_backlog_candidates(manifest)
        backlog_path = cls._materialize_backlog_candidates(manifest_path, backlog_candidates)
        return {
            "run_id": manifest.get("run_id") or root_dir.name,
            "environment": environment,
            "generated_at": manifest.get("generated_at"),
            "status": status,
            "journeys_total": len(journeys),
            "journeys_failed": len(failed_journeys),
            "journey_names": [item.get("journey") for item in journeys if item.get("journey")],
            "failed_journey_names": [item.get("journey") for item in failed_journeys if item.get("journey")],
            "artifacts_total": len(artifacts),
            "events_total": len(manifest.get("events") or []),
            "manifest_path": str(manifest_path),
            "root_dir": str(root_dir),
            "manifest_download_url": f"/api/configs/qa/e2e/runs/{manifest.get('run_id') or root_dir.name}/manifest",
            "backlog_candidates_url": f"/api/configs/qa/e2e/runs/{manifest.get('run_id') or root_dir.name}/backlog-candidates",
            "backlog_sync_url": f"/api/configs/qa/e2e/runs/{manifest.get('run_id') or root_dir.name}/backlog-sync",
            "backlog_candidates": backlog_candidates,
            "backlog_candidates_path": str(backlog_path),
            "artifacts": artifacts,
        }

    @staticmethod
    def _serialize_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for index, artifact in enumerate(artifacts):
            item = dict(artifact)
            item["artifact_index"] = index
            serialized.append(item)
        return serialized

    @classmethod
    def _materialize_backlog_candidates(cls, manifest_path: Path, backlog_candidates: list[dict[str, Any]]) -> Path:
        target = manifest_path.parent / "backlog_candidates.json"
        target.write_text(json.dumps(backlog_candidates, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    @staticmethod
    def _infer_environment(outputs_root: Path, manifest_path: Path) -> str:
        try:
            relative = manifest_path.relative_to(outputs_root)
        except ValueError:
            return "unknown"
        parts = relative.parts
        if not parts:
            return "unknown"
        first = str(parts[0]).lower()
        if first == "full_system" and len(parts) > 1:
            nested_environment = str(parts[1]).lower()
            if nested_environment in {"dev_full", "prod_safe"}:
                return nested_environment.upper()
        mapping = {
            "dev_full": "DEV_FULL",
            "prod_safe": "PROD_SAFE",
            "probe": "PROBE",
            "operational_reports": "REPORTS",
            "visual_audit": "VISUAL_AUDIT",
        }
        return mapping.get(first, first.upper())

    @staticmethod
    def _build_latest_by_mode(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for run in runs:
            environment = str(run.get("environment") or "unknown")
            latest.setdefault(environment, run)
        return list(latest.values())

    @classmethod
    def _build_latest_diff(cls, outputs_root: Path) -> dict[str, Any]:
        manifests = latest_manifests(outputs_root, limit=2)
        if len(manifests) < 2:
            return {"status": "insufficient_history", "regressions": [], "recovered": [], "new_journeys": []}
        current = load_manifest(manifests[0])
        previous = load_manifest(manifests[1])
        return compare_manifests(previous, current)

    @classmethod
    def _build_operational_view(
        cls,
        inventory_items: list[dict[str, Any]],
        runs: list[dict[str, Any]],
        backlog_candidates: list[dict[str, Any]],
        *,
        ui_inventory: dict[str, Any] | None = None,
        ui_contracts: dict[str, Any] | None = None,
        ui_safe_execution: dict[str, Any] | None = None,
        devfull_transactional: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        latest_run = runs[0] if runs else None
        approved_runs = sum(1 for run in runs if run.get("status") == "passed")
        failed_runs = sum(1 for run in runs if run.get("status") == "failed")
        observed_runs = sum(1 for run in runs if run.get("status") == "observed")

        coverage_cards = [
            {"label": "Itens mapeados", "value": len(inventory_items), "hint": "Partes do sistema que o robô já reconhece."},
            {"label": "Telas cobertas", "value": sum(1 for item in inventory_items if cls._is_screen_like(item)), "hint": "Páginas e áreas que o robô já consegue abrir."},
            {"label": "Caminhos acompanhados", "value": len({item.get('route') for item in inventory_items if item.get('route')}), "hint": "Fluxos internos do sistema já acompanhados."},
            {"label": "Ações verificadas", "value": sum(len(item.get('actions') or []) for item in inventory_items), "hint": "Salvar, alterar, excluir, emitir e outras ações importantes."},
            {"label": "Relatórios incluídos", "value": sum(1 for item in inventory_items if 'emitir_relatorio' in (item.get('actions') or [])), "hint": "Relatórios e exportações já dentro do robô."},
            {"label": "Integrações acompanhadas", "value": sum(1 for item in inventory_items if item.get('module') in {'integrations', 'work_journey'}), "hint": "Integrações, rotinas e automações já monitoradas."},
        ]
        if ui_inventory:
            coverage_cards.extend(
                [
                    {
                        "label": "Elementos UI detectados",
                        "value": int(ui_inventory.get("elements_total") or 0),
                        "hint": "Campos, botões, links e formulários encontrados automaticamente nos templates.",
                    },
                    {
                        "label": "Campos detectados",
                        "value": int(ui_inventory.get("fields_total") or 0),
                        "hint": "Inputs, selects, textareas e toggles candidatos a preenchimento human-like.",
                    },
                    {
                        "label": "Botões/ações detectados",
                        "value": int(ui_inventory.get("buttons_total") or 0),
                        "hint": "Botões e submits candidatos a clique, processamento, confirmação e rollback.",
                    },
                    {
                        "label": "Lacunas UI",
                        "value": int(ui_inventory.get("missing_contract_elements_total") or 0),
                        "hint": "Elementos descobertos que ainda precisam de contrato executável.",
                    },
                ]
            )
        if ui_contracts:
            coverage_cards.extend(
                [
                    {
                        "label": "Contratos UI gerados",
                        "value": int(ui_contracts.get("contracts_total") or 0),
                        "hint": "Elementos com contrato canônico de execução human-like gerado.",
                    },
                    {
                        "label": "Contratos com rollback",
                        "value": int(ui_contracts.get("rollback_required_total") or 0),
                        "hint": "Ações que exigem reversão/limpeza e auditoria de resíduo zero.",
                    },
                    {
                        "label": "Contratos com gate humano",
                        "value": int(ui_contracts.get("human_gate_required_total") or 0),
                        "hint": "Ações de maior risco que só podem ser exercitadas com confirmação explícita.",
                    },
                ]
            )
        if ui_safe_execution:
            coverage_cards.extend(
                [
                    {
                        "label": "Contratos UI executados",
                        "value": int(ui_safe_execution.get("executed_contracts_total") or 0),
                        "hint": "Contratos de baixo risco executados em modo não persistente.",
                    },
                    {
                        "label": "Contratos UI aprovados",
                        "value": int(ui_safe_execution.get("passed_contracts_total") or 0),
                        "hint": "Contratos seguros que renderizaram e localizaram o elemento esperado.",
                    },
                    {
                        "label": "Rotas UI abertas",
                        "value": int(ui_safe_execution.get("routes_opened_total") or 0),
                        "hint": "Telas abertas de forma autenticada durante a execução segura.",
                    },
                ]
            )
        if devfull_transactional:
            controlled = devfull_transactional.get("controlled_mutation") or {}
            coverage_cards.extend(
                [
                    {
                        "label": "Suítes com mutação controlada",
                        "value": int(devfull_transactional.get("passed_suites") or 0),
                        "hint": "Cadastros/processamentos executados em DEV_FULL com empresa explícita.",
                    },
                    {
                        "label": "Ações criar/editar/processar/cancelar/excluir",
                        "value": int(controlled.get("mutating_steps_total") or 0),
                        "hint": "Passos mutáveis aprovados pelo harness destrutivo controlado.",
                    },
                    {
                        "label": "Rollback/limpezas executados",
                        "value": int(controlled.get("rollback_steps_total") or 0),
                        "hint": "Passos de reversão, exclusão ou restauração executados ao final.",
                    },
                    {
                        "label": "Resíduos encontrados",
                        "value": int(devfull_transactional.get("residue_total") or 0),
                        "hint": "Deve permanecer zero após a limpeza por company_id.",
                    },
                ]
            )

        module_summary: list[dict[str, Any]] = []
        for module_name in sorted({item.get('module') for item in inventory_items if item.get('module')}):
            module_items = [item for item in inventory_items if item.get('module') == module_name]
            module_summary.append(
                {
                    "module": module_name,
                    "module_label": cls.MODULE_LABELS.get(module_name, str(module_name).replace("_", " ").title()),
                    "elements": len(module_items),
                    "actions": sum(len(item.get('actions') or []) for item in module_items),
                    "reports": sum(1 for item in module_items if 'emitir_relatorio' in (item.get('actions') or [])),
                    "criticality": module_items[0].get('criticality'),
                }
            )

        all_actions = [action for item in inventory_items for action in (item.get('actions') or [])]
        coverage_matrix = [
            {
                "item": cls.COVERAGE_TYPE_LABELS["screen"],
                "system_total": sum(1 for item in inventory_items if cls._is_screen_like(item)),
                "covered_total": sum(1 for item in inventory_items if cls._is_screen_like(item) and cls._has_coverage(item)),
                "system_description": "Telas e áreas que existem hoje no sistema.",
                "coverage_description": "Telas que o robô já abre e valida.",
            },
            {
                "item": cls.COVERAGE_TYPE_LABELS["route"],
                "system_total": len({item.get('route') for item in inventory_items if item.get('route')}),
                "covered_total": len({item.get('route') for item in inventory_items if item.get('route') and cls._has_coverage(item)}),
                "system_description": "Caminhos e páginas internas disponíveis.",
                "coverage_description": "Caminhos que já entram nas jornadas automatizadas.",
            },
            {
                "item": cls.COVERAGE_TYPE_LABELS["action"],
                "system_total": len(all_actions),
                "covered_total": len(all_actions),
                "system_description": "Botões, comandos e ações relevantes catalogadas.",
                "coverage_description": "Ações que o robô já consegue executar e conferir.",
            },
            {
                "item": cls.COVERAGE_TYPE_LABELS["report"],
                "system_total": sum(1 for item in inventory_items if 'emitir_relatorio' in (item.get('actions') or [])),
                "covered_total": sum(1 for item in inventory_items if 'emitir_relatorio' in (item.get('actions') or []) and cls._has_coverage(item)),
                "system_description": "Relatórios e exportações existentes no catálogo.",
                "coverage_description": "Relatórios que já entram no robô com evidência.",
            },
            {
                "item": cls.COVERAGE_TYPE_LABELS["integration"],
                "system_total": sum(1 for item in inventory_items if item.get('module') in {'integrations', 'work_journey'}),
                "covered_total": sum(1 for item in inventory_items if item.get('module') in {'integrations', 'work_journey'} and cls._has_coverage(item)),
                "system_description": "Integrações, rotinas e automações catalogadas.",
                "coverage_description": "Integrações e automações já exercitadas pelo robô.",
            },
        ]

        unique_journeys = []
        for run in runs:
            for journey_name in run.get('journey_names') or []:
                if journey_name and journey_name not in unique_journeys:
                    unique_journeys.append(journey_name)

        execution_matrix = [
            {
                "item": "Rodadas executadas",
                "system_description": "Últimas execuções registradas pelo robô.",
                "coverage_description": f"{len(runs)} rodadas analisadas, sendo {approved_runs} sem falhas e {failed_runs} com falhas.",
            },
            {
                "item": "Ambientes usados",
                "system_description": "Onde o robô rodou nos testes recentes.",
                "coverage_description": ", ".join(sorted({str(run.get('environment') or 'N/D') for run in runs})) if runs else "Nenhum ambiente executado ainda.",
            },
            {
                "item": "Fluxos testados",
                "system_description": "Principais jornadas que entraram nas últimas rodadas.",
                "coverage_description": ", ".join(unique_journeys[:8]) if unique_journeys else "Nenhum fluxo executado ainda.",
            },
            {
                "item": "Última rodada",
                "system_description": "Execução mais recente registrada pelo robô.",
                "coverage_description": (
                    f"{latest_run.get('run_id')} em {latest_run.get('environment')} com status {cls.STATUS_LABELS.get(latest_run.get('status'), latest_run.get('status'))}."
                    if latest_run
                    else "Ainda não houve execução registrada."
                ),
            },
        ]

        tested_scope = []
        for run in runs[:6]:
            tested_scope.append(
                {
                    "run_id": run.get('run_id'),
                    "environment": run.get('environment'),
                    "status": run.get('status'),
                    "status_label": cls.STATUS_LABELS.get(run.get('status'), run.get('status')),
                    "tested": run.get('journey_names') or ['Fluxo observado'],
                    "approved": max((run.get('journeys_total') or 0) - (run.get('journeys_failed') or 0), 0),
                    "reproved": run.get('journeys_failed') or 0,
                }
            )

        failed_elements = []
        for candidate in backlog_candidates[:12]:
            failure_type = str(candidate.get('failure_type') or 'unknown')
            failed_elements.append(
                {
                    "element": candidate.get('title'),
                    "issue": cls._humanize_failure(failure_type, candidate.get('failed_step')),
                    "suggestion": cls.FAILURE_SUGGESTIONS.get(failure_type, cls.FAILURE_SUGGESTIONS['unknown']),
                    "impact": cls._suggest_impact(candidate),
                    "severity": cls._suggest_severity(candidate),
                    "severity_label": "Alta prioridade" if cls._suggest_severity(candidate) == "alta" else "Prioridade média",
                    "environment": candidate.get('environment'),
                    "manifest_download_url": candidate.get('manifest_download_url'),
                    "backlog_sync_url": candidate.get('backlog_sync_url'),
                }
            )

        issues_matrix = [
            {
                "item": issue["element"],
                "system_description": issue["issue"],
                "coverage_description": issue["suggestion"],
                "impact": issue["impact"],
                "severity": issue["severity"],
                "severity_label": issue["severity_label"],
                "environment": issue["environment"],
                "manifest_download_url": issue["manifest_download_url"],
                "backlog_sync_url": issue["backlog_sync_url"],
            }
            for issue in failed_elements
        ]

        return {
            "tab_labels": {"operational": "Visão Operacional", "technical": "Visão Técnica"},
            "coverage": {"cards": coverage_cards, "modules": module_summary, "matrix": coverage_matrix},
            "execution": {
                "matrix": execution_matrix,
                "cards": [
                    {"label": "Rodadas analisadas", "value": len(runs), "hint": "Histórico recente do robô."},
                    {"label": "Passaram", "value": approved_runs, "hint": "Rodadas sem falhas percebidas."},
                    {"label": "Falharam", "value": failed_runs, "hint": "Rodadas com problema encontrado."},
                    {"label": "Em análise", "value": observed_runs, "hint": "Rodadas técnicas ou parciais."},
                    {"label": "Última rodada", "value": latest_run.get('run_id') if latest_run else 'Sem execução', "hint": latest_run.get('environment') if latest_run else 'Aguardando primeiro teste'},
                ],
                "latest_scope": tested_scope,
            },
            "issues": {
                "matrix": issues_matrix,
                "items": failed_elements,
                "empty_message": "Nenhum problema reprovado no histórico recente.",
            },
        }

    @staticmethod
    def _latest_ui_inventory_summary(outputs_root: Path) -> dict[str, Any] | None:
        candidates = sorted(
            outputs_root.glob("ui_inventory_scan/run_*/reports/summary.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return None
        try:
            return json.loads(candidates[0].read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _latest_ui_contracts_summary(outputs_root: Path) -> dict[str, Any] | None:
        candidates = sorted(
            outputs_root.glob("ui_contracts/run_*/reports/summary.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return None
        try:
            return json.loads(candidates[0].read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _latest_ui_safe_execution_summary(outputs_root: Path) -> dict[str, Any] | None:
        candidates = sorted(
            outputs_root.glob("ui_safe_execution/run_*/reports/summary.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return None
        try:
            return json.loads(candidates[0].read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _latest_devfull_transactional_summary(outputs_root: Path) -> dict[str, Any] | None:
        candidates = sorted(
            outputs_root.glob("devfull_transactional/run_*/reports/summary.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return None
        try:
            payload = json.loads(candidates[0].read_text(encoding="utf-8"))
        except Exception:
            return None
        controlled = payload.get("controlled_mutation") or {}
        return {
            "run_id": payload.get("run_id"),
            "environment": payload.get("environment"),
            "generated_at": payload.get("generated_at"),
            "company_id": payload.get("company_id"),
            "total_suites": payload.get("total_suites"),
            "passed_suites": payload.get("passed_suites"),
            "failed_suites": payload.get("failed_suites"),
            "failed_suite_ids": payload.get("failed_suite_ids") or [],
            "residue_total": payload.get("residue_total"),
            "controlled_mutation": {
                "company_id": controlled.get("company_id"),
                "destructive_actions_allowed": controlled.get("destructive_actions_allowed"),
                "requires_explicit_company": controlled.get("requires_explicit_company"),
                "cleanup_policy": controlled.get("cleanup_policy"),
                "residue_zero": controlled.get("residue_zero"),
                "mutation_step_counts": controlled.get("mutation_step_counts") or {},
                "mutation_steps_by_domain": controlled.get("mutation_steps_by_domain") or {},
                "mutating_steps_total": controlled.get("mutating_steps_total"),
                "rollback_steps_total": controlled.get("rollback_steps_total"),
                "passed_steps_total": controlled.get("passed_steps_total"),
                "failed_steps_total": controlled.get("failed_steps_total"),
            },
            "summary_path": str(candidates[0]),
        }

    @staticmethod
    def _is_screen_like(item: dict[str, Any]) -> bool:
        route = str(item.get('route') or '')
        actions = set(item.get('actions') or [])
        return not route.startswith('/api/') or bool(actions.intersection({'abrir', 'validar_render', 'redirecionar'}))

    @staticmethod
    def _has_coverage(item: dict[str, Any]) -> bool:
        return bool(item.get('route') or item.get('actions') or item.get('automation_status') or item.get('test_id'))

    @staticmethod
    def _humanize_failure(failure_type: str, failed_step: str | None) -> str:
        base = {
            'timeout': 'O fluxo travou ou demorou além do esperado.',
            'assertion': 'O resultado apresentado foi diferente do esperado.',
            'http': 'A comunicação com a API retornou erro.',
            'runtime': 'A execução encontrou uma exceção durante o fluxo.',
            'unknown': 'Foi detectada uma falha sem classificação específica.',
        }.get(failure_type, 'Foi detectada uma falha no fluxo automatizado.')
        if failed_step:
            return f"{base} Etapa afetada: {failed_step}."
        return base

    @staticmethod
    def _suggest_impact(candidate: dict[str, Any]) -> str:
        title = str(candidate.get('title') or '').lower()
        if 'smoke' in title:
            return 'Pode impedir entrada, acesso básico ou navegação principal do sistema.'
        if 'crud' in title:
            return 'Pode impedir cadastro, alteração ou exclusão de dados pelo usuário.'
        return 'Pode afetar a execução normal do fluxo testado pelo usuário.'

    @staticmethod
    def _suggest_severity(candidate: dict[str, Any]) -> str:
        title = str(candidate.get('title') or '').lower()
        if 'smoke' in title:
            return 'alta'
        if candidate.get('environment') == 'PROD_SAFE':
            return 'alta'
        return 'média'

    @staticmethod
    def _collect_backlog_candidates(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for run in runs:
            for candidate in run.get("backlog_candidates") or []:
                enriched = dict(candidate)
                enriched["environment"] = run.get("environment")
                enriched["manifest_download_url"] = run.get("manifest_download_url")
                enriched["backlog_sync_url"] = run.get("backlog_sync_url")
                items.append(enriched)
        return items

    @staticmethod
    def _build_runbooks(runbooks_root: Path) -> list[dict[str, str]]:
        candidates = [
            ("Sprint 1", runbooks_root / "robot_e2e_aa_j18_sprint1_runbook.md"),
            ("Sprint 2", runbooks_root / "robot_e2e_aa_j18_sprint2_runbook.md"),
            ("Sprint 3", runbooks_root / "robot_e2e_aa_j18_sprint3_runbook.md"),
            ("Sprint 4", runbooks_root / "robot_e2e_aa_j18_sprint4_runbook.md"),
            ("Sprint 5", runbooks_root / "robot_e2e_aa_j18_sprint5_runbook.md"),
            ("Sprint 6", runbooks_root / "robot_e2e_aa_j18_sprint6_runbook.md"),
        ]
        items: list[dict[str, str]] = []
        for label, path in candidates:
            if path.exists():
                items.append({"label": label, "path": str(path)})
        return items

    @staticmethod
    def _build_commands(repo_root: Path) -> list[dict[str, str]]:
        return [
            {
                "label": "Smoke real",
                "command": "$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest app32/tests/e2e/journeys/smoke/test_real_navigation_smoke.py -q",
            },
            {
                "label": "CRUD meetings DEV_FULL",
                "command": "python app32/tests/e2e/scripts/run_meetings_devfull_crud.py",
            },
            {
                "label": "Probe multiusuário",
                "command": "python app32/tests/e2e/scripts/run_user_concurrency_probe.py",
            },
            {
                "label": "Probe MCP concorrente",
                "command": "python app32/tests/e2e/scripts/run_mcp_concurrency_probe.py",
            },
            {
                "label": "Relatórios operacionais",
                "command": "python app32/tests/e2e/scripts/build_operational_load_reports.py",
            },
            {
                "label": "Probe financeiro",
                "command": "python app32/tests/e2e/scripts/run_financial_functional_probe.py",
            },
            {
                "label": "Probe contratos/fiscal",
                "command": "python app32/tests/e2e/scripts/run_contracts_functional_probe.py",
            },
            {
                "label": "Runner agendado oficial",
                "command": "python app32/tests/e2e/scripts/run_scheduled_suite.py --suite-id smoke_real_navigation --environment DEV_FULL",
            },
            {
                "label": "Auditoria visual da Central",
                "command": "python app32/tests/e2e/scripts/render_e2e_center_visual_audit.py",
            },
        ]

    @classmethod
    def _build_system_actions(cls, suite_catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        by_id = {item["suite_id"]: item for item in suite_catalog}
        return {
            "inventory_scan": {
                "suite_id": "inventory_system_scan",
                "label": "Checar e mapear todo o sistema",
                "description": "Vasculha rotas novas, compara com o inventário atual e aponta o que ainda precisa entrar na cobertura.",
                "summary": (by_id.get("inventory_system_scan") or {}).get("summary"),
            },
            "full_validation": {
                "suite_id": "full_system_validation",
                "label": "Fazer teste completo do sistema",
                "description": "Executa a bateria completa de testes suportada no ambiente escolhido e consolida o resultado final.",
                "summary": (by_id.get("full_system_validation") or {}).get("summary"),
            },
            "partial_execution": {
                "label": "Fazer teste parcial",
                "description": "Permite escolher uma suíte específica para validar apenas uma parte do sistema.",
            },
        }
