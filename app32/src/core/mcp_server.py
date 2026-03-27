import asyncio
import sys
import os
import base64
from typing import Any, Optional

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.intelligence.tools import consult_rules, query_database, get_my_work

from src.intelligence.tools import tools as system_tools

# Tenta importar MCP
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

def run_mcp_server():
    if not FastMCP:
        print("ERRO: Biblioteca 'mcp' não encontrada.", file=sys.stderr)
        print("Instale com: pip install mcp fastmcp", file=sys.stderr)
        sys.exit(1)

    # Cria o servidor MCP
    mcp = FastMCP("GestaoVersus Core System")

    # Registro dinâmico de ferramentas do LangGraph/Intelligence
    # Isso garante que tanto o Agente interno quanto Agentes externos (MCP)
    # usem exatamente a mesma lógica de negócio (Regra do Espelhamento).
    for tool in system_tools:
        # FastMCP usa introspecção da função Python (assinatura e docstring)
        # Vamos passar a função original (tool.func) para gerar o Schema exato
        if hasattr(tool, 'func'):
            mcp.tool(name=tool.name, description=tool.description)(tool.func)
        else:
            # Caso não tenha func, fallback
            def make_wrapper(t):
                @mcp.tool(name=t.name, description=t.description)
                def mcp_tool_wrapper(*args, **kwargs):
                    return t.invoke(kwargs if kwargs else args[0] if args else {})
                return mcp_tool_wrapper
            make_wrapper(tool)


    # Ferramentas Adicionais de Diagnóstico de Sistema
    @mcp.tool()
    def get_system_health() -> str:
        """Verifica a saúde do banco de dados e do servidor."""
        from src.core.database import db
        status, msg = db.health_check()
        return f"Database: {'OK' if status else 'ERROR'} - {msg}"

    @mcp.tool()
    def get_database_schema() -> str:
        """Retorna uma lista de todas as tabelas do banco de dados (Visão Geral)."""
        from src.core.database import db
        from sqlalchemy import text
        try:
            with db.engine.connect() as connection:
                query = text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                result = connection.execute(query)
                tables = [row[0] for row in result]
                return f"Tabelas ativas: {', '.join(tables)}"
        except Exception as e:
            return f"Erro ao ler schema: {str(e)}"

    @mcp.tool()
    def harvest_incentive_module(company_id: int) -> str:
        """
        Dispara a coleta automática de fatos para o módulo de Incentivos (S3).
        Lê processos, projetos e ocorrências do banco e gera fatos para o bônus.
        """
        from app import create_app
        from services.incentive_service import IncentiveService
        from datetime import date
        from models import db
        
        # Cria app para ter context de DB (SQLAlchemy)
        app = create_app()
        
        today = date.today()
        p_start = date(today.year, today.month, 1)
        p_end = today
        
        try:
            with app.app_context():
                results = IncentiveService.harvest_all_modules(company_id, p_start, p_end)
                db.session.commit()
                summary = results.get('summary', {})
                return f"Coleta S3 concluída: Proc={summary.get('processo')}, Proj={summary.get('projeto')}, Ocor={summary.get('ocorrencia')}. Pendentes Manual: {summary.get('manual_pendente')}"
        except Exception as e:
            return f"Erro na coleta: {str(e)}"

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
            payload=payload,
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

        entry, error = _run_financial_action(
            FinancialService.create_entry,
            payload=payload,
        )
        if error:
            return {"success": False, "error": error}
        return {"success": True, "item": entry.to_dict()}

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
    def review_financial_reconciliation_match(company_id: int, match_id: int, decision: str) -> dict:
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
    def preview_financial_closing(company_id: int, period_start: str, period_end: str) -> dict:
        """
        Gera conferência e prévia do fechamento financeiro para um período.
        """
        from datetime import datetime
        from services.financial_closing_service import FinancialClosingService

        result, error = _run_financial_action(
            FinancialClosingService.preview_closing,
            company_id=company_id,
            period_start=datetime.strptime(period_start, "%Y-%m-%d").date(),
            period_end=datetime.strptime(period_end, "%Y-%m-%d").date(),
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

    # Inicia o servidor
    print("Iniciando MCP Server via STDIO (AI-Readable Mode)...", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    run_mcp_server()
