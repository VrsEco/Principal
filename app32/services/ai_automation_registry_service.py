from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from models.financial import FinancialAutomationExecution, FinancialAutomationRule
from models.process import ProcessRoutine
from services.scheduler_service import get_scheduler


class AIAutomationRegistryService:
    """Registry consultivo das automações recorrentes e event-driven do APP32."""

    DEFAULT_JOB_SPECS: tuple[dict[str, Any], ...] = (
        {
            "key": "process_daily_routines",
            "title": "Processamento de Rotinas Agendadas",
            "kind": "scheduler_core",
            "trigger": "cron:* * * * *",
            "surface": "scheduler",
            "status": "ready",
            "description": "Varre rotinas configuradas e cria/atualiza instâncias operacionais.",
            "governance": ["company_id por rotina", "auditoria operacional", "job idempotente por janela"],
        },
        {
            "key": "check_overdue_tasks",
            "title": "Verificação de Instâncias Atrasadas",
            "kind": "scheduler_core",
            "trigger": "cron:0 * * * *",
            "surface": "scheduler",
            "status": "ready",
            "description": "Atualiza status de instâncias e sinaliza atrasos operacionais.",
            "governance": ["tenant scope", "sem mutação cross-tenant"],
        },
        {
            "key": "proactive_morning_summary",
            "title": "Resumo Matinal Proativo",
            "kind": "proactive",
            "trigger": "cron:0 8 * * *",
            "surface": "sapiens",
            "status": "ready",
            "description": "Dispara resumos proativos para canais configurados.",
            "governance": ["opt-in por canal", "auditoria de envio", "policy por empresa"],
        },
        {
            "key": "knowledge_product_help_sync",
            "title": "Atualização do Manual Interativo",
            "kind": "knowledge_sync",
            "trigger": "interval:15m",
            "surface": "scheduler",
            "status": "ready",
            "description": "Descobre artigos product_help, compara checksum e sincroniza somente mudanças.",
            "governance": [
                "conteúdo global sem company_id",
                "execução idempotente por checksum",
                "falha fechada e ledger auditável",
            ],
        },
        {
            "key": "knowledge_tenant_sources_sync",
            "title": "Atualização do Conhecimento por Empresa",
            "kind": "knowledge_sync",
            "trigger": "interval:15m",
            "surface": "scheduler",
            "status": "ready",
            "description": "Reconcilia publicações de Processo/POP e reuniões concluídas por empresa ativa.",
            "governance": [
                "company_id obrigatório por execução",
                "grants projetados antes da recuperação",
                "execução idempotente por fonte",
                "falha isolada por empresa e adapter",
            ],
        },
        {
            "key": "chat_timeout_monitor",
            "title": "Monitor de Inatividade de Chat",
            "kind": "conversation_guard",
            "trigger": "interval:30s",
            "surface": "sapiens",
            "status": "ready",
            "description": "Encerra e reconcilia sessões inativas com regras operacionais.",
            "governance": ["timeout policy", "trilha de encerramento", "isolamento por canal"],
        },
    )

    @classmethod
    def build_registry(cls, active_company: Any | None = None) -> dict[str, Any]:
        company_id = getattr(active_company, "id", None)
        scheduler = get_scheduler()
        runtime_jobs = {
            str(job.id): job
            for job in (scheduler.scheduler.get_jobs() if getattr(scheduler, "scheduler", None) else [])
        }

        automation_items: list[dict[str, Any]] = []
        kind_counter: Counter[str] = Counter()
        status_counter: Counter[str] = Counter()

        for spec in cls.DEFAULT_JOB_SPECS:
            runtime_job = runtime_jobs.get(spec["key"])
            item = {
                **spec,
                "next_run_at": runtime_job.next_run_time.isoformat() if runtime_job and runtime_job.next_run_time else None,
                "runtime_present": bool(runtime_job),
                "execution_mode": "scheduled",
            }
            automation_items.append(item)
            kind_counter.update([item["kind"]])
            status_counter.update([item["status"]])

        try:
            routine_query = ProcessRoutine.query.filter(ProcessRoutine.is_active.is_(True))
            if company_id is not None:
                routine_query = routine_query.filter(ProcessRoutine.company_id == int(company_id))
            active_routines = routine_query.count()
        except Exception:
            active_routines = 0
        automation_items.append(
            {
                "key": "process_routines_catalog",
                "title": "Catálogo de Rotinas de Processo",
                "kind": "process_routine",
                "trigger": "event + scheduler",
                "surface": "operations",
                "status": "ready" if active_routines else "planned",
                "description": "Base operacional usada pelo scheduler de rotinas e follow-up diário.",
                "count": int(active_routines),
                "execution_mode": "catalog",
                "governance": ["escopo por empresa", "execução sob scheduler corporativo"],
            }
        )
        kind_counter.update(["process_routine"])
        status_counter.update(["ready" if active_routines else "planned"])

        try:
            financial_rule_query = FinancialAutomationRule.query.filter(FinancialAutomationRule.deleted_at.is_(None))
            financial_execution_query = FinancialAutomationExecution.query
            if company_id is not None:
                financial_rule_query = financial_rule_query.filter(FinancialAutomationRule.company_id == int(company_id))
                financial_execution_query = financial_execution_query.filter(FinancialAutomationExecution.company_id == int(company_id))

            total_financial_rules = financial_rule_query.count()
            active_financial_rules = financial_rule_query.filter(FinancialAutomationRule.is_active.is_(True)).count()
            recent_since = datetime.utcnow() - timedelta(days=30)
            recent_financial_executions = (
                financial_execution_query
                .filter(FinancialAutomationExecution.executed_at >= recent_since)
                .count()
            )
        except Exception:
            total_financial_rules = 0
            active_financial_rules = 0
            recent_financial_executions = 0
        automation_items.append(
            {
                "key": "financial_automation_rules",
                "title": "Automações Financeiras",
                "kind": "financial",
                "trigger": "event-driven",
                "surface": "finance",
                "status": "ready" if active_financial_rules else ("planned" if total_financial_rules else "partial"),
                "description": "Regras financeiras acionadas por eventos de processo e geração de schedules/execuções.",
                "count": int(active_financial_rules),
                "total_rules": int(total_financial_rules),
                "recent_executions": int(recent_financial_executions),
                "execution_mode": "event-driven",
                "governance": ["idempotência por idempotency_key", "tenant scope", "máximo de tentativas controlado"],
            }
        )
        kind_counter.update(["financial"])
        status_counter.update(["ready" if active_financial_rules else ("planned" if total_financial_rules else "partial")])

        return {
            "summary": {
                "automations": len(automation_items),
                "scheduled_jobs": sum(1 for item in automation_items if item.get("execution_mode") == "scheduled"),
                "event_driven": sum(1 for item in automation_items if item.get("execution_mode") == "event-driven"),
                "catalog_entries": sum(1 for item in automation_items if item.get("execution_mode") == "catalog"),
                "active_routines": int(active_routines),
                "active_financial_rules": int(active_financial_rules),
                "recent_financial_executions": int(recent_financial_executions),
                "by_kind": dict(kind_counter),
                "by_status": dict(status_counter),
            },
            "automations": automation_items,
        }
