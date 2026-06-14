"""Ferramentas MCP financeiras do APP32.

Mantém o servidor MCP legado magro e concentra a superfície financeira
em um registrador reutilizável. As validações de multi-tenancy de negócio
continuam nos serviços financeiros chamados por cada tool.
"""

from __future__ import annotations

import base64
import os
from typing import Any, Optional


def register_financial_mcp_tools(mcp: Any) -> None:
    """Registra as tools MCP financeiras no servidor informado."""

    def _attach_mcp_audit_payload(payload: dict | None) -> dict:
        from src.intelligence.tool_context import get_sapiens_context

        def _resolve_employee_id(resolved_user_id: int | None, company_id_value: int | None, fallback_employee_id: int | None) -> int | None:
            if fallback_employee_id is not None:
                return int(fallback_employee_id)
            if resolved_user_id is None or company_id_value is None:
                return None
            try:
                from models.employee import Employee

                employee = Employee.query.filter_by(
                    user_id=int(resolved_user_id),
                    company_id=int(company_id_value),
                ).first()
                if employee and getattr(employee, "id", None) is not None:
                    return int(employee.id)
            except Exception:
                return None
            return None

        normalized = dict(payload or {})
        identity = get_sapiens_context()
        user_id = identity.user_id or (int(os.environ["APP32_MCP_USER_ID"]) if os.environ.get("APP32_MCP_USER_ID") else None)
        company_id = normalized.get("company_id") or os.environ.get("APP32_MCP_COMPANY_ID") or identity.company_id
        company_id = int(company_id) if company_id not in (None, "") else None
        employee_id = _resolve_employee_id(user_id, company_id, identity.employee_id)
        channel = (
            str(os.environ.get("APP32_MCP_CLIENT") or os.environ.get("APP32_MCP_CHANNEL") or identity.channel or "app32_mcp")
            .strip()
            .lower()
        )
        thread_id = identity.thread_id or os.environ.get("APP32_MCP_THREAD_ID")
        agent_name = channel or "app32_mcp"

        normalized.setdefault("created_by_agent", agent_name)
        if user_id is not None:
            normalized.setdefault("created_by_user_id", int(user_id))
        if employee_id is not None:
            normalized.setdefault("created_by_employee_id", int(employee_id))

        metadata = dict(normalized.get("metadata_json") or {})
        audit = dict(metadata.get("audit") or {})
        actor = dict(audit.get("actor") or {})
        if user_id is not None:
            actor.setdefault("user_id", int(user_id))
        if employee_id is not None:
            actor.setdefault("employee_id", int(employee_id))
        actor.setdefault("agent", agent_name)
        audit["actor"] = actor
        audit.setdefault("channel", channel)
        if thread_id:
            audit.setdefault("thread_id", thread_id)
        metadata["audit"] = audit
        normalized["metadata_json"] = metadata
        return normalized

    def _run_financial_action(callback, *args, **kwargs) -> Any:
        from app import create_app

        app = create_app()
        with app.app_context():
            return callback(*args, **kwargs)

    @mcp.tool()
    def list_financial_catalog_items(company_id: int, catalog_type: str) -> dict:
        """
        Lista cadastros-base do financeiro (bank_accounts, chart_accounts, cost_centers, counterparties).
        """
        from services.financial_catalog_service import FinancialCatalogService

        result, error = _run_financial_action(
            FinancialCatalogService.list_items,
            company_id=company_id,
            catalog_type=catalog_type,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def create_financial_catalog_item(catalog_type: str, payload: dict) -> dict:
        """
        Cria item de cadastro-base do financeiro.
        """
        from services.financial_catalog_service import FinancialCatalogService

        result, error = _run_financial_action(
            FinancialCatalogService.create_item,
            catalog_type=catalog_type,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def update_financial_catalog_item(company_id: int, catalog_type: str, item_id: int, payload: dict) -> dict:
        """
        Atualiza item de cadastro-base do financeiro.
        """
        from services.financial_catalog_service import FinancialCatalogService

        result, error = _run_financial_action(
            FinancialCatalogService.update_item,
            catalog_type=catalog_type,
            item_id=item_id,
            company_id=company_id,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def toggle_financial_catalog_item(company_id: int, catalog_type: str, item_id: int, is_active: bool) -> dict:
        """
        Ativa ou inativa item de cadastro-base do financeiro.
        """
        from services.financial_catalog_service import FinancialCatalogService

        result, error = _run_financial_action(
            FinancialCatalogService.toggle_item,
            catalog_type=catalog_type,
            item_id=item_id,
            company_id=company_id,
            is_active=is_active,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def list_financial_domain_enablements(company_id: int, domain_type: Optional[str] = None) -> dict:
        """
        Lista projetos/processos habilitados para uso no Financeiro.
        domain_type pode ser 'project' ou 'process'.
        """
        from services.financial_domain_enablement_service import FinancialDomainEnablementService

        result, error = _run_financial_action(
            FinancialDomainEnablementService.list_items,
            company_id=company_id,
            domain_type=domain_type,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **(result or {})}

    @mcp.tool()
    def upsert_financial_domain_enablement(payload: dict) -> dict:
        """
        Cria ou atualiza a habilitação financeira de um projeto/processo.
        Espera company_id, domain_type, source_id e opcionalmente is_enabled/notes.
        """
        from services.financial_domain_enablement_service import FinancialDomainEnablementService

        result, error = _run_financial_action(
            FinancialDomainEnablementService.upsert_item,
            company_id=payload.get("company_id"),
            domain_type=payload.get("domain_type"),
            source_id=payload.get("source_id"),
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def toggle_financial_domain_enablement(company_id: int, domain_type: str, source_id: int, is_enabled: bool) -> dict:
        """
        Habilita ou desabilita um projeto/processo para uso no Financeiro.
        """
        from services.financial_domain_enablement_service import FinancialDomainEnablementService

        result, error = _run_financial_action(
            FinancialDomainEnablementService.toggle_item,
            company_id=company_id,
            domain_type=domain_type,
            source_id=source_id,
            is_enabled=is_enabled,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def list_financial_ingestion_records(
        company_id: int,
        origin_type: Optional[str] = None,
        completion_status: Optional[str] = None,
        review_status: Optional[str] = None,
    ) -> dict:
        """
        Lista registros de ingestão financeira vindos de integrações, importações e Sapiens.
        """
        from services.financial_ingestion_service import FinancialIngestionService

        result, error = _run_financial_action(
            FinancialIngestionService.list_records,
            company_id=company_id,
            origin_type=origin_type,
            completion_status=completion_status,
            review_status=review_status,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def create_financial_ingestion_record(payload: dict) -> dict:
        """
        Cria um registro transversal de ingestão financeira para integração, importação ou Sapiens.
        """
        from services.financial_ingestion_service import FinancialIngestionService

        result, error = _run_financial_action(
            FinancialIngestionService.create_record,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def review_financial_ingestion_record(
        company_id: int,
        record_id: int,
        review_status: str,
        review_notes: Optional[str] = None,
        completion_status: Optional[str] = None,
        reviewed_by_user_id: Optional[int] = None,
    ) -> dict:
        """
        Registra revisão humana de um registro de ingestão financeira.
        """
        from services.financial_ingestion_service import FinancialIngestionService

        result, error = _run_financial_action(
            FinancialIngestionService.review_record,
            company_id=company_id,
            record_id=record_id,
            review_status=review_status,
            review_notes=review_notes,
            completion_status=completion_status,
            reviewed_by_user_id=reviewed_by_user_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def convert_financial_ingestion_record(company_id: int, record_id: int, target_type: str) -> dict:
        """
        Converte um registro de ingestão financeira em agendamento ou lançamento.
        """
        from services.financial_ingestion_service import FinancialIngestionService

        result, error = _run_financial_action(
            FinancialIngestionService.convert_record,
            company_id=company_id,
            record_id=record_id,
            target_type=target_type,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def list_financial_schedules(company_id: int, status: Optional[str] = None) -> dict:
        """
        Lista previsões e agendamentos financeiros da empresa.
        """
        from services.financial_schedule_service import FinancialScheduleService

        result, error = _run_financial_action(
            FinancialScheduleService.list_schedules,
            company_id=company_id,
            status=status,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def create_financial_schedule(payload: dict) -> dict:
        """
        Cria previsão/agendamento financeiro recorrente ou pontual.
        """
        from services.financial_schedule_service import FinancialScheduleService

        result, error = _run_financial_action(
            FinancialScheduleService.create_schedule,
            payload=_attach_mcp_audit_payload(payload),
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def update_financial_schedule(company_id: int, schedule_id: int, payload: dict) -> dict:
        """
        Atualiza um agendamento financeiro existente.
        """
        from services.financial_schedule_service import FinancialScheduleService

        result, error = _run_financial_action(
            FinancialScheduleService.update_schedule,
            company_id=company_id,
            schedule_id=schedule_id,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def toggle_financial_schedule(company_id: int, schedule_id: int, status: str) -> dict:
        """
        Altera o status de um agendamento financeiro: draft, active, paused, completed ou cancelled.
        """
        from services.financial_schedule_service import FinancialScheduleService

        result, error = _run_financial_action(
            FinancialScheduleService.toggle_schedule,
            company_id=company_id,
            schedule_id=schedule_id,
            status=status,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def generate_due_financial_schedules(company_id: int, run_until: Optional[str] = None, schedule_id: Optional[int] = None) -> dict:
        """
        Gera lançamentos do ledger a partir de agendamentos ativos e vencidos até a data informada.
        """
        from datetime import datetime
        from services.financial_schedule_service import FinancialScheduleService

        run_until_date = None
        if run_until:
            try:
                run_until_date = datetime.strptime(run_until, "%Y-%m-%d").date()
            except ValueError:
                return {"success": False, "error": "run_until inválido. Use YYYY-MM-DD."}

        result, error = _run_financial_action(
            FinancialScheduleService.generate_due_entries,
            company_id=company_id,
            schedule_id=schedule_id,
            run_until=run_until_date,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}


    @mcp.tool()
    def list_financial_borderos(company_id: int, bordero_type: Optional[str] = None, status: Optional[str] = None) -> dict:
        """
        Lista borderôs financeiros da empresa por tipo e status.
        """
        from services.financial_bordero_service import FinancialBorderoService

        result, error = _run_financial_action(
            FinancialBorderoService.list_borderos,
            company_id=company_id,
            bordero_type=bordero_type,
            status=status,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def get_financial_bordero(company_id: int, bordero_id: int) -> dict:
        """
        Retorna o detalhe de um borderô financeiro com itens e baixas.
        """
        from services.financial_bordero_service import FinancialBorderoService

        result, error = _run_financial_action(
            FinancialBorderoService.get_bordero_detail,
            company_id=company_id,
            bordero_id=bordero_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def create_financial_bordero(payload: dict) -> dict:
        """
        Cria um borderô financeiro de pagamento ou recebimento a partir de agendamentos.
        """
        from services.financial_bordero_service import FinancialBorderoService

        result, error = _run_financial_action(
            FinancialBorderoService.create_bordero,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def create_financial_bordero_settlement(bordero_id: int, payload: dict) -> dict:
        """
        Registra uma baixa total ou parcial em um borderô financeiro.
        """
        from services.financial_bordero_service import FinancialBorderoService

        result, error = _run_financial_action(
            FinancialBorderoService.create_settlement,
            bordero_id=bordero_id,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}


    @mcp.tool()
    def get_financial_budget_planning_workspace(company_id: int, version_id: Optional[int] = None) -> dict:
        """
        Retorna o workspace de planejamento do Orçamento Matricial: orçamento + verbas orçamentárias + resumo executivo.
        """
        from services.financial_budget_workspace_service import FinancialBudgetWorkspaceService

        result, error = _run_financial_action(
            FinancialBudgetWorkspaceService.get_planning_workspace,
            company_id=company_id,
            version_id=version_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **(result or {})}

    @mcp.tool()
    def get_financial_budget_execution_workspace(
        company_id: int,
        version_id: Optional[int] = None,
        line_id: Optional[int] = None,
        contract_id: Optional[int] = None,
        document_id: Optional[int] = None,
    ) -> dict:
        """
        Retorna o workspace de execução do Orçamento Matricial: verbas, contratos, NF/equivalentes e agendamentos.
        """
        from services.financial_budget_workspace_service import FinancialBudgetWorkspaceService

        result, error = _run_financial_action(
            FinancialBudgetWorkspaceService.get_execution_workspace,
            company_id=company_id,
            version_id=version_id,
            line_id=line_id,
            contract_id=contract_id,
            document_id=document_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **(result or {})}

    @mcp.tool()
    def create_financial_budget_line(payload: dict) -> dict:
        """
        Cria uma verba orçamentária dentro de um orçamento matricial.
        """
        from services.financial_budget_workspace_service import FinancialBudgetWorkspaceService

        result, error = _run_financial_action(
            FinancialBudgetWorkspaceService.create_line,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def create_financial_budget_contract(payload: dict) -> dict:
        """
        Cria um contrato vinculado a uma verba orçamentária.
        """
        from services.financial_budget_workspace_service import FinancialBudgetWorkspaceService

        result, error = _run_financial_action(
            FinancialBudgetWorkspaceService.create_contract,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def create_financial_budget_document(payload: dict) -> dict:
        """
        Cria uma NF/equivalente vinculada a um contrato do orçamento matricial.
        """
        from services.financial_budget_workspace_service import FinancialBudgetWorkspaceService

        result, error = _run_financial_action(
            FinancialBudgetWorkspaceService.create_document,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def create_financial_budget_document_schedules(company_id: int, document_id: int, payload: dict) -> dict:
        """
        Gera agendamentos financeiros para uma NF/equivalente do orçamento matricial.
        """
        from services.financial_budget_workspace_service import FinancialBudgetWorkspaceService

        result, error = _run_financial_action(
            FinancialBudgetWorkspaceService.create_document_schedules,
            company_id=company_id,
            document_id=document_id,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **(result or {})}

    @mcp.tool()
    def list_financial_automation_rules(company_id: int) -> dict:
        """
        Lista regras de automação financeira por processo/instância.
        """
        from services.financial_automation_service import FinancialAutomationService

        result, error = _run_financial_action(
            FinancialAutomationService.list_rules,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def create_financial_automation_rule(payload: dict) -> dict:
        """
        Cria uma regra que gera agendamentos financeiros a partir de processos/instâncias.
        """
        from services.financial_automation_service import FinancialAutomationService

        result, error = _run_financial_action(
            FinancialAutomationService.create_rule,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def apply_financial_automation_to_instance(company_id: int, process_instance_id: int, trigger_status: Optional[str] = None) -> dict:
        """
        Aplica as regras financeiras compatíveis a uma instância de processo específica.
        """
        from services.financial_automation_service import FinancialAutomationService

        result, error = _run_financial_action(
            FinancialAutomationService.apply_rules_to_instance,
            company_id=company_id,
            process_instance_id=process_instance_id,
            trigger_status=trigger_status,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def list_financial_automation_executions(
        company_id: int,
        rule_id: Optional[int] = None,
        process_instance_id: Optional[int] = None,
    ) -> dict:
        """
        Lista execuções, skips, erros e sucessos da automação financeira para auditoria.
        """
        from services.financial_automation_service import FinancialAutomationService

        result, error = _run_financial_action(
            FinancialAutomationService.list_executions,
            company_id=company_id,
            rule_id=rule_id,
            process_instance_id=process_instance_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def dispatch_financial_process_trigger(
        company_id: int,
        process_instance_id: int,
        trigger_status: Optional[str] = None,
        event_name: str = "manual_dispatch",
    ) -> dict:
        """
        Dispara manualmente o gatilho financeiro para uma instância de processo específica.
        """
        from services.financial_process_trigger_service import FinancialProcessTriggerService

        result, error = _run_financial_action(
            FinancialProcessTriggerService.dispatch_for_instance,
            company_id=company_id,
            process_instance_id=process_instance_id,
            trigger_status=trigger_status,
            event_name=event_name,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def list_financial_entries(
        company_id: int,
        status: Optional[str] = None,
        entry_type: Optional[str] = None,
        origin_type: Optional[str] = None,
        activity_id: Optional[int] = None,
        process_instance_id: Optional[int] = None,
    ) -> dict:
        """
        Lista lançamentos financeiros do ledger unificado por empresa.
        Use filtros opcionais para reduzir o escopo operacional.
        """
        from services.financial_service import FinancialService

        entries, error = _run_financial_action(
            FinancialService.list_entries,
            company_id=company_id,
            status=status,
            entry_type=entry_type,
            origin_type=origin_type,
            activity_id=activity_id,
            process_instance_id=process_instance_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": entries, "count": len(entries)}

    @mcp.tool()
    def get_financial_entry(company_id: int, entry_id: int) -> dict:
        """
        Retorna um lançamento financeiro com seus rateios e liquidações.
        """
        from services.financial_service import FinancialService

        entry, error = _run_financial_action(
            FinancialService.get_entry,
            entry_id=entry_id,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": entry}

    @mcp.tool()
    def create_financial_entry(payload: dict) -> dict:
        """
        Cria um lançamento financeiro no ledger.
        Espera payload compatível com FinancialEntryCreateInput.
        """
        from services.financial_service import FinancialService

        def _create_and_serialize_entry(*, payload: dict):
            entry, error = FinancialService.create_entry(payload=payload)
            if error:
                return None, error
            return FinancialService.serialize_entry(entry), None

        entry, error = _run_financial_action(
            _create_and_serialize_entry,
            payload=_attach_mcp_audit_payload(payload),
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": entry}

    @mcp.tool()
    def create_financial_direct_entry(payload: dict) -> dict:
        """
        Cria um lançamento direto operacional com geração concomitante do agendamento.
        """
        from services.financial_direct_entry_service import FinancialDirectEntryService

        result, error = _run_financial_action(
            FinancialDirectEntryService.create_direct_entry,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def replace_financial_allocations(payload: dict) -> dict:
        """
        Substitui integralmente o rateio de um lançamento financeiro.
        Espera payload compatível com FinancialAllocationBatchInput.
        """
        from services.financial_service import FinancialService

        allocations, error = _run_financial_action(
            FinancialService.replace_allocations,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {
            "success": True,
            "items": [allocation.to_dict() for allocation in allocations],
            "count": len(allocations),
        }

    @mcp.tool()
    def create_financial_settlement(payload: dict) -> dict:
        """
        Cria uma liquidação financeira com juros, multas, descontos e ajustes.
        Espera payload compatível com FinancialSettlementInput.
        """
        from services.financial_service import FinancialService

        settlement, error = _run_financial_action(
            FinancialService.create_settlement,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": settlement.to_dict()}

    @mcp.tool()
    def list_financial_import_batches(company_id: int) -> dict:
        """
        Lista lotes do staging de importação financeira por empresa.
        """
        from services.financial_import_service import FinancialImportService

        batches, error = _run_financial_action(
            FinancialImportService.list_import_batches,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": batches, "count": len(batches)}

    @mcp.tool()
    def get_financial_import_batch(company_id: int, batch_id: int) -> dict:
        """
        Retorna lote e linhas staged de uma importação financeira.
        """
        from services.financial_import_service import FinancialImportService

        result, error = _run_financial_action(
            FinancialImportService.get_import_batch,
            batch_id=batch_id,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def create_financial_import_batch(payload: dict, file_base64: str) -> dict:
        """
        Cria um lote de importação financeira no staging.
        payload deve seguir FinancialImportBatchInput; file_base64 contém o arquivo codificado.
        """
        from services.financial_import_service import FinancialImportService

        try:
            file_bytes = base64.b64decode(file_base64)
        except Exception as exc:
            return {"success": False, "error": f"Arquivo base64 inválido: {str(exc)}"}

        result, error = _run_financial_action(
            FinancialImportService.create_import_batch,
            payload=payload,
            file_bytes=file_bytes,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def process_financial_import_batch(company_id: int, batch_id: int) -> dict:
        """
        Promove as linhas válidas do staging para o ledger financeiro.
        """
        from services.financial_import_service import FinancialImportService

        result, error = _run_financial_action(
            FinancialImportService.process_import_batch,
            batch_id=batch_id,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def reconcile_financial_import_batch(company_id: int, batch_id: int) -> dict:
        """
        Executa matching automático inicial entre staging de importação e ledger financeiro.
        """
        from services.financial_reconciliation_service import FinancialReconciliationService

        result, error = _run_financial_action(
            FinancialReconciliationService.auto_match_batch,
            batch_id=batch_id,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def review_financial_reconciliation_match(
        company_id: int,
        match_id: int,
        decision: str,
        selected_entry_id: Optional[int] = None,
        adjustments: Optional[dict] = None,
    ) -> dict:
        """
        Confirma ou rejeita manualmente uma sugestão de conciliação.
        decision: confirmed | rejected
        """
        from services.financial_reconciliation_service import FinancialReconciliationService

        result, error = _run_financial_action(
            FinancialReconciliationService.review_match,
            match_id=match_id,
            company_id=company_id,
            decision=decision,
            selected_entry_id=selected_entry_id,
            adjustments=adjustments,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def get_financial_bank_reconciliation_overview(company_id: int) -> dict:
        """
        Retorna o painel por conta bancária com situação atual da conciliação e preparação para integração automática.
        """
        from services.financial_reconciliation_workspace_service import FinancialReconciliationWorkspaceService

        result, error = _run_financial_action(
            FinancialReconciliationWorkspaceService.get_overview,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def get_financial_bank_reconciliation_workspace(
        company_id: int,
        bank_account_id: int,
        batch_id: Optional[int] = None,
    ) -> dict:
        """
        Retorna o workspace operacional da conciliação bancária para uma conta e, opcionalmente, um lote específico.
        """
        from services.financial_reconciliation_workspace_service import FinancialReconciliationWorkspaceService

        result, error = _run_financial_action(
            FinancialReconciliationWorkspaceService.get_workspace,
            company_id=company_id,
            bank_account_id=bank_account_id,
            batch_id=batch_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def list_financial_bank_reconciliation_candidates(
        company_id: int,
        row_id: int,
        limit: int = 8,
    ) -> dict:
        """
        Lista candidatos ranqueados do ledger para uma linha do extrato bancário importado.
        """
        from services.financial_reconciliation_workspace_service import FinancialReconciliationWorkspaceService

        result, error = _run_financial_action(
            FinancialReconciliationWorkspaceService.list_row_candidates,
            company_id=company_id,
            row_id=row_id,
            limit=limit,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def match_financial_bank_reconciliation_row(
        company_id: int,
        row_id: int,
        financial_entry_id: int,
        adjustments: Optional[dict] = None,
    ) -> dict:
        """
        Confirma manualmente a conciliação de uma linha do extrato contra um lançamento financeiro, com ajustes opcionais.
        """
        from services.financial_reconciliation_service import FinancialReconciliationService

        result, error = _run_financial_action(
            FinancialReconciliationService.manually_match_row,
            row_id=row_id,
            financial_entry_id=financial_entry_id,
            company_id=company_id,
            adjustments=adjustments,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def create_financial_entry_from_bank_reconciliation_row(
        company_id: int,
        row_id: int,
        payload: dict,
    ) -> dict:
        """
        Cria um novo lançamento financeiro a partir de uma linha do extrato e já o devolve conciliado no workspace.
        """
        from services.financial_reconciliation_workspace_service import FinancialReconciliationWorkspaceService

        result, error = _run_financial_action(
            FinancialReconciliationWorkspaceService.create_entry_from_row,
            company_id=company_id,
            row_id=row_id,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def list_financial_classification_rules(company_id: int) -> dict:
        """
        Lista regras de classificação automática do financeiro por empresa.
        """
        from services.financial_classification_service import FinancialClassificationService

        result, error = _run_financial_action(
            FinancialClassificationService.list_rules,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def create_financial_classification_rule(payload: dict) -> dict:
        """
        Cria regra determinística de classificação para o hub de importação financeira.
        """
        from services.financial_classification_service import FinancialClassificationService

        result, error = _run_financial_action(
            FinancialClassificationService.create_rule,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def update_financial_classification_rule(company_id: int, rule_id: int, payload: dict) -> dict:
        """
        Atualiza uma regra determinística de classificação financeira.
        """
        from services.financial_classification_service import FinancialClassificationService

        result, error = _run_financial_action(
            FinancialClassificationService.update_rule,
            rule_id=rule_id,
            company_id=company_id,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def toggle_financial_classification_rule(company_id: int, rule_id: int, is_active: bool) -> dict:
        """
        Ativa ou inativa uma regra determinística de classificação financeira.
        """
        from services.financial_classification_service import FinancialClassificationService

        result, error = _run_financial_action(
            FinancialClassificationService.toggle_rule,
            rule_id=rule_id,
            company_id=company_id,
            is_active=is_active,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def classify_financial_import_batch(company_id: int, batch_id: int) -> dict:
        """
        Aplica regras automáticas de classificação às linhas de um lote de importação financeira.
        """
        from services.financial_classification_service import FinancialClassificationService

        result, error = _run_financial_action(
            FinancialClassificationService.classify_batch,
            batch_id=batch_id,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def list_financial_classification_memories(company_id: int) -> dict:
        """
        Lista memórias históricas de classificação por cliente.
        """
        from services.financial_classification_hybrid_service import FinancialClassificationHybridService

        result, error = _run_financial_action(
            FinancialClassificationHybridService.list_memories,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def update_financial_classification_memory(company_id: int, memory_id: int, payload: dict) -> dict:
        """
        Atualiza uma memória histórica de classificação financeira.
        """
        from services.financial_classification_hybrid_service import FinancialClassificationHybridService

        result, error = _run_financial_action(
            FinancialClassificationHybridService.update_memory,
            memory_id=memory_id,
            company_id=company_id,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def toggle_financial_classification_memory(company_id: int, memory_id: int, is_active: bool) -> dict:
        """
        Ativa ou inativa uma memória histórica de classificação financeira.
        """
        from services.financial_classification_hybrid_service import FinancialClassificationHybridService

        result, error = _run_financial_action(
            FinancialClassificationHybridService.toggle_memory,
            memory_id=memory_id,
            company_id=company_id,
            is_active=is_active,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def suggest_financial_classification_for_batch(company_id: int, batch_id: int) -> dict:
        """
        Gera sugestões ranqueadas a partir da memória histórica do cliente para um lote.
        """
        from services.financial_classification_hybrid_service import FinancialClassificationHybridService

        result, error = _run_financial_action(
            FinancialClassificationHybridService.suggest_from_memory,
            batch_id=batch_id,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def list_financial_classification_suggestions(company_id: int, batch_id: Optional[int] = None) -> dict:
        """
        Lista sugestões persistidas de classificação financeira.
        """
        from services.financial_classification_hybrid_service import FinancialClassificationHybridService

        result, error = _run_financial_action(
            FinancialClassificationHybridService.list_suggestions,
            company_id=company_id,
            batch_id=batch_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def review_financial_classification_suggestion(company_id: int, suggestion_id: int, decision: str) -> dict:
        """
        Confirma, aplica ou rejeita uma sugestão de classificação persistida.
        """
        from services.financial_classification_hybrid_service import FinancialClassificationHybridService

        result, error = _run_financial_action(
            FinancialClassificationHybridService.review_suggestion,
            suggestion_id=suggestion_id,
            company_id=company_id,
            decision=decision,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def ai_rank_financial_classification(company_id: int, batch_id: int) -> dict:
        """
        Gera ranking de classificação financeira por IA usando contexto do cliente, memórias e regras.
        """
        from services.financial_ai_classification_service import FinancialAIClassificationService

        result, error = _run_financial_action(
            FinancialAIClassificationService.rank_batch_with_ai,
            batch_id=batch_id,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def list_financial_classification_pending(company_id: int, batch_id: Optional[int] = None) -> dict:
        """
        Lista a fila de pendências de classificação financeira com pergunta sugerida ao usuário.
        """
        from services.financial_classification_hybrid_service import FinancialClassificationHybridService

        result, error = _run_financial_action(
            FinancialClassificationHybridService.list_pending_queue,
            company_id=company_id,
            batch_id=batch_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def get_financial_classification_dashboard(company_id: int) -> dict:
        """
        Retorna métricas executivas da classificação híbrida, memórias, fila pendente e cobertura.
        """
        from services.financial_classification_dashboard_service import FinancialClassificationDashboardService

        result, error = _run_financial_action(
            FinancialClassificationDashboardService.get_dashboard,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def list_financial_closings(company_id: int) -> dict:
        """
        Lista fechamentos financeiros registrados para a empresa.
        """
        from services.financial_closing_service import FinancialClosingService

        result, error = _run_financial_action(
            FinancialClosingService.list_closings,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def create_financial_closing(payload: dict) -> dict:
        """
        Registra fechamento financeiro do período com snapshot de conferência.
        """
        from services.financial_closing_service import FinancialClosingService

        result, error = _run_financial_action(
            FinancialClosingService.create_closing,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def list_financial_report_types(company_id: int) -> dict:
        """
        Lista relatórios automáticos disponíveis no módulo financeiro.
        """
        from services.financial_report_service import FinancialReportService

        result, error = _run_financial_action(
            FinancialReportService.list_report_types,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def generate_financial_report(company_id: int, report_type: str, period_start: str, period_end: str) -> dict:
        """
        Gera relatório financeiro automático para o período informado.
        """
        from services.financial_report_service import FinancialReportService

        result, error = _run_financial_action(
            FinancialReportService.generate_report,
            company_id=company_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def get_financial_executive_dashboard(
        company_id: int,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> dict:
        """
        Retorna dashboard executivo integrado do financeiro.
        """
        from services.financial_executive_dashboard_service import FinancialExecutiveDashboardService

        result, error = _run_financial_action(
            FinancialExecutiveDashboardService.get_dashboard,
            company_id=company_id,
            period_start=period_start,
            period_end=period_end,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def list_financial_budget_versions(company_id: int) -> dict:
        """
        Lista versões do orçamento matricial financeiro da empresa.
        """
        from services.financial_budget_service import FinancialBudgetService

        result, error = _run_financial_action(
            FinancialBudgetService.list_versions,
            company_id=company_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "items": result, "count": len(result)}

    @mcp.tool()
    def create_financial_budget_version(payload: dict) -> dict:
        """
        Cria uma nova versão de orçamento matricial financeiro.
        """
        from services.financial_budget_service import FinancialBudgetService

        result, error = _run_financial_action(
            FinancialBudgetService.create_version,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def duplicate_financial_budget_version(company_id: int, version_id: int, payload: Optional[dict] = None) -> dict:
        """
        Duplica uma versão existente do orçamento matricial financeiro.
        """
        from services.financial_budget_version_clone_service import FinancialBudgetVersionCloneService

        result, error = _run_financial_action(
            FinancialBudgetVersionCloneService.duplicate_version,
            company_id=company_id,
            source_version_id=version_id,
            payload=payload or {},
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": result}

    @mcp.tool()
    def get_financial_budget_matrix(company_id: int, version_id: int) -> dict:
        """
        Retorna a matriz orçamentária de uma versão financeira.
        """
        from services.financial_budget_service import FinancialBudgetService

        result, error = _run_financial_action(
            FinancialBudgetService.get_matrix,
            company_id=company_id,
            version_id=version_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def upsert_financial_budget_matrix(payload: dict) -> dict:
        """
        Atualiza ou cria linhas e valores da matriz orçamentária financeira.
        """
        from services.financial_budget_service import FinancialBudgetService

        result, error = _run_financial_action(
            FinancialBudgetService.upsert_matrix,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def import_financial_budget_matrix(company_id: int, version_id: int, file_name: str, file_base64: str) -> dict:
        """
        Importa uma planilha XLSX da matriz orçamentária financeira.
        """
        import base64
        from services.financial_budget_import_service import FinancialBudgetImportService

        try:
            file_bytes = base64.b64decode(file_base64)
        except Exception:
            return {"success": False, "error": "file_base64 inválido para importação da matriz orçamentária."}

        result, error = _run_financial_action(
            FinancialBudgetImportService.import_matrix_file,
            company_id=company_id,
            version_id=version_id,
            file_name=file_name,
            file_bytes=file_bytes,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def ask_user_for_financial_classification(
        company_id: int,
        import_row_id: int,
        user_id: int,
        preferred_channel: Optional[str] = None,
    ) -> dict:
        """
        Dispara a pergunta de classificação financeira ao usuário via Sapiens/canal preferido.
        """
        from services.financial_classification_question_service import FinancialClassificationQuestionService

        result, error = _run_financial_action(
            FinancialClassificationQuestionService.dispatch_question_to_user,
            company_id=company_id,
            import_row_id=import_row_id,
            user_id=user_id,
            preferred_channel=preferred_channel,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}

    @mcp.tool()
    def resolve_financial_classification_answer(
        company_id: int,
        import_row_id: int,
        answer_payload: dict,
        user_id: Optional[int] = None,
    ) -> dict:
        """
        Aplica a resposta do usuário para uma pendência de classificação e alimenta a memória quando solicitado.
        """
        from services.financial_classification_hybrid_service import FinancialClassificationHybridService

        result, error = _run_financial_action(
            FinancialClassificationHybridService.resolve_user_answer,
            company_id=company_id,
            import_row_id=import_row_id,
            answer_payload=answer_payload,
            user_id=user_id,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, **result}


__all__ = ["register_financial_mcp_tools"]
