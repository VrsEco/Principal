from __future__ import annotations

import io
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models import db
from models.financial import (
    FinancialAccountCategory,
    FinancialAssetAccount,
    FinancialBankAccount,
    FinancialBordero,
    FinancialBorderoItem,
    FinancialChartAccount,
    FinancialCostCenter,
    FinancialCounterparty,
    FinancialEntry,
    FinancialSchedule,
    FinancialSettlement,
)
from models.process import Process
from models.project import Project
from schemas.financial_reports import FinancialManagementReportFiltersInput
from services.financial_dashboard_analytics import FinancialDashboardAnalytics
from services.financial_service import FinancialService


class FinancialReportService:
    """Relatórios gerenciais do módulo financeiro com saída HTML/PDF/XLSX."""

    WORKING_CAPITAL_PROGRAMMED_ACCOUNTS: tuple[Dict[str, Any], ...] = (
        {"id": 1, "description": "1.1.1 - Disponibilidades", "type": "Ativo", "class_name": "Circulante", "category": "Saldo Conta Corrente", "rule": "bank_balance"},
        {"id": 2, "description": "1.2.1 - Recebíveis a Vencer (até 06 meses)", "type": "Ativo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "receivable_due_180"},
        {"id": 3, "description": "1.2.2 - Recebíveis em Atraso", "type": "Ativo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "receivable_overdue"},
        {"id": 4, "description": "2.1.1 - Contas a Pagar / Fornecedores - A Vencer", "type": "Passivo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "payable_supplier_due"},
        {"id": 5, "description": "2.1.2 - Contas a Pagar / Fornecedores - Vencidas", "type": "Passivo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "payable_supplier_overdue"},
        {"id": 6, "description": "2.2.1 - Funcionários e Colaboradores - A Vencer", "type": "Passivo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "payable_people_due"},
        {"id": 7, "description": "2.2.2 - Funcionários e Colaboradores - Vencidas", "type": "Passivo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "payable_people_overdue"},
        {"id": 8, "description": "2.3.1 - Impostos a Vencer", "type": "Passivo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "payable_tax_due"},
        {"id": 9, "description": "2.3.2 - Impostos Vencidos", "type": "Passivo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "payable_tax_overdue"},
        {"id": 10, "description": "2.4.1 - Empréstimos e Financiamentos a Vencer", "type": "Passivo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "payable_financing_due"},
        {"id": 11, "description": "2.4.2 - Empréstimos e Financiamentos Vencidos", "type": "Passivo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "payable_financing_overdue"},
        {"id": 12, "description": "1.3.1 - Investimentos Contratados a Receber - A Vencer", "type": "Ativo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "receivable_investment_due"},
        {"id": 13, "description": "1.3.2 - Investimentos Contratados a Receber - Vencidos", "type": "Ativo", "class_name": "Circulante", "category": "Data de Vencimento", "rule": "receivable_investment_overdue"},
    )

    REPORT_TYPES: tuple[str, ...] = (
        "schedule_report",
        "bank_statement",
        "income_statement",
        "cash_flow",
        "ledger",
        "working_capital",
    )

    REPORT_DEFINITIONS: Dict[str, Dict[str, Any]] = {
        "schedule_report": {
            "code": "schedule_report",
            "slug": "agendamento",
            "label": "Relatório de Agendamentos",
            "description": "Mapa operacional dos agendamentos financeiros com títulos, saldos, liquidação e vínculo com borderô.",
            "filters": ("schedule_report_config",),
        },
        "bank_statement": {
            "code": "bank_statement",
            "slug": "extrato-bancario",
            "label": "Extrato Bancário",
            "description": "Extrato gerencial dos movimentos liquidados por conta bancária com saldo inicial, entradas, saídas e saldo final.",
            "filters": ("period", "bank_account", "include_reconciled_only"),
        },
        "income_statement": {
            "code": "income_statement",
            "slug": "demonstrativo-resultados",
            "label": "Demonstrativo de Resultados",
            "description": "DRE gerencial nas visões de competência, vencimento e liquidação por conta contábil.",
            "filters": (
                "competence_period",
                "due_period",
                "settlement_period",
                "chart_account_multi",
                "cost_center_multi",
                "project_multi",
                "income_statement_config",
            ),
        },
        "cash_flow": {
            "code": "cash_flow",
            "slug": "fluxo-caixa",
            "label": "Fluxo de Caixa",
            "description": "Fluxo diário com saldo inicial, realizado, projeções abertas e saldo acumulado do período.",
            "filters": ("cash_flow_config",),
        },
        "ledger": {
            "code": "ledger",
            "slug": "razao",
            "label": "Razão",
            "description": "Razão gerencial por conta contábil, com histórico dos lançamentos, liquidação vinculada e saldo acumulado.",
            "filters": ("ledger_config",),
        },
        "working_capital": {
            "code": "working_capital",
            "slug": "capital-circulante-liquido",
            "label": "Capital Circulante Líquido",
            "description": "Composição do capital circulante líquido com disponibilidades, recebíveis, exigibilidades e folga financeira.",
            "filters": ("working_capital_config",),
        },
    }

    @staticmethod
    def _definition_by_slug(report_slug: str) -> Optional[Dict[str, Any]]:
        normalized = str(report_slug or "").strip().lower()
        for definition in FinancialReportService.REPORT_DEFINITIONS.values():
            if definition["slug"] == normalized:
                return definition
        return None

    @staticmethod
    def get_report_definition(identifier: str) -> Optional[Dict[str, Any]]:
        normalized = str(identifier or "").strip().lower()
        if normalized in FinancialReportService.REPORT_DEFINITIONS:
            return FinancialReportService.REPORT_DEFINITIONS[normalized]
        return FinancialReportService._definition_by_slug(normalized)

    @staticmethod
    def get_report_definition_or_error(identifier: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        definition = FinancialReportService.get_report_definition(identifier)
        if not definition:
            return None, "Tipo de relatório financeiro inválido."
        return definition, None

    @staticmethod
    def default_period() -> Tuple[date, date]:
        today = date.today()
        return today.replace(day=1), today

    @staticmethod
    def _normalize_filters(report_type: str, raw_filters: Optional[Dict[str, Any]]) -> Tuple[Optional[FinancialManagementReportFiltersInput], Optional[str]]:
        payload = dict(raw_filters or {})
        if report_type == "cash_flow":
            payload.setdefault("frequency", "daily")
        if report_type == "working_capital":
            payload.setdefault("include_overdraft", "true")
        payload["report_type"] = report_type
        for key, value in list(payload.items()):
            if value in ("", None):
                payload.pop(key, None)
        try:
            data = FinancialManagementReportFiltersInput(**payload)
        except Exception as exc:
            return None, f"Filtros inválidos para o relatório: {exc}"

        period_start, period_end = data.period_start, data.period_end
        if not period_start or not period_end:
            default_start, default_end = FinancialReportService.default_period()
            period_start = period_start or data.competence_start or default_start
            period_end = period_end or data.competence_end or default_end
            data = data.model_copy(update={"period_start": period_start, "period_end": period_end})

        if data.report_type == "income_statement":
            updates = {}
            if not data.competence_start:
                updates["competence_start"] = data.period_start
            if not data.competence_end:
                updates["competence_end"] = data.period_end
            if updates:
                data = data.model_copy(update=updates)

        for start_attr, end_attr, label in [
            ("period_start", "period_end", "Período"),
            ("competence_start", "competence_end", "Competência"),
            ("due_start", "due_end", "Vencimento"),
            ("settlement_start", "settlement_end", "Baixa"),
        ]:
            start_value = getattr(data, start_attr)
            end_value = getattr(data, end_attr)
            if (start_value and not end_value) or (end_value and not start_value):
                return None, f"Faixa de {label.lower()} incompleta para relatório."
            if start_value and end_value and start_value > end_value:
                return None, f"Faixa de {label.lower()} inválida para relatório."

        if data.report_type == "income_statement":
            if not any([data.include_open, data.include_settled]):
                return None, "Selecione ao menos um status para o DRE."
            if not any([data.include_receivable, data.include_payable, data.include_budget_vs_actual]):
                return None, "Selecione ao menos um tipo para o DRE."
            if not any([data.show_code, data.show_description]):
                return None, "Selecione ao menos uma coluna de identificação para o DRE."
        if data.report_type == "schedule_report":
            updates = {"orientation": "portrait"}
            if not data.competence_start:
                updates["competence_start"] = data.period_start
            if not data.competence_end:
                updates["competence_end"] = data.period_end
            if updates:
                data = data.model_copy(update=updates)
            if not any([data.include_settled, data.include_partial, data.include_open, data.include_bordero]):
                return None, "Selecione ao menos um status para o relatório de agendamentos."
            if not any([data.include_receivable, data.include_payable]):
                return None, "Selecione ao menos um tipo para o relatório de agendamentos."
            if not any([
                data.show_title_number,
                data.show_installment,
                data.show_history,
                data.show_counterparty,
                data.show_title_amount,
                data.show_balance_amount,
                data.show_competence_date,
                data.show_due_date,
                data.show_settlement_date,
            ]):
                return None, "Selecione ao menos uma coluna para exibir no relatório de agendamentos."
        if data.report_type == "working_capital" and data.reference_date:
            data = data.model_copy(update={"period_end": data.reference_date, "period_start": data.reference_date})
        return data, None

    @staticmethod
    def _serialize_money(value: Decimal | float | int) -> float:
        return float(Decimal(value or 0).quantize(Decimal("0.01")))

    @staticmethod
    def _format_currency(value: Decimal | float | int) -> str:
        amount = FinancialReportService._serialize_money(value)
        inteiro, decimal = f"{amount:,.2f}".split(".")
        return f"R$ {inteiro.replace(',', '.')},{decimal}"

    @staticmethod
    def _format_signed_currency(value: Decimal | float | int, *, positive_sign: bool = False) -> str:
        amount = Decimal(value or 0)
        signal = ""
        if amount < 0:
            signal = "- "
        elif positive_sign and amount > 0:
            signal = "+ "
        return f"{signal}{FinancialReportService._format_currency(abs(amount))}"

    @staticmethod
    def _reconciliation_status_label(value: Optional[str]) -> str:
        return {
            "pending": "Pendente",
            "suggested": "Sugerida",
            "matched": "Casada",
            "reconciled": "Conciliada",
            "rejected": "Rejeitada",
        }.get(str(value or "").strip().lower(), "Não informada")

    @staticmethod
    def _reconciliation_status_tone(value: Optional[str]) -> str:
        return {
            "pending": "neutral",
            "suggested": "primary",
            "matched": "primary",
            "reconciled": "positive",
            "rejected": "negative",
        }.get(str(value or "").strip().lower(), "neutral")

    @staticmethod
    def _name_map(model, company_id: int) -> Dict[int, str]:
        query = model.query.filter(model.company_id == company_id)
        if hasattr(model, "deleted_at"):
            query = query.filter(model.deleted_at.is_(None))
        items = query.all()
        result: Dict[int, str] = {}
        for item in items:
            code = getattr(item, "code", None)
            prefix = f"{code} - " if code else ""
            result[item.id] = f"{prefix}{getattr(item, 'name', str(item.id))}"
        return result

    @staticmethod
    def _working_capital_type_label(value: Optional[str]) -> str:
        return {
            "asset": "Ativo",
            "liability": "Passivo",
            "equity": "Patrimônio Líquido",
        }.get(str(value or "").strip().lower(), "Ativo")

    @staticmethod
    def _working_capital_class_label(value: Optional[str]) -> str:
        return {
            "current": "Circulante",
            "non_current": "Não Circulante",
        }.get(str(value or "").strip().lower(), "Circulante")

    @staticmethod
    def _working_capital_value_label(config_mode: str, metadata: Dict[str, Any]) -> str:
        if config_mode == "bank_balances":
            return "Saldo Conta Corrente"
        if config_mode == "manual_value":
            return "Informado na emissão"
        due_scope = str(metadata.get("due_scope") or "overdue").strip().lower()
        if due_scope == "all_future":
            return "Todas a vencer"
        if due_scope == "due_in_days":
            days = metadata.get("due_in_days")
            return f"A vencer em {days} dias" if days not in (None, "") else "A vencer em dias"
        return "Vencidas"

    @staticmethod
    def _get_working_capital_accounts(company_id: int) -> List[Dict[str, Any]]:
        category_names = FinancialReportService._name_map(FinancialAccountCategory, company_id)
        records = FinancialAssetAccount.query.filter(
            FinancialAssetAccount.company_id == company_id,
            FinancialAssetAccount.deleted_at.is_(None),
            FinancialAssetAccount.is_active.is_(True),
        ).order_by(FinancialAssetAccount.code.asc(), FinancialAssetAccount.name.asc()).all()

        if records:
            options: List[Dict[str, Any]] = []
            for item in records:
                metadata = dict(item.metadata_json or {})
                config_mode = str(metadata.get("config_mode") or "due_dates").strip().lower()
                category_id = metadata.get("category_id")
                category_label = category_names.get(category_id) if category_id else None
                options.append(
                    {
                        "id": item.id,
                        "description": f"{item.code} - {item.name}" if item.code else item.name,
                        "type": FinancialReportService._working_capital_type_label(metadata.get("patrimonial_type")),
                        "class_name": FinancialReportService._working_capital_class_label(metadata.get("account_class")),
                        "category": category_label or FinancialReportService._working_capital_type_label(metadata.get("patrimonial_type")),
                        "rule": config_mode,
                        "config_mode": config_mode,
                        "value_label": FinancialReportService._working_capital_value_label(config_mode, metadata),
                        "requires_manual_value": config_mode == "manual_value",
                        "metadata_json": metadata,
                        "code": item.code,
                        "name": item.name,
                    }
                )
            return options

        return [dict(item) for item in FinancialReportService.WORKING_CAPITAL_PROGRAMMED_ACCOUNTS]

    @staticmethod
    def get_filter_options(*, company_id: int, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[Dict[str, List[Dict[str, Any]]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        def _natural_sort_parts(value: str) -> Tuple[Any, ...]:
            return tuple(int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value or ""))

        def _code_sort_key(item):
            code = str(getattr(item, "code", "") or "")
            name = str(getattr(item, "name", "") or "")
            return (_natural_sort_parts(code), _natural_sort_parts(name), int(getattr(item, "id", 0) or 0))

        def _base_records(model):
            query = model.query.filter(model.company_id == company_id)
            if hasattr(model, "deleted_at"):
                query = query.filter(model.deleted_at.is_(None))
            if hasattr(model, "is_active"):
                query = query.filter(model.is_active.is_(True))
            return sorted(query.all(), key=_code_sort_key)

        def _label(item, *, level: int = 0) -> str:
            code = str(getattr(item, "code", "") or "")
            name = str(getattr(item, "name", "") or "")
            prefix = "— " * max(level, 0)
            return f"{prefix}{code} - {name}" if code else f"{prefix}{name}"

        def _flat_list(model):
            return [
                {
                    "id": item.id,
                    "label": _label(item),
                    "code": str(getattr(item, "code", "") or ""),
                    "selectable": True,
                    "level": 0,
                }
                for item in _base_records(model)
            ]

        def _hierarchical_list(model):
            records = _base_records(model)
            by_id = {item.id: item for item in records}
            parent_ids = {item.parent_id for item in records if getattr(item, "parent_id", None)}
            level_cache: Dict[int, int] = {}

            def _level(item) -> int:
                if item.id in level_cache:
                    return level_cache[item.id]
                seen = {item.id}
                current = item
                level = 0
                while getattr(current, "parent_id", None) and current.parent_id in by_id and current.parent_id not in seen:
                    level += 1
                    seen.add(current.parent_id)
                    current = by_id[current.parent_id]
                level_cache[item.id] = level
                return level

            return [
                {
                    "id": item.id,
                    "label": _label(item, level=_level(item)),
                    "code": str(getattr(item, "code", "") or ""),
                    "selectable": bool(getattr(item, "accepts_posting", True)) and item.id not in parent_ids,
                    "level": _level(item),
                }
                for item in records
            ]

        return {
            "bank_accounts": _flat_list(FinancialBankAccount),
            "chart_accounts": _hierarchical_list(FinancialChartAccount),
            "cost_centers": _hierarchical_list(FinancialCostCenter),
            "projects": _flat_list(Project),
            "processes": _flat_list(Process),
            "working_capital_accounts": FinancialReportService._get_working_capital_accounts(company_id),
            "counterparties": _flat_list(FinancialCounterparty),
            "movement_natures": [{"id": "credit", "label": "Entrada"}, {"id": "debit", "label": "Saída"}],
            "schedule_statuses": [
                {"id": "draft", "label": "Rascunho"},
                {"id": "active", "label": "Ativo"},
                {"id": "paused", "label": "Pausado"},
                {"id": "completed", "label": "Concluído"},
                {"id": "cancelled", "label": "Cancelado"},
            ],
            "frequencies": [
                {"id": "one_time", "label": "Uma vez"},
                {"id": "weekly", "label": "Semanal"},
                {"id": "monthly", "label": "Mensal"},
                {"id": "yearly", "label": "Anual"},
            ],
        }, None

    @staticmethod
    def list_report_types(*, company_id: int, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        return [
            {"code": code, "slug": definition["slug"], "label": definition["label"], "description": definition["description"]}
            for code, definition in FinancialReportService.REPORT_DEFINITIONS.items()
        ], None

    @staticmethod
    def _selected_ids(single_id: Optional[int], multiple_ids: Optional[Sequence[int]]) -> List[int]:
        values: List[int] = []
        for current in list(multiple_ids or []) + ([single_id] if single_id else []):
            try:
                parsed = int(current)
            except (TypeError, ValueError):
                continue
            if parsed > 0 and parsed not in values:
                values.append(parsed)
        return values

    @staticmethod
    def _entry_project_ids(entry: FinancialEntry) -> List[int]:
        metadata = getattr(entry, "metadata_json", None) or {}
        candidates = [metadata.get("project_id"), metadata.get("app_project_id"), metadata.get("grv_project_id")]
        values = metadata.get("project_ids") or []
        if isinstance(values, (list, tuple, set)):
            candidates.extend(values)
        project_ids: List[int] = []
        for value in candidates:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0 and parsed not in project_ids:
                project_ids.append(parsed)
        return project_ids

    @staticmethod
    def _entry_matches_projects(entry: FinancialEntry, project_ids: Sequence[int]) -> bool:
        selected = {int(item) for item in project_ids if item}
        if not selected:
            return True
        return bool(selected.intersection(FinancialReportService._entry_project_ids(entry)))

    @staticmethod
    def _schedule_project_ids(schedule: FinancialSchedule) -> List[int]:
        metadata = dict(getattr(schedule, "metadata_json", None) or {})
        candidates = [
            metadata.get("project_id"),
            metadata.get("app_project_id"),
            metadata.get("grv_project_id"),
        ]
        values = metadata.get("project_ids") or []
        if isinstance(values, (list, tuple, set)):
            candidates.extend(values)

        allocations = metadata.get("allocations") or []
        if isinstance(allocations, list):
            for allocation in allocations:
                if not isinstance(allocation, dict):
                    continue
                candidates.extend([
                    allocation.get("project_id"),
                    allocation.get("app_project_id"),
                    allocation.get("grv_project_id"),
                ])
                allocation_values = allocation.get("project_ids") or []
                if isinstance(allocation_values, (list, tuple, set)):
                    candidates.extend(allocation_values)

        project_ids: List[int] = []
        for value in candidates:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0 and parsed not in project_ids:
                project_ids.append(parsed)
        return project_ids

    @staticmethod
    def _schedule_matches_projects(schedule: FinancialSchedule, project_ids: Sequence[int]) -> bool:
        selected = {int(item) for item in project_ids if item}
        if not selected:
            return True
        return bool(selected.intersection(FinancialReportService._schedule_project_ids(schedule)))

    @staticmethod
    def _schedule_process_ids(schedule: FinancialSchedule) -> List[int]:
        metadata = dict(getattr(schedule, "metadata_json", None) or {})
        candidates = [
            metadata.get("process_id"),
            metadata.get("app_process_id"),
            metadata.get("grv_process_id"),
        ]
        values = metadata.get("process_ids") or []
        if isinstance(values, (list, tuple, set)):
            candidates.extend(values)

        process_instance = getattr(schedule, "process_instance", None)
        if process_instance is not None:
            candidates.append(getattr(process_instance, "process_id", None))

        activity = getattr(schedule, "activity", None)
        if activity is not None:
            candidates.append(getattr(activity, "process_id", None))

        process_ids: List[int] = []
        for value in candidates:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0 and parsed not in process_ids:
                process_ids.append(parsed)
        return process_ids

    @staticmethod
    def _schedule_matches_processes(schedule: FinancialSchedule, process_ids: Sequence[int]) -> bool:
        selected = {int(item) for item in process_ids if item}
        if not selected:
            return True
        return bool(selected.intersection(FinancialReportService._schedule_process_ids(schedule)))

    @staticmethod
    def _entry_query(company_id: int, filters: FinancialManagementReportFiltersInput):
        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.competence_date >= filters.period_start,
            FinancialEntry.competence_date <= filters.period_end,
        )
        bank_account_ids = FinancialReportService._selected_ids(filters.bank_account_id, filters.bank_account_ids)
        if bank_account_ids:
            query = query.filter(FinancialEntry.bank_account_id.in_(bank_account_ids))
        chart_account_ids = FinancialReportService._selected_ids(filters.chart_account_id, filters.chart_account_ids)
        if chart_account_ids:
            query = query.filter(FinancialEntry.chart_account_id.in_(chart_account_ids))
        cost_center_ids = FinancialReportService._selected_ids(filters.cost_center_id, filters.cost_center_ids)
        if cost_center_ids:
            query = query.filter(FinancialEntry.cost_center_id.in_(cost_center_ids))
        counterparty_ids = FinancialReportService._selected_ids(filters.counterparty_id, filters.counterparty_ids)
        if counterparty_ids:
            query = query.filter(FinancialEntry.counterparty_id.in_(counterparty_ids))
        if filters.movement_nature:
            query = query.filter(FinancialEntry.movement_nature == filters.movement_nature)
        return query

    @staticmethod
    def _open_entries_until(company_id: int, filters: FinancialManagementReportFiltersInput, until: date) -> List[FinancialEntry]:
        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.status.in_(["draft", "pending_review", "scheduled", "posted", "partially_settled"]),
            FinancialEntry.due_date.isnot(None),
            FinancialEntry.due_date <= until,
        )
        bank_account_ids = FinancialReportService._selected_ids(filters.bank_account_id, filters.bank_account_ids)
        if bank_account_ids:
            query = query.filter(FinancialEntry.bank_account_id.in_(bank_account_ids))
        if filters.chart_account_id:
            query = query.filter(FinancialEntry.chart_account_id == filters.chart_account_id)
        if filters.cost_center_id:
            query = query.filter(FinancialEntry.cost_center_id == filters.cost_center_id)
        return query.order_by(FinancialEntry.due_date.asc(), FinancialEntry.id.asc()).all()

    @staticmethod
    def _settlement_query(company_id: int, filters: FinancialManagementReportFiltersInput):
        query = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
            FinancialSettlement.settlement_date >= filters.period_start,
            FinancialSettlement.settlement_date <= filters.period_end,
        )
        bank_account_ids = FinancialReportService._selected_ids(filters.bank_account_id, filters.bank_account_ids)
        if bank_account_ids:
            query = query.filter(FinancialSettlement.bank_account_id.in_(bank_account_ids))
        if filters.include_reconciled_only:
            query = query.filter(FinancialSettlement.reconciliation_status == "reconciled")
        return query

    @staticmethod
    def _build_schedule_report(company_id: int, filters: FinancialManagementReportFiltersInput) -> Dict[str, Any]:
        definition = FinancialReportService.REPORT_DEFINITIONS[filters.report_type]
        counterparty_names = FinancialReportService._name_map(FinancialCounterparty, company_id)
        query = FinancialSchedule.query.filter(
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        )
        if filters.competence_start and filters.competence_end:
            query = query.filter(
                FinancialSchedule.start_date >= filters.competence_start,
                FinancialSchedule.start_date <= filters.competence_end,
            )
        if filters.due_start and filters.due_end:
            query = query.filter(
                FinancialSchedule.next_due_date >= filters.due_start,
                FinancialSchedule.next_due_date <= filters.due_end,
            )
        if filters.bank_account_id:
            query = query.filter(FinancialSchedule.bank_account_id == filters.bank_account_id)
        counterparty_ids = FinancialReportService._selected_ids(filters.counterparty_id, filters.counterparty_ids)
        if counterparty_ids:
            query = query.filter(FinancialSchedule.counterparty_id.in_(counterparty_ids))
        chart_account_ids = FinancialReportService._selected_ids(filters.chart_account_id, filters.chart_account_ids)
        if chart_account_ids:
            query = query.filter(FinancialSchedule.chart_account_id.in_(chart_account_ids))
        cost_center_ids = FinancialReportService._selected_ids(filters.cost_center_id, filters.cost_center_ids)
        if cost_center_ids:
            query = query.filter(FinancialSchedule.cost_center_id.in_(cost_center_ids))
        allowed_entry_types = []
        if filters.include_payable:
            allowed_entry_types.append("payable")
        if filters.include_receivable:
            allowed_entry_types.append("receivable")
        if allowed_entry_types:
            query = query.filter(FinancialSchedule.entry_type.in_(allowed_entry_types))

        schedules = query.order_by(FinancialSchedule.next_due_date.asc(), FinancialSchedule.id.asc()).all()
        if filters.process_ids:
            schedules = [item for item in schedules if FinancialReportService._schedule_matches_processes(item, filters.process_ids)]
        if filters.project_ids:
            schedules = [item for item in schedules if FinancialReportService._schedule_matches_projects(item, filters.project_ids)]

        schedule_map = {item.id: item for item in schedules}
        entry_refs = {f"financial_schedule:{item.id}": item.id for item in schedules}
        entries = []
        if entry_refs:
            entries = FinancialEntry.query.filter(
                FinancialEntry.company_id == company_id,
                FinancialEntry.external_reference.in_(list(entry_refs.keys())),
                FinancialEntry.deleted_at.is_(None),
            ).all()

        entries_by_schedule: Dict[int, List[FinancialEntry]] = {item.id: [] for item in schedules}
        for entry in entries:
            schedule_id = entry_refs.get(entry.external_reference)
            if schedule_id and schedule_id in entries_by_schedule:
                entries_by_schedule[schedule_id].append(entry)

        settlements_by_entry: Dict[int, List[FinancialSettlement]] = {}
        if entries:
            entry_ids = [item.id for item in entries]
            settlements = FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.financial_entry_id.in_(entry_ids),
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            ).order_by(
                FinancialSettlement.financial_entry_id.asc(),
                FinancialSettlement.settlement_date.asc(),
                FinancialSettlement.id.asc(),
            ).all()
            for settlement in settlements:
                settlements_by_entry.setdefault(settlement.financial_entry_id, []).append(settlement)

        active_borderos_by_schedule: Dict[int, FinancialBordero] = {}
        if schedules:
            bordero_rows = db.session.query(FinancialBorderoItem, FinancialBordero).join(
                FinancialBordero,
                FinancialBorderoItem.bordero_id == FinancialBordero.id,
            ).filter(
                FinancialBorderoItem.company_id == company_id,
                FinancialBorderoItem.financial_schedule_id.in_(list(schedule_map.keys())),
                FinancialBorderoItem.deleted_at.is_(None),
                FinancialBordero.company_id == company_id,
                FinancialBordero.deleted_at.is_(None),
                FinancialBordero.status.in_(("draft", "open", "partially_settled")),
            ).order_by(FinancialBordero.id.desc()).all()
            for bordero_item, bordero in bordero_rows:
                active_borderos_by_schedule.setdefault(bordero_item.financial_schedule_id, bordero)

        rows: List[Dict[str, Any]] = []
        receivable_title_total = Decimal("0")
        receivable_open_total = Decimal("0")
        payable_title_total = Decimal("0")
        payable_open_total = Decimal("0")
        open_count = 0
        bordero_count = 0

        for schedule in schedules:
            metadata = dict(schedule.metadata_json or {})
            schedule_entries = entries_by_schedule.get(schedule.id, [])
            original_total = Decimal("0")
            settled_total = Decimal("0")
            open_total = Decimal("0")
            settled_entries = 0
            partial_entries = 0
            open_entries = 0
            latest_settlement_date = None

            if not schedule_entries:
                template_amount = Decimal(str(schedule.template_amount or 0))
                original_total = template_amount
                if schedule.status not in {"completed", "cancelled"} and template_amount > 0:
                    open_total = template_amount
                    open_entries = 1

            for entry in schedule_entries:
                original_amount = Decimal(str(entry.original_amount or 0))
                entry_settlements = settlements_by_entry.get(entry.id, [])
                settlements_total = sum(Decimal(str(item.principal_amount or 0)) for item in entry_settlements)
                outstanding = max(original_amount - settlements_total, Decimal("0"))
                original_total += original_amount
                settled_total += settlements_total
                open_total += outstanding
                if entry_settlements:
                    latest_entry_settlement = entry_settlements[-1].settlement_date
                    if latest_entry_settlement and (latest_settlement_date is None or latest_entry_settlement > latest_settlement_date):
                        latest_settlement_date = latest_entry_settlement
                if outstanding == 0 and original_amount > 0:
                    settled_entries += 1
                elif settlements_total > 0:
                    partial_entries += 1
                else:
                    open_entries += 1

            settlement_state = "open"
            if schedule_entries:
                if open_entries == 0 and partial_entries == 0:
                    settlement_state = "settled"
                elif partial_entries > 0 or settled_entries > 0:
                    settlement_state = "partial"

            active_bordero = active_borderos_by_schedule.get(schedule.id)
            report_state = "bordero" if active_bordero else settlement_state
            if report_state == "settled" and not filters.include_settled:
                continue
            if report_state == "partial" and not filters.include_partial:
                continue
            if report_state == "open" and not filters.include_open:
                continue
            if report_state == "bordero" and not filters.include_bordero:
                continue

            if filters.settlement_start and filters.settlement_end:
                if not latest_settlement_date:
                    continue
                if latest_settlement_date < filters.settlement_start or latest_settlement_date > filters.settlement_end:
                    continue

            signed_title_amount = Decimal(str(FinancialService.get_signed_amount(original_total, schedule.movement_nature)))
            signed_open_amount = Decimal(str(FinancialService.get_signed_amount(open_total, schedule.movement_nature)))
            if schedule.entry_type == "receivable":
                receivable_title_total += original_total
                receivable_open_total += signed_open_amount
            else:
                payable_title_total += original_total
                payable_open_total += signed_open_amount
            if report_state != "settled":
                open_count += 1
            if report_state == "bordero":
                bordero_count += 1

            installment_value = (
                metadata.get("installment_number")
                or metadata.get("parcela")
                or metadata.get("installment_label")
                or metadata.get("parcel_label")
                or metadata.get("repeat_label")
                or "-"
            )
            title_number_value = schedule.document_number_prefix or schedule.schedule_code or str(schedule.id)
            history_value = schedule.name or schedule.description or "-"
            counterparty_value = counterparty_names.get(schedule.counterparty_id) or metadata.get("counterparty_name") or "Não informado"
            competence_date_value = schedule.start_date.isoformat() if schedule.start_date else "-"
            due_date_value = (schedule.next_due_date or schedule.first_due_date).isoformat() if (schedule.next_due_date or schedule.first_due_date) else "-"
            settlement_date_value = latest_settlement_date.isoformat() if latest_settlement_date else "-"
            status_label = {
                "settled": "Liquidado",
                "partial": "Liquidado Parcial",
                "open": "Aberto",
                "bordero": "Borderô",
            }[report_state]
            type_label = "Recebimento" if schedule.entry_type == "receivable" else "Pagamento"

            rows.append(
                {
                    "title_number": title_number_value,
                    "installment": str(installment_value),
                    "history": history_value,
                    "counterparty": counterparty_value,
                    "title_amount": FinancialReportService._format_currency(signed_title_amount),
                    "balance_amount": FinancialReportService._format_currency(signed_open_amount),
                    "competence_date": competence_date_value,
                    "due_date": due_date_value,
                    "settlement_date": settlement_date_value,
                    "status": status_label,
                    "type": type_label,
                    "_title_number_sort": str(title_number_value or "").lower(),
                    "_installment_sort": str(installment_value or "").lower(),
                    "_history_sort": str(history_value or "").lower(),
                    "_counterparty_sort": str(counterparty_value or "").lower(),
                    "_title_amount_sort": float(signed_title_amount),
                    "_balance_amount_sort": float(signed_open_amount),
                    "_competence_date_sort": competence_date_value if competence_date_value != "-" else "",
                    "_due_date_sort": due_date_value if due_date_value != "-" else "",
                    "_settlement_date_sort": settlement_date_value if settlement_date_value != "-" else "",
                }
            )

        sort_key_map = {
            "title_number": "_title_number_sort",
            "installment": "_installment_sort",
            "history": "_history_sort",
            "counterparty": "_counterparty_sort",
            "title_amount": "_title_amount_sort",
            "balance_amount": "_balance_amount_sort",
            "competence_date": "_competence_date_sort",
            "due_date": "_due_date_sort",
            "settlement_date": "_settlement_date_sort",
        }
        reverse = filters.order_direction == "desc"
        sort_key = sort_key_map.get(filters.order_by, "_title_number_sort")
        rows.sort(key=lambda item: item.get(sort_key) or "", reverse=reverse)

        columns = []
        for key, label, enabled in [
            ("title_number", "Nº Título", filters.show_title_number),
            ("counterparty", "Favorecido", filters.show_counterparty),
            ("title_amount", "Valor Título", filters.show_title_amount),
            ("balance_amount", "Valor Saldo", filters.show_balance_amount),
            ("competence_date", "Competência", filters.show_competence_date),
            ("due_date", "Vencimento", filters.show_due_date),
            ("settlement_date", "Dt. da Última Liquid.", filters.show_settlement_date),
        ]:
            if enabled:
                columns.append({"key": key, "label": label})

        total_general = receivable_title_total - payable_title_total
        total_general_net = receivable_open_total + payable_open_total

        return {
            "title": definition["label"],
            "subtitle": definition["description"],
            "summary_cards": [
                {"label": "Quantidade de registros", "value": len(rows), "tone": "neutral"},
                {"label": "Total a receber", "value": FinancialReportService._format_currency(receivable_title_total), "tone": "positive"},
                {"label": "Total líquido a receber", "value": FinancialReportService._format_currency(receivable_open_total), "tone": "positive"},
                {"label": "Total a pagar", "value": FinancialReportService._format_currency(payable_title_total), "tone": "negative"},
                {"label": "Total líquido a pagar", "value": FinancialReportService._format_currency(abs(payable_open_total)), "tone": "negative"},
                {"label": "Total geral", "value": FinancialReportService._format_currency(total_general), "tone": "primary"},
                {"label": "Total geral líquido", "value": FinancialReportService._format_currency(total_general_net), "tone": "primary"},
            ],
            "general_info": [
                {"label": "Competência base", "value": f"{filters.competence_start.isoformat()} até {filters.competence_end.isoformat()}"},
                {"label": "Critério principal", "value": "Agendamento operacional por título e saldo"},
                {"label": "Em aberto / borderô", "value": f"{open_count} / {bordero_count}"},
            ],
            "columns": columns,
            "rows": rows,
            "totals": {
                "count": len(rows),
                "receivable_title_total": FinancialReportService._serialize_money(receivable_title_total),
                "receivable_open_total": FinancialReportService._serialize_money(receivable_open_total),
                "payable_title_total": FinancialReportService._serialize_money(payable_title_total),
                "payable_open_total": FinancialReportService._serialize_money(abs(payable_open_total)),
                "total_general": FinancialReportService._serialize_money(total_general),
                "total_general_net": FinancialReportService._serialize_money(total_general_net),
            },
        }

    @staticmethod
    def _build_bank_statement(company_id: int, filters: FinancialManagementReportFiltersInput) -> Dict[str, Any]:
        definition = FinancialReportService.REPORT_DEFINITIONS[filters.report_type]
        bank_names = FinancialReportService._name_map(FinancialBankAccount, company_id)
        counterparty_names = FinancialReportService._name_map(FinancialCounterparty, company_id)
        settlements = FinancialReportService._settlement_query(company_id, filters).order_by(FinancialSettlement.settlement_date.asc(), FinancialSettlement.id.asc()).all()
        entry_ids = [item.financial_entry_id for item in settlements]
        entries = {}
        if entry_ids:
            for entry in FinancialEntry.query.filter(FinancialEntry.company_id == company_id, FinancialEntry.id.in_(entry_ids), FinancialEntry.deleted_at.is_(None)).all():
                entries[entry.id] = entry

        history_query = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
            FinancialSettlement.settlement_date < filters.period_start,
        )
        if filters.bank_account_id:
            history_query = history_query.filter(FinancialSettlement.bank_account_id == filters.bank_account_id)
        all_entries = {entry.id: entry for entry in FinancialEntry.query.filter(FinancialEntry.company_id == company_id, FinancialEntry.deleted_at.is_(None)).all()}
        balance_base = FinancialDashboardAnalytics.calculate_current_balance(settlements=history_query.all(), entries_by_id=all_entries, as_of_date=filters.period_start)

        running = Decimal(balance_base)
        inflow = Decimal("0")
        outflow = Decimal("0")
        rows: List[Dict[str, Any]] = []
        for settlement in settlements:
            entry = entries.get(settlement.financial_entry_id)
            if not entry:
                continue
            amount = Decimal(settlement.net_amount or 0)
            movement_tone = "positive" if entry.movement_nature == "credit" else "negative"
            if entry.movement_nature == "credit":
                inflow += amount
                running += amount
            else:
                outflow += amount
                running -= amount
            rows.append(
                {
                    "data": settlement.settlement_date.isoformat(),
                    "codigo": settlement.settlement_code,
                    "conta_bancaria": bank_names.get(settlement.bank_account_id, "Não informada"),
                    "lancamento": entry.entry_code,
                    "descricao": entry.description,
                    "favorecido": counterparty_names.get(entry.counterparty_id, "Não informado"),
                    "movimento": "Entrada" if entry.movement_nature == "credit" else "Saída",
                    "movimento_tone": movement_tone,
                    "valor": FinancialReportService._serialize_money(amount),
                    "valor_label": FinancialReportService._format_signed_currency(amount, positive_sign=entry.movement_nature == "credit"),
                    "conciliacao": settlement.reconciliation_status,
                    "conciliacao_label": FinancialReportService._reconciliation_status_label(settlement.reconciliation_status),
                    "conciliacao_tone": FinancialReportService._reconciliation_status_tone(settlement.reconciliation_status),
                    "saldo": FinancialReportService._serialize_money(running),
                    "saldo_label": FinancialReportService._format_currency(running),
                    "saldo_tone": "negative" if running < 0 else "neutral",
                }
            )
        return {
            "title": definition["label"],
            "subtitle": definition["description"],
            "summary_cards": [
                {"label": "Saldo inicial", "value": FinancialReportService._format_currency(balance_base), "tone": "neutral"},
                {"label": "Entradas", "value": FinancialReportService._format_currency(inflow), "tone": "positive"},
                {"label": "Saídas", "value": FinancialReportService._format_currency(outflow), "tone": "negative"},
                {"label": "Saldo final", "value": FinancialReportService._format_currency(running), "tone": "primary" if running >= 0 else "negative"},
            ],
            "general_info": [
                {"label": "Janela analisada", "value": f"{filters.period_start.isoformat()} até {filters.period_end.isoformat()}"},
                {"label": "Recorte", "value": bank_names.get(filters.bank_account_id, "Todas as contas bancárias")},
                {"label": "Movimentos", "value": str(len(rows))},
                {"label": "Somente conciliados", "value": "Sim" if filters.include_reconciled_only else "Não"},
            ],
            "columns": [
                {"key": "data", "label": "Data"},
                {"key": "codigo", "label": "Liquidação"},
                {"key": "conta_bancaria", "label": "Conta bancária"},
                {"key": "lancamento", "label": "Lançamento"},
                {"key": "descricao", "label": "Descrição"},
                {"key": "favorecido", "label": "Favorecido"},
                {"key": "movimento", "label": "Movimento"},
                {"key": "valor", "label": "Valor"},
                {"key": "conciliacao", "label": "Conciliação"},
                {"key": "saldo", "label": "Saldo"},
            ],
            "rows": rows,
            "totals": {
                "opening_balance": FinancialReportService._serialize_money(balance_base),
                "inflow": FinancialReportService._serialize_money(inflow),
                "outflow": FinancialReportService._serialize_money(outflow),
                "closing_balance": FinancialReportService._serialize_money(running),
            },
        }

    @staticmethod
    def _build_income_statement(company_id: int, filters: FinancialManagementReportFiltersInput) -> Dict[str, Any]:
        definition = FinancialReportService.REPORT_DEFINITIONS[filters.report_type]
        chart_accounts = FinancialChartAccount.query.filter(
            FinancialChartAccount.company_id == company_id,
            FinancialChartAccount.deleted_at.is_(None),
        ).all()
        chart_map = {
            item.id: {
                "code": getattr(item, "code", None) or f"CTA-{item.id}",
                "name": item.name,
            }
            for item in chart_accounts
        }
        center_names = FinancialReportService._name_map(FinancialCostCenter, company_id)
        project_names = FinancialReportService._name_map(Project, company_id)

        competence_start = filters.competence_start or filters.period_start
        competence_end = filters.competence_end or filters.period_end
        due_start = filters.due_start
        due_end = filters.due_end
        settlement_start = filters.settlement_start
        settlement_end = filters.settlement_end

        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.competence_date >= competence_start,
            FinancialEntry.competence_date <= competence_end,
        )
        chart_account_ids = FinancialReportService._selected_ids(filters.chart_account_id, filters.chart_account_ids)
        if chart_account_ids:
            query = query.filter(FinancialEntry.chart_account_id.in_(chart_account_ids))
        cost_center_ids = FinancialReportService._selected_ids(filters.cost_center_id, filters.cost_center_ids)
        if cost_center_ids:
            query = query.filter(FinancialEntry.cost_center_id.in_(cost_center_ids))

        allowed_entry_types = []
        if filters.include_receivable:
            allowed_entry_types.append("receivable")
        if filters.include_payable:
            allowed_entry_types.append("payable")
        if filters.include_budget_vs_actual:
            allowed_entry_types.append("forecast")
        if allowed_entry_types:
            query = query.filter(FinancialEntry.entry_type.in_(allowed_entry_types))

        entries = query.order_by(FinancialEntry.chart_account_id.asc(), FinancialEntry.competence_date.asc(), FinancialEntry.id.asc()).all()
        if filters.project_ids:
            entries = [entry for entry in entries if FinancialReportService._entry_matches_projects(entry, filters.project_ids)]

        entry_ids = [entry.id for entry in entries]
        settlement_totals_by_entry: Dict[int, Decimal] = {}
        if entry_ids:
            settlement_query = FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.financial_entry_id.in_(entry_ids),
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            )
            if settlement_start:
                settlement_query = settlement_query.filter(FinancialSettlement.settlement_date >= settlement_start)
            if settlement_end:
                settlement_query = settlement_query.filter(FinancialSettlement.settlement_date <= settlement_end)
            for settlement in settlement_query.all():
                settlement_totals_by_entry.setdefault(settlement.financial_entry_id, Decimal("0"))
                settlement_totals_by_entry[settlement.financial_entry_id] += Decimal(settlement.net_amount or 0)

        grouped: Dict[int, Dict[str, Any]] = {}
        for entry in entries:
            settlement_total = settlement_totals_by_entry.get(entry.id, Decimal("0"))
            is_settled = entry.status == "settled" or settlement_total >= Decimal(entry.original_amount or 0)
            is_open = not is_settled
            if not ((filters.include_settled and is_settled) or (filters.include_open and is_open)):
                continue
            if due_start and ((not entry.due_date) or entry.due_date < due_start):
                continue
            if due_end and ((not entry.due_date) or entry.due_date > due_end):
                continue

            signed_original = Decimal(entry.original_amount or 0) if entry.movement_nature == "credit" else -Decimal(entry.original_amount or 0)
            account = chart_map.get(entry.chart_account_id, {"code": f"CTA-{entry.chart_account_id or 0}", "name": "Sem conta contábil"})
            slot = grouped.setdefault(
                entry.chart_account_id or 0,
                {
                    "codigo": account["code"],
                    "descricao": account["name"],
                    "competencia": Decimal("0"),
                    "vencimento": Decimal("0"),
                    "liquidacao": Decimal("0"),
                    "aberto": Decimal("0"),
                    "liquidado": Decimal("0"),
                    "centros": set(),
                    "projetos": set(),
                    "tipos": set(),
                },
            )
            slot["competencia"] += signed_original
            if entry.due_date:
                slot["vencimento"] += signed_original
            if settlement_total:
                signed_settlement = settlement_total if entry.movement_nature == "credit" else -settlement_total
                slot["liquidacao"] += signed_settlement
            if is_open:
                slot["aberto"] += signed_original
            if is_settled:
                slot["liquidado"] += signed_original
            if entry.cost_center_id:
                slot["centros"].add(center_names.get(entry.cost_center_id, str(entry.cost_center_id)))
            for project_id in FinancialReportService._entry_project_ids(entry):
                if not filters.project_ids or project_id in filters.project_ids:
                    slot["projetos"].add(project_names.get(project_id, str(project_id)))
            if entry.entry_type == "forecast":
                slot["tipos"].add("Orçado")
            elif entry.entry_type == "receivable":
                slot["tipos"].add("Recebimento")
            elif entry.entry_type == "payable":
                slot["tipos"].add("Pagamento")
            else:
                slot["tipos"].add(entry.entry_type)

        grouped_values = list(grouped.values())
        grouped_values.sort(
            key=lambda item: (str(item["codigo"]) if filters.order_by == "code" else str(item["descricao"])).lower(),
            reverse=filters.order_direction == "desc",
        )

        rows = []
        total_comp = Decimal("0")
        total_due = Decimal("0")
        total_set = Decimal("0")
        total_open = Decimal("0")
        total_settled = Decimal("0")
        for item in grouped_values:
            total_comp += item["competencia"]
            total_due += item["vencimento"]
            total_set += item["liquidacao"]
            total_open += item["aberto"]
            total_settled += item["liquidado"]
            rows.append(
                {
                    "codigo": item["codigo"],
                    "descricao": item["descricao"],
                    "competencia": FinancialReportService._serialize_money(item["competencia"]),
                    "vencimento": FinancialReportService._serialize_money(item["vencimento"]),
                    "liquidacao": FinancialReportService._serialize_money(item["liquidacao"]),
                    "aberto": FinancialReportService._serialize_money(item["aberto"]),
                    "liquidado": FinancialReportService._serialize_money(item["liquidado"]),
                    "centros": ", ".join(sorted(item["centros"])) or "Todos",
                    "projetos": ", ".join(sorted(item["projetos"])) or "Todos",
                    "tipos": ", ".join(sorted(item["tipos"])) or "N/D",
                }
            )

        columns: List[Dict[str, str]] = []
        if filters.show_code:
            columns.append({"key": "codigo", "label": "Código"})
        if filters.show_description:
            columns.append({"key": "descricao", "label": "Descrição"})
        columns.extend(
            [
                {"key": "competencia", "label": "Competência"},
                {"key": "vencimento", "label": "Vencimento"},
                {"key": "liquidacao", "label": "Liquidação"},
                {"key": "aberto", "label": "Em aberto"},
                {"key": "liquidado", "label": "Liquidado"},
                {"key": "centros", "label": "Centros de resultado"},
                {"key": "projetos", "label": "Projetos"},
                {"key": "tipos", "label": "Tipos"},
            ]
        )

        due_window = f"{due_start.isoformat()} até {due_end.isoformat()}" if due_start and due_end else "Livre"
        settlement_window = f"{settlement_start.isoformat()} até {settlement_end.isoformat()}" if settlement_start and settlement_end else "Livre"
        return {
            "title": definition["label"],
            "subtitle": definition["description"],
            "summary_cards": [
                {"label": "Resultado competência", "value": FinancialReportService._format_currency(total_comp)},
                {"label": "Resultado vencimento", "value": FinancialReportService._format_currency(total_due)},
                {"label": "Resultado liquidação", "value": FinancialReportService._format_currency(total_set)},
                {"label": "Linhas da DRE", "value": len(rows)},
            ],
            "general_info": [
                {"label": "Competência", "value": f"{competence_start.isoformat()} até {competence_end.isoformat()}"},
                {"label": "Vencimento", "value": due_window},
                {"label": "Baixa", "value": settlement_window},
                {"label": "Ordenação", "value": f"{filters.order_by} / {filters.order_direction}"},
                {"label": "Orientação PDF", "value": "Paisagem" if filters.orientation == "landscape" else "Retrato"},
            ],
            "columns": columns,
            "rows": rows,
            "totals": {
                "competence": FinancialReportService._serialize_money(total_comp),
                "due": FinancialReportService._serialize_money(total_due),
                "liquidation": FinancialReportService._serialize_money(total_set),
                "open": FinancialReportService._serialize_money(total_open),
                "settled": FinancialReportService._serialize_money(total_settled),
            },
            "orientation": filters.orientation,
        }

    @staticmethod
    def _build_cash_flow(company_id: int, filters: FinancialManagementReportFiltersInput) -> Dict[str, Any]:
        definition = FinancialReportService.REPORT_DEFINITIONS[filters.report_type]
        bank_names = FinancialReportService._name_map(FinancialBankAccount, company_id)
        bank_account_ids = FinancialReportService._selected_ids(filters.bank_account_id, filters.bank_account_ids)
        settlements = FinancialReportService._settlement_query(company_id, filters).order_by(FinancialSettlement.settlement_date.asc(), FinancialSettlement.id.asc()).all()
        entries = {item.id: item for item in FinancialEntry.query.filter(FinancialEntry.company_id == company_id, FinancialEntry.deleted_at.is_(None)).all()}

        history_query = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
            FinancialSettlement.settlement_date < filters.period_start,
        )
        if bank_account_ids:
            history_query = history_query.filter(FinancialSettlement.bank_account_id.in_(bank_account_ids))
        initial_balance = FinancialDashboardAnalytics.calculate_current_balance(settlements=history_query.all(), entries_by_id=entries, as_of_date=filters.period_start)

        daily: Dict[str, Dict[str, Decimal]] = {}
        realized_in = Decimal("0")
        realized_out = Decimal("0")
        for settlement in settlements:
            entry = entries.get(settlement.financial_entry_id)
            if not entry:
                continue
            slot = daily.setdefault(settlement.settlement_date.isoformat(), {"realized_in": Decimal("0"), "realized_out": Decimal("0"), "projected_in": Decimal("0"), "projected_out": Decimal("0")})
            amount = Decimal(settlement.net_amount or 0)
            if entry.movement_nature == "credit":
                slot["realized_in"] += amount
                realized_in += amount
            else:
                slot["realized_out"] += amount
                realized_out += amount

        if filters.include_projected:
            projected_entries = FinancialEntry.query.filter(
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
                FinancialEntry.status.in_(["draft", "pending_review", "scheduled", "posted", "partially_settled"]),
                FinancialEntry.due_date >= filters.period_start,
                FinancialEntry.due_date <= filters.period_end,
            )
            if bank_account_ids:
                projected_entries = projected_entries.filter(FinancialEntry.bank_account_id.in_(bank_account_ids))
            if filters.cost_center_id:
                projected_entries = projected_entries.filter(FinancialEntry.cost_center_id == filters.cost_center_id)
            settled_ids = {item.financial_entry_id for item in settlements}
            for entry in projected_entries.all():
                if entry.id in settled_ids or not entry.due_date:
                    continue
                slot = daily.setdefault(entry.due_date.isoformat(), {"realized_in": Decimal("0"), "realized_out": Decimal("0"), "projected_in": Decimal("0"), "projected_out": Decimal("0")})
                amount = Decimal(entry.original_amount or 0)
                if entry.movement_nature == "credit":
                    slot["projected_in"] += amount
                else:
                    slot["projected_out"] += amount

        bucket_mode = (filters.frequency or "daily").lower()

        def _bucket_label(current_day: str) -> str:
            current = date.fromisoformat(current_day)
            if bucket_mode == "weekly":
                iso_year, iso_week, _ = current.isocalendar()
                return f"{iso_year}-W{iso_week:02d}"
            if bucket_mode == "monthly":
                return current.strftime("%Y-%m")
            return current_day

        aggregated: Dict[str, Dict[str, Decimal]] = {}
        for day in sorted(daily.keys()):
            label = _bucket_label(day)
            bucket = aggregated.setdefault(
                label,
                {"realized_in": Decimal("0"), "realized_out": Decimal("0"), "projected_in": Decimal("0"), "projected_out": Decimal("0")},
            )
            bucket["realized_in"] += daily[day]["realized_in"]
            bucket["realized_out"] += daily[day]["realized_out"]
            bucket["projected_in"] += daily[day]["projected_in"]
            bucket["projected_out"] += daily[day]["projected_out"]

        running = Decimal(initial_balance)
        rows: List[Dict[str, Any]] = []
        for bucket_label in sorted(aggregated.keys()):
            slot = aggregated[bucket_label]
            opening = running
            running = opening + slot["realized_in"] - slot["realized_out"]
            projected_final = running + slot["projected_in"] - slot["projected_out"]
            rows.append(
                {
                    "data": bucket_label,
                    "saldo_inicial": FinancialReportService._serialize_money(opening),
                    "entrada_realizada": FinancialReportService._serialize_money(slot["realized_in"]),
                    "saida_realizada": FinancialReportService._serialize_money(slot["realized_out"]),
                    "entrada_projetada": FinancialReportService._serialize_money(slot["projected_in"]),
                    "saida_projetada": FinancialReportService._serialize_money(slot["projected_out"]),
                    "saldo_final": FinancialReportService._serialize_money(running),
                    "saldo_projetado": FinancialReportService._serialize_money(projected_final),
                }
            )
        projected_final_value = rows[-1]["saldo_projetado"] if rows else FinancialReportService._serialize_money(initial_balance)
        return {
            "title": definition["label"],
            "subtitle": definition["description"],
            "summary_cards": [
                {"label": "Saldo inicial", "value": FinancialReportService._format_currency(initial_balance)},
                {"label": "Entradas realizadas", "value": FinancialReportService._format_currency(realized_in)},
                {"label": "Saídas realizadas", "value": FinancialReportService._format_currency(realized_out)},
                {"label": "Saldo projetado final", "value": FinancialReportService._format_currency(projected_final_value)},
            ],
            "general_info": [
                {"label": "Janela analisada", "value": f"{filters.period_start.isoformat()} até {filters.period_end.isoformat()}"},
                {"label": "Contas correntes", "value": ", ".join(bank_names.get(item, str(item)) for item in bank_account_ids) if bank_account_ids else "Todas"},
                {"label": "Periodicidade", "value": {"daily": "Diário", "weekly": "Semanal", "monthly": "Mensal"}.get(bucket_mode, bucket_mode)},
                {"label": "Projeções abertas", "value": "Sim" if filters.include_projected else "Não"},
            ],
            "columns": [
                {"key": "data", "label": "Data"},
                {"key": "saldo_inicial", "label": "Saldo inicial"},
                {"key": "entrada_realizada", "label": "Entrada realizada"},
                {"key": "saida_realizada", "label": "Saída realizada"},
                {"key": "entrada_projetada", "label": "Entrada projetada"},
                {"key": "saida_projetada", "label": "Saída projetada"},
                {"key": "saldo_final", "label": "Saldo final"},
                {"key": "saldo_projetado", "label": "Saldo projetado"},
            ],
            "rows": rows,
            "totals": {"opening_balance": FinancialReportService._serialize_money(initial_balance), "realized_inflow": FinancialReportService._serialize_money(realized_in), "realized_outflow": FinancialReportService._serialize_money(realized_out), "projected_final": FinancialReportService._serialize_money(projected_final_value)},
        }

    @staticmethod
    def _build_ledger(company_id: int, filters: FinancialManagementReportFiltersInput) -> Dict[str, Any]:
        definition = FinancialReportService.REPORT_DEFINITIONS[filters.report_type]
        chart_names = FinancialReportService._name_map(FinancialChartAccount, company_id)
        center_names = FinancialReportService._name_map(FinancialCostCenter, company_id)
        project_names = FinancialReportService._name_map(Project, company_id)
        competence_start = filters.competence_start or filters.period_start
        competence_end = filters.competence_end or filters.period_end
        due_start = filters.due_start
        due_end = filters.due_end
        settlement_start = filters.settlement_start
        settlement_end = filters.settlement_end

        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.competence_date >= competence_start,
            FinancialEntry.competence_date <= competence_end,
        )
        chart_account_ids = FinancialReportService._selected_ids(filters.chart_account_id, filters.chart_account_ids)
        if chart_account_ids:
            query = query.filter(FinancialEntry.chart_account_id.in_(chart_account_ids))
        cost_center_ids = FinancialReportService._selected_ids(filters.cost_center_id, filters.cost_center_ids)
        if cost_center_ids:
            query = query.filter(FinancialEntry.cost_center_id.in_(cost_center_ids))
        entries = query.order_by(FinancialEntry.competence_date.asc(), FinancialEntry.id.asc()).all()
        if filters.project_ids:
            entries = [entry for entry in entries if FinancialReportService._entry_matches_projects(entry, filters.project_ids)]
        entry_ids = [entry.id for entry in entries]
        settlements_by_entry: Dict[int, Decimal] = {}
        if entry_ids:
            settlement_query = FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.financial_entry_id.in_(entry_ids),
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            )
            if settlement_start:
                settlement_query = settlement_query.filter(FinancialSettlement.settlement_date >= settlement_start)
            if settlement_end:
                settlement_query = settlement_query.filter(FinancialSettlement.settlement_date <= settlement_end)
            for settlement in settlement_query.all():
                settlements_by_entry.setdefault(settlement.financial_entry_id, Decimal("0"))
                settlements_by_entry[settlement.financial_entry_id] += Decimal(settlement.net_amount or 0)

        debit_total = Decimal("0")
        credit_total = Decimal("0")
        running = Decimal("0")
        rows = []
        for entry in entries:
            if due_start and ((not entry.due_date) or entry.due_date < due_start):
                continue
            if due_end and ((not entry.due_date) or entry.due_date > due_end):
                continue
            settled_amount = settlements_by_entry.get(entry.id, Decimal("0"))
            if entry.status == "settled":
                status_bucket = "Liquidado"
            elif settled_amount > 0:
                status_bucket = "Liquidado Parcial"
            else:
                status_bucket = "Aberto"
            if status_bucket == "Liquidado" and not filters.include_settled:
                continue
            if status_bucket == "Liquidado Parcial" and not filters.include_budget_vs_actual:
                continue
            if status_bucket == "Aberto" and not filters.include_open:
                continue
            debit = Decimal(entry.original_amount or 0) if entry.movement_nature == "debit" else Decimal("0")
            credit = Decimal(entry.original_amount or 0) if entry.movement_nature == "credit" else Decimal("0")
            debit_total += debit
            credit_total += credit
            running += credit - debit
            project_labels = [project_names.get(pid, str(pid)) for pid in FinancialReportService._entry_project_ids(entry)]
            rows.append(
                {
                    "data": entry.competence_date.isoformat() if entry.competence_date else "-",
                    "codigo": entry.entry_code,
                    "conta": chart_names.get(entry.chart_account_id, "Sem conta contábil"),
                    "centro_resultado": center_names.get(entry.cost_center_id, "Não informado"),
                    "projeto": ", ".join(project_labels) or "Não informado",
                    "descricao": entry.description,
                    "debito": FinancialReportService._serialize_money(debit),
                    "credito": FinancialReportService._serialize_money(credit),
                    "liquidado": FinancialReportService._serialize_money(settled_amount),
                    "status": status_bucket,
                    "saldo": FinancialReportService._serialize_money(running),
                }
            )
        grouped_sort_key = filters.order_by
        reverse = filters.order_direction == "desc"
        sort_key_map = {
            "code": lambda item: str(item["conta"]).lower(),
            "description": lambda item: str(item["centro_resultado"]).lower(),
            "project": lambda item: str(item["projeto"]).lower(),
        }
        rows.sort(key=sort_key_map.get(grouped_sort_key, sort_key_map["code"]), reverse=reverse)
        return {
            "title": definition["label"],
            "subtitle": definition["description"],
            "summary_cards": [
                {"label": "Total débito", "value": FinancialReportService._format_currency(debit_total)},
                {"label": "Total crédito", "value": FinancialReportService._format_currency(credit_total)},
                {"label": "Saldo líquido", "value": FinancialReportService._format_currency(running)},
                {"label": "Movimentos", "value": len(rows)},
            ],
            "general_info": [
                {"label": "Competência", "value": f"{competence_start.isoformat()} até {competence_end.isoformat()}"},
                {"label": "Vencimento", "value": f"{due_start.isoformat()} até {due_end.isoformat()}" if due_start and due_end else "Livre"},
                {"label": "Baixa", "value": f"{settlement_start.isoformat()} até {settlement_end.isoformat()}" if settlement_start and settlement_end else "Livre"},
                {"label": "Ordenar por", "value": {"code": "Plano de Conta", "description": "Centro de Resultado", "project": "Projeto"}.get(filters.order_by, filters.order_by)},
                {"label": "Orientação PDF", "value": "Paisagem" if filters.orientation == "landscape" else "Retrato"},
            ],
            "columns": [
                {"key": "data", "label": "Data"},
                {"key": "codigo", "label": "Lançamento"},
                {"key": "conta", "label": "Conta"},
                {"key": "centro_resultado", "label": "Centro de Resultado"},
                {"key": "projeto", "label": "Projeto"},
                {"key": "descricao", "label": "Descrição"},
                {"key": "debito", "label": "Débito"},
                {"key": "credito", "label": "Crédito"},
                {"key": "liquidado", "label": "Liquidado"},
                {"key": "status", "label": "Status"},
                {"key": "saldo", "label": "Saldo acumulado"},
            ],
            "rows": rows,
            "totals": {"debit": FinancialReportService._serialize_money(debit_total), "credit": FinancialReportService._serialize_money(credit_total), "net": FinancialReportService._serialize_money(running)},
            "orientation": filters.orientation,
        }

    @staticmethod
    def _build_working_capital(company_id: int, filters: FinancialManagementReportFiltersInput) -> Dict[str, Any]:
        definition = FinancialReportService.REPORT_DEFINITIONS[filters.report_type]
        reference_date = filters.reference_date or filters.period_end
        working_capital_accounts = FinancialReportService._get_working_capital_accounts(company_id)
        entries_by_id = {entry.id: entry for entry in FinancialEntry.query.filter(FinancialEntry.company_id == company_id, FinancialEntry.deleted_at.is_(None)).all()}
        settlement_query = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
            FinancialSettlement.settlement_date <= reference_date,
        )
        bank_account_ids = FinancialReportService._selected_ids(filters.bank_account_id, filters.bank_account_ids)
        if bank_account_ids:
            settlement_query = settlement_query.filter(FinancialSettlement.bank_account_id.in_(bank_account_ids))
        bank_balance = FinancialDashboardAnalytics.calculate_current_balance(settlements=settlement_query.all(), entries_by_id=entries_by_id, as_of_date=reference_date)
        open_entries = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.status.in_(["draft", "pending_review", "scheduled", "posted", "partially_settled"]),
            FinancialEntry.due_date.isnot(None),
        )
        if bank_account_ids:
            open_entries = open_entries.filter(FinancialEntry.bank_account_id.in_(bank_account_ids))
        if filters.cost_center_id:
            open_entries = open_entries.filter(FinancialEntry.cost_center_id == filters.cost_center_id)
        global_chart_account_ids = set(FinancialReportService._selected_ids(filters.chart_account_id, filters.chart_account_ids))
        if global_chart_account_ids:
            open_entries = open_entries.filter(FinancialEntry.chart_account_id.in_(list(global_chart_account_ids)))
        open_entries = open_entries.order_by(FinancialEntry.due_date.asc(), FinancialEntry.id.asc()).all()
        chart_names = FinancialReportService._name_map(FinancialChartAccount, company_id)
        overdraft = FinancialDashboardAnalytics.calculate_overdraft_limit(company_id) if filters.include_overdraft else Decimal("0")

        def _entry_label(entry: FinancialEntry) -> str:
            return f"{chart_names.get(entry.chart_account_id, entry.description or 'Sem conta')} · {entry.description}"

        def _is_due(entry: FinancialEntry) -> bool:
            return bool(entry.due_date and entry.due_date >= reference_date)

        def _is_overdue(entry: FinancialEntry) -> bool:
            return bool(entry.due_date and entry.due_date < reference_date)

        def _classify_bucket(entry: FinancialEntry) -> str:
            label = f"{chart_names.get(entry.chart_account_id, '')} {entry.description or ''}".lower()
            if any(token in label for token in ["fornecedor", "compra", "mercadoria"]):
                return "supplier"
            if any(token in label for token in ["salário", "funcion", "folha", "colaborador"]):
                return "people"
            if any(token in label for token in ["imposto", "tribut", "taxa", "fiscal"]):
                return "tax"
            if any(token in label for token in ["emprést", "financi", "banco", "finame"]):
                return "financing"
            if any(token in label for token in ["invest", "aplica", "contrato"]):
                return "investment"
            return "generic"

        def _sum_entries(predicate) -> tuple[Decimal, list[str]]:
            total = Decimal("0")
            labels: list[str] = []
            for entry in open_entries:
                if predicate(entry):
                    total += Decimal(entry.original_amount or 0)
                    labels.append(_entry_label(entry))
            return total, labels

        receivables_due_180, receivables_due_180_labels = _sum_entries(lambda e: e.movement_nature == "credit" and _is_due(e) and (e.due_date - reference_date).days <= 180)
        receivables_overdue, receivables_overdue_labels = _sum_entries(lambda e: e.movement_nature == "credit" and _is_overdue(e))
        payable_supplier_due, payable_supplier_due_labels = _sum_entries(lambda e: e.movement_nature == "debit" and _classify_bucket(e) == "supplier" and _is_due(e))
        payable_supplier_overdue, payable_supplier_overdue_labels = _sum_entries(lambda e: e.movement_nature == "debit" and _classify_bucket(e) == "supplier" and _is_overdue(e))
        payable_people_due, payable_people_due_labels = _sum_entries(lambda e: e.movement_nature == "debit" and _classify_bucket(e) == "people" and _is_due(e))
        payable_people_overdue, payable_people_overdue_labels = _sum_entries(lambda e: e.movement_nature == "debit" and _classify_bucket(e) == "people" and _is_overdue(e))
        payable_tax_due, payable_tax_due_labels = _sum_entries(lambda e: e.movement_nature == "debit" and _classify_bucket(e) == "tax" and _is_due(e))
        payable_tax_overdue, payable_tax_overdue_labels = _sum_entries(lambda e: e.movement_nature == "debit" and _classify_bucket(e) == "tax" and _is_overdue(e))
        payable_financing_due, payable_financing_due_labels = _sum_entries(lambda e: e.movement_nature == "debit" and _classify_bucket(e) == "financing" and _is_due(e))
        payable_financing_overdue, payable_financing_overdue_labels = _sum_entries(lambda e: e.movement_nature == "debit" and _classify_bucket(e) == "financing" and _is_overdue(e))
        receivable_investment_due, receivable_investment_due_labels = _sum_entries(lambda e: e.movement_nature == "credit" and _classify_bucket(e) == "investment" and _is_due(e))
        receivable_investment_overdue, receivable_investment_overdue_labels = _sum_entries(lambda e: e.movement_nature == "credit" and _classify_bucket(e) == "investment" and _is_overdue(e))

        computed_accounts = {
            "bank_balance": (Decimal(bank_balance), []),
            "receivable_due_180": (receivables_due_180, receivables_due_180_labels),
            "receivable_overdue": (receivables_overdue, receivables_overdue_labels),
            "payable_supplier_due": (payable_supplier_due, payable_supplier_due_labels),
            "payable_supplier_overdue": (payable_supplier_overdue, payable_supplier_overdue_labels),
            "payable_people_due": (payable_people_due, payable_people_due_labels),
            "payable_people_overdue": (payable_people_overdue, payable_people_overdue_labels),
            "payable_tax_due": (payable_tax_due, payable_tax_due_labels),
            "payable_tax_overdue": (payable_tax_overdue, payable_tax_overdue_labels),
            "payable_financing_due": (payable_financing_due, payable_financing_due_labels),
            "payable_financing_overdue": (payable_financing_overdue, payable_financing_overdue_labels),
            "receivable_investment_due": (receivable_investment_due, receivable_investment_due_labels),
            "receivable_investment_overdue": (receivable_investment_overdue, receivable_investment_overdue_labels),
        }

        def _calculate_bank_balance_for_ids(selected_bank_ids: Sequence[int]) -> Decimal:
            ids = [int(item) for item in selected_bank_ids if item]
            if not ids:
                return Decimal("0")
            scoped_query = FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
                FinancialSettlement.settlement_date <= reference_date,
                FinancialSettlement.bank_account_id.in_(ids),
            )
            return Decimal(
                FinancialDashboardAnalytics.calculate_current_balance(
                    settlements=scoped_query.all(),
                    entries_by_id=entries_by_id,
                    as_of_date=reference_date,
                )
            )

        def _calculate_due_date_account(config: Dict[str, Any]) -> tuple[Decimal, list[str]]:
            metadata = dict(config.get("metadata_json") or {})
            chart_account_ids = {int(item) for item in metadata.get("chart_account_ids") or [] if item}
            if global_chart_account_ids:
                chart_account_ids = chart_account_ids.intersection(global_chart_account_ids) if chart_account_ids else set(global_chart_account_ids)
            if not chart_account_ids:
                return Decimal("0"), []

            patrimonial_type = str(metadata.get("patrimonial_type") or "asset").strip().lower()
            expected_nature = "debit" if patrimonial_type == "liability" else "credit"
            due_scope = str(metadata.get("due_scope") or "overdue").strip().lower()
            due_in_days = metadata.get("due_in_days")

            def _matches_scope(entry: FinancialEntry) -> bool:
                if entry.chart_account_id not in chart_account_ids:
                    return False
                if entry.movement_nature != expected_nature:
                    return False
                if not entry.due_date:
                    return False
                if due_scope == "all_future":
                    return entry.due_date >= reference_date
                if due_scope == "due_in_days":
                    if entry.due_date < reference_date:
                        return False
                    if due_in_days in (None, ""):
                        return True
                    return (entry.due_date - reference_date).days <= int(due_in_days)
                return entry.due_date < reference_date

            total = Decimal("0")
            labels: list[str] = []
            for entry in open_entries:
                if _matches_scope(entry):
                    total += Decimal(entry.original_amount or 0)
                    labels.append(_entry_label(entry))
            return total, labels

        selected_ids = set(filters.working_capital_accounts or [item["id"] for item in working_capital_accounts])
        detail_rows = []
        current_assets = Decimal("0")
        current_liabilities = Decimal("0")
        for config in working_capital_accounts:
            if config["id"] not in selected_ids:
                continue
            metadata = dict(config.get("metadata_json") or {})
            config_mode = str(config.get("config_mode") or config.get("rule") or "").strip().lower()
            if metadata:
                if config_mode == "bank_balances":
                    configured_bank_ids = [int(item) for item in metadata.get("bank_account_ids") or [] if item]
                    if bank_account_ids and configured_bank_ids:
                        effective_bank_ids = [item for item in configured_bank_ids if item in set(bank_account_ids)]
                    else:
                        effective_bank_ids = configured_bank_ids or list(bank_account_ids)
                    amount = _calculate_bank_balance_for_ids(effective_bank_ids)
                    labels = ["Contas bancárias selecionadas"] if effective_bank_ids else []
                elif config_mode == "manual_value":
                    amount = Decimal(filters.manual_values.get(config["id"], 0) or 0)
                    labels = ["Valor informado na emissão"] if amount else []
                else:
                    amount, labels = _calculate_due_date_account(config)
            else:
                amount, labels = computed_accounts.get(config["rule"], (Decimal("0"), []))
            signal = Decimal("1") if config["type"] == "Ativo" else Decimal("-1")
            if config["type"] == "Ativo":
                current_assets += amount
            elif config["type"] == "Passivo":
                current_liabilities += amount
            detail_rows.append(
                {
                    "id": config["id"],
                    "descricao": config["description"],
                    "tipo": config["type"],
                    "classe": config["class_name"],
                    "categoria": config["category"],
                    "valor_data": config.get("value_label") or ("Saldo em conta" if config["rule"] == "bank_balance" else ("Vencidas" if "overdue" in config["rule"] else "Todas à vencer" if "payable" in config["rule"] or "investment" in config["rule"] else "À vencer em 180 dias.")),
                    "valor": FinancialReportService._serialize_money(amount * signal if config["type"] == "Passivo" else amount),
                    "base_calculo": ", ".join(labels[:5]) if labels else ("Contas bancárias selecionadas" if config_mode == "bank_balances" or config.get("rule") == "bank_balance" else "Valor não informado para esta emissão" if config_mode == "manual_value" else "Sem títulos para a regra"),
                }
            )

        working_capital = current_assets - current_liabilities
        adjusted_liquidity = working_capital + overdraft
        liquidity_ratio = (current_assets / current_liabilities) if current_liabilities else Decimal("0")
        return {
            "title": definition["label"],
            "subtitle": definition["description"],
            "summary_cards": [
                {"label": "Ativo circulante", "value": FinancialReportService._format_currency(current_assets)},
                {"label": "Passivo circulante", "value": FinancialReportService._format_currency(current_liabilities)},
                {"label": "CCL", "value": FinancialReportService._format_currency(working_capital)},
                {"label": "Índice de liquidez", "value": f"{float(liquidity_ratio):.2f}" if current_liabilities else "N/A"},
            ],
            "general_info": [
                {"label": "Posição base", "value": reference_date.isoformat()},
                {"label": "Contas programadas", "value": len(detail_rows)},
                {"label": "Considera limites", "value": "Sim" if filters.include_overdraft else "Não"},
            ],
            "columns": [
                {"key": "id", "label": "ID"},
                {"key": "descricao", "label": "Descrição"},
                {"key": "tipo", "label": "Tipo"},
                {"key": "classe", "label": "Classe"},
                {"key": "categoria", "label": "Categoria"},
                {"key": "valor_data", "label": "Valor/Data"},
                {"key": "valor", "label": "Valor"},
                {"key": "base_calculo", "label": "Base de cálculo"},
            ],
            "rows": detail_rows,
            "totals": {"current_assets": FinancialReportService._serialize_money(current_assets), "current_liabilities": FinancialReportService._serialize_money(current_liabilities), "working_capital": FinancialReportService._serialize_money(working_capital), "adjusted_liquidity": FinancialReportService._serialize_money(adjusted_liquidity)},
        }

    @staticmethod
    def _build_filter_labels(
        filters: FinancialManagementReportFiltersInput,
        company_id: int,
        raw_filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        bank_names = FinancialReportService._name_map(FinancialBankAccount, company_id)
        chart_names = FinancialReportService._name_map(FinancialChartAccount, company_id)
        center_names = FinancialReportService._name_map(FinancialCostCenter, company_id)
        counterparty_names = FinancialReportService._name_map(FinancialCounterparty, company_id)
        project_names = FinancialReportService._name_map(Project, company_id)
        process_names = FinancialReportService._name_map(Process, company_id)
        raw_filters = raw_filters or {}
        order_labels = {
            "code": "Código",
            "description": "Descrição",
            "project": "Projeto",
            "title_number": "Nº Título",
            "installment": "Parcela",
            "history": "Histórico",
            "counterparty": "Favorecido",
            "title_amount": "Valor Título",
            "balance_amount": "Valor Saldo",
            "competence_date": "Competência",
            "due_date": "Vencimento",
            "settlement_date": "Dt. da Última Liquid.",
        }
        default_start, default_end = FinancialReportService.default_period()
        values: List[Dict[str, str]] = []
        if filters.report_type != "schedule_report":
            values.extend(
                [
                    {"label": "Período inicial", "value": filters.period_start.isoformat()},
                    {"label": "Período final", "value": filters.period_end.isoformat()},
                ]
            )
        if filters.report_type == "schedule_report":
            competence_explicit = (
                "competence_start" in raw_filters
                or "competence_end" in raw_filters
            )
            default_competence = (
                filters.competence_start == default_start
                and filters.competence_end == default_end
            )
            if filters.competence_start and filters.competence_end and (competence_explicit or not default_competence):
                values.append({"label": "Data competência", "value": f"{filters.competence_start.isoformat()} até {filters.competence_end.isoformat()}"})
        elif filters.competence_start and filters.competence_end:
            values.append({"label": "Data competência", "value": f"{filters.competence_start.isoformat()} até {filters.competence_end.isoformat()}"})
        if filters.due_start and filters.due_end and ("due_start" in raw_filters or "due_end" in raw_filters or filters.report_type != "schedule_report"):
            values.append({"label": "Data vencimento", "value": f"{filters.due_start.isoformat()} até {filters.due_end.isoformat()}"})
        if filters.settlement_start and filters.settlement_end and ("settlement_start" in raw_filters or "settlement_end" in raw_filters or filters.report_type != "schedule_report"):
            values.append({"label": "Data baixa", "value": f"{filters.settlement_start.isoformat()} até {filters.settlement_end.isoformat()}"})
        if filters.reference_date and filters.report_type != "schedule_report":
            values.append({"label": "Data de referência", "value": filters.reference_date.isoformat()})
        for current, label, names in [
            (filters.bank_account_id, "Conta bancária", bank_names),
            (filters.chart_account_id, "Conta contábil", chart_names),
            (filters.cost_center_id, "Centro de resultados", center_names),
        ]:
            if current:
                values.append({"label": label, "value": names.get(current, str(current))})
        if filters.bank_account_ids:
            values.append({"label": "Contas correntes", "value": ", ".join(bank_names.get(item, str(item)) for item in filters.bank_account_ids)})
        if filters.chart_account_ids:
            values.append({"label": "Planos de conta", "value": ", ".join(chart_names.get(item, str(item)) for item in filters.chart_account_ids)})
        if filters.cost_center_ids:
            values.append({"label": "Centros de resultado", "value": ", ".join(center_names.get(item, str(item)) for item in filters.cost_center_ids)})
        counterparty_ids = FinancialReportService._selected_ids(filters.counterparty_id, filters.counterparty_ids)
        if counterparty_ids:
            values.append({"label": "Favorecidos", "value": ", ".join(counterparty_names.get(item, str(item)) for item in counterparty_ids)})
        if filters.process_ids:
            values.append({"label": "Processos", "value": ", ".join(process_names.get(item, str(item)) for item in filters.process_ids)})
        if filters.project_ids:
            values.append({"label": "Projetos", "value": ", ".join(project_names.get(item, str(item)) for item in filters.project_ids)})
        if filters.working_capital_accounts:
            selected_map = {item["id"]: item for item in FinancialReportService._get_working_capital_accounts(company_id)}
            selected = [selected_map[item_id] for item_id in filters.working_capital_accounts if item_id in selected_map]
            values.append({"label": "Contas patrimoniais", "value": ", ".join(item["description"] for item in selected)})
        if filters.manual_values:
            manual_labels = []
            account_map = {item["id"]: item for item in FinancialReportService._get_working_capital_accounts(company_id)}
            for account_id, value in filters.manual_values.items():
                account = account_map.get(account_id)
                if not account:
                    continue
                manual_labels.append(f"{account['description']}: {FinancialReportService._format_currency(value)}")
            if manual_labels:
                values.append({"label": "Valores digitados", "value": " | ".join(manual_labels)})
        if filters.movement_nature:
            values.append({"label": "Movimento", "value": "Entrada" if filters.movement_nature == "credit" else "Saída"})
        if filters.schedule_status:
            values.append({"label": "Status do agendamento", "value": filters.schedule_status})
        if filters.frequency:
            values.append({"label": "Frequência", "value": filters.frequency})
        if filters.report_type == "schedule_report":
            all_status_enabled = all([filters.include_settled, filters.include_partial, filters.include_open, filters.include_bordero])
            status_explicit = any(
                key in raw_filters
                for key in ("include_settled", "include_partial", "include_open", "include_bordero")
            )
            if status_explicit or not all_status_enabled:
                values.append({
                    "label": "Status",
                    "value": ", ".join(
                        [
                            label for enabled, label in [
                                (filters.include_settled, "Liquidado"),
                                (filters.include_partial, "Liquidado Parcial"),
                                (filters.include_open, "Aberto"),
                                (filters.include_bordero, "Borderô"),
                            ] if enabled
                        ]
                    ) or "Nenhum",
                })
            all_types_enabled = all([filters.include_payable, filters.include_receivable])
            type_explicit = any(
                key in raw_filters
                for key in ("include_payable", "include_receivable")
            )
            if type_explicit or not all_types_enabled:
                values.append({
                    "label": "Tipo",
                    "value": ", ".join(
                        [
                            label for enabled, label in [
                                (filters.include_payable, "Pagamento"),
                                (filters.include_receivable, "Recebimento"),
                            ] if enabled
                        ]
                    ) or "Nenhum",
                })
        elif filters.report_type == "bank_statement":
            include_reconciled_explicit = "include_reconciled_only" in raw_filters
            if include_reconciled_explicit or filters.include_reconciled_only:
                values.append({"label": "Somente conciliados", "value": "Sim" if filters.include_reconciled_only else "Não"})
        else:
            values.append({"label": "Projetar abertos", "value": "Sim" if filters.include_projected else "Não"})
            values.append({"label": "Somente conciliados", "value": "Sim" if filters.include_reconciled_only else "Não"})
            values.append({"label": "Considerar limites", "value": "Sim" if filters.include_overdraft else "Não"})
            values.append({"label": "Status considerados", "value": ", ".join([label for enabled, label in [(filters.include_settled, "Liquidado"), (filters.include_open, "Aberto")] if enabled]) or "Nenhum"})
            values.append({"label": "Tipos considerados", "value": ", ".join([label for enabled, label in [(filters.include_receivable, "Recebimento"), (filters.include_payable, "Pagamento"), (filters.include_budget_vs_actual, "Orçado x Realizado")] if enabled]) or "Nenhum"})
            values.append({"label": "Exibir", "value": ", ".join([label for enabled, label in [(filters.show_code, "Código"), (filters.show_description, "Descrição")] if enabled]) or "Nenhum"})
            values.append({"label": "Ordenar por", "value": order_labels.get(filters.order_by, filters.order_by)})
            values.append({"label": "Direção", "value": filters.order_direction})
            values.append({"label": "Orientação", "value": "Paisagem" if filters.orientation == "landscape" else "Retrato"})
        return values

    @staticmethod
    def build_management_report(*, company_id: int, report_type: str, filters: Optional[Dict[str, Any]] = None, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        definition, error = FinancialReportService.get_report_definition_or_error(report_type)
        if error:
            return None, error
        normalized_filters, error = FinancialReportService._normalize_filters(definition["code"], filters)
        if error:
            return None, error
        builder_map = {
            "schedule_report": FinancialReportService._build_schedule_report,
            "bank_statement": FinancialReportService._build_bank_statement,
            "income_statement": FinancialReportService._build_income_statement,
            "cash_flow": FinancialReportService._build_cash_flow,
            "ledger": FinancialReportService._build_ledger,
            "working_capital": FinancialReportService._build_working_capital,
        }
        payload = builder_map[definition["code"]](company_id, normalized_filters)
        payload.update(
            {
                "report_type": definition["code"],
                "report_slug": definition["slug"],
                "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "filters": FinancialReportService._build_filter_labels(normalized_filters, company_id, raw_filters=filters),
                "period_start": normalized_filters.period_start.isoformat(),
                "period_end": normalized_filters.period_end.isoformat(),
                "orientation": normalized_filters.orientation,
                "output_mode": normalized_filters.output_mode,
                "items": payload.get("rows", []),
            }
        )
        return payload, None

    @staticmethod
    def generate_report(*, company_id: int, report_type: str, period_start: str, period_end: str, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return FinancialReportService.build_management_report(
            company_id=company_id,
            report_type=report_type,
            filters={"period_start": period_start, "period_end": period_end},
            allowed_company_ids=allowed_company_ids,
        )

    @staticmethod
    def export_xlsx(report_payload: Dict[str, Any]) -> bytes:
        from openpyxl import Workbook
        from openpyxl.styles import Font

        workbook = Workbook()
        summary_sheet = workbook.active
        summary_sheet.title = "Filtros e resumo"
        summary_sheet["A1"] = report_payload.get("title", "Relatório")
        summary_sheet["A1"].font = Font(bold=True, size=14)
        summary_sheet["A3"] = "Gerado em"
        summary_sheet["B3"] = report_payload.get("generated_at")

        row_cursor = 5
        for section_title, items in [
            ("Filtros", report_payload.get("filters", [])),
            ("Informações gerais", report_payload.get("general_info", [])),
            ("Resumo executivo", report_payload.get("summary_cards", [])),
        ]:
            summary_sheet[f"A{row_cursor}"] = section_title
            summary_sheet[f"A{row_cursor}"].font = Font(bold=True)
            row_cursor += 1
            for item in items:
                summary_sheet[f"A{row_cursor}"] = item.get("label")
                summary_sheet[f"B{row_cursor}"] = item.get("value")
                row_cursor += 1
            row_cursor += 1

        data_sheet = workbook.create_sheet("Dados")
        columns = report_payload.get("columns", [])
        for index, column in enumerate(columns, start=1):
            cell = data_sheet.cell(row=1, column=index, value=column.get("label"))
            cell.font = Font(bold=True)
        for row_index, item in enumerate(report_payload.get("rows", []), start=2):
            for col_index, column in enumerate(columns, start=1):
                data_sheet.cell(row=row_index, column=col_index, value=item.get(column.get("key"), ""))

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_pdf(report_payload: Dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        pagesize = landscape(A4) if report_payload.get("orientation", "landscape") == "landscape" else A4
        doc = SimpleDocTemplate(buffer, pagesize=pagesize, leftMargin=24, rightMargin=24, topMargin=26, bottomMargin=36)
        styles = getSampleStyleSheet()
        available_width = pagesize[0] - doc.leftMargin - doc.rightMargin

        if report_payload.get("report_type") == "schedule_report":
            elements = FinancialReportService._build_schedule_pdf_elements(
                report_payload=report_payload,
                styles=styles,
                available_width=available_width,
            )
            doc.build(
                elements,
                onFirstPage=lambda canvas, current_doc: FinancialReportService._draw_default_pdf_footer(canvas, current_doc, report_payload),
                onLaterPages=lambda canvas, current_doc: FinancialReportService._draw_default_pdf_footer(canvas, current_doc, report_payload),
            )
            buffer.seek(0)
            return buffer.getvalue()

        title_style = ParagraphStyle("FinancialReportTitle", parent=styles["Heading1"], fontSize=18, textColor=colors.HexColor("#0f172a"), spaceAfter=10)
        subtitle_style = ParagraphStyle("FinancialReportSubtitle", parent=styles["BodyText"], fontSize=9, textColor=colors.HexColor("#475569"), spaceAfter=8)

        elements = [
            Paragraph(report_payload.get("title", "Relatório financeiro"), title_style),
            Paragraph(report_payload.get("subtitle", ""), subtitle_style),
            Paragraph(f"Gerado em: {report_payload.get('generated_at', '-')}", subtitle_style),
            Spacer(1, 8),
        ]

        summary_rows = [["Resumo", "Valor"]] + [[item.get("label", ""), str(item.get("value", ""))] for item in report_payload.get("summary_cards", [])]
        summary_table = Table(summary_rows, colWidths=[180, 220])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ]
            )
        )
        elements.extend([summary_table, Spacer(1, 10)])

        columns = [column.get("label", "") for column in report_payload.get("columns", [])]
        rows = [[str(item.get(column.get("key"), "")) for column in report_payload.get("columns", [])] for item in report_payload.get("rows", [])]
        if columns:
            data = [columns] + rows
            table = Table(data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8),
                        ("FONTSIZE", (0, 1), (-1, -1), 7),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            elements.append(table)

        doc.build(
            elements,
            onFirstPage=lambda canvas, current_doc: FinancialReportService._draw_default_pdf_footer(canvas, current_doc, report_payload),
            onLaterPages=lambda canvas, current_doc: FinancialReportService._draw_default_pdf_footer(canvas, current_doc, report_payload),
        )
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def _pdf_generated_at_label(report_payload: Dict[str, Any]) -> str:
        generated_at = str(report_payload.get("generated_at") or "-").strip()
        if generated_at == "-":
            return generated_at
        if " às " in generated_at:
            return generated_at
        if " " in generated_at:
            date_part, time_part = generated_at.split(" ", 1)
            return f"{date_part} às {time_part}"
        return generated_at

    @staticmethod
    def _draw_default_pdf_footer(canvas, doc, report_payload: Dict[str, Any]) -> None:
        canvas.saveState()
        width, _ = doc.pagesize
        footer_y = 18
        line_y = footer_y + 10
        canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
        canvas.setLineWidth(0.6)
        canvas.line(doc.leftMargin, line_y, width - doc.rightMargin, line_y)
        canvas.setFillColor(colors.HexColor("#0f172a"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(doc.leftMargin, footer_y, "Versus Gestão Corporativa - Todos os direitos reservados.")
        canvas.drawRightString(
            width - doc.rightMargin,
            footer_y,
            f"Emitido em: {FinancialReportService._pdf_generated_at_label(report_payload)}",
        )
        canvas.restoreState()

    @staticmethod
    def _build_schedule_pdf_elements(*, report_payload: Dict[str, Any], styles, available_width: float) -> List[Any]:
        title_style = ParagraphStyle(
            "SchedulePdfTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=21,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )
        section_title_style = ParagraphStyle(
            "SchedulePdfSectionTitle",
            parent=styles["BodyText"],
            fontSize=10,
            leading=12,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=6,
        )
        filter_cell_style = ParagraphStyle(
            "SchedulePdfFilterCell",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#0f172a"),
        )
        stat_label_style = ParagraphStyle(
            "SchedulePdfStatLabel",
            parent=styles["BodyText"],
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#334155"),
        )
        stat_value_style = ParagraphStyle(
            "SchedulePdfStatValue",
            parent=styles["BodyText"],
            fontSize=11,
            leading=13,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f172a"),
        )
        table_header_style = ParagraphStyle(
            "SchedulePdfTableHeader",
            parent=styles["BodyText"],
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )
        table_cell_style = ParagraphStyle(
            "SchedulePdfTableCell",
            parent=styles["BodyText"],
            fontSize=7,
            leading=8,
            textColor=colors.HexColor("#0f172a"),
        )
        table_cell_center_style = ParagraphStyle(
            "SchedulePdfTableCellCenter",
            parent=table_cell_style,
            alignment=TA_CENTER,
        )
        table_cell_currency_style = ParagraphStyle(
            "SchedulePdfTableCellCurrency",
            parent=table_cell_style,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )

        elements: List[Any] = [
            Paragraph(report_payload.get("title", "Relatório financeiro"), title_style),
            Spacer(1, 8),
        ]

        report_filters = report_payload.get("filters") or []
        elements.append(Paragraph("FILTROS APLICADOS", section_title_style))
        elements.append(
            FinancialReportService._build_schedule_pdf_filter_cards(
                report_filters=report_filters,
                available_width=available_width,
                content_style=filter_cell_style,
            )
        )
        elements.append(Spacer(1, 8))

        report_summary_cards = report_payload.get("summary_cards") or []
        elements.append(
            FinancialReportService._build_schedule_pdf_summary_cards(
                report_summary_cards=report_summary_cards,
                available_width=available_width,
                label_style=stat_label_style,
                value_style=stat_value_style,
            )
        )
        elements.append(Spacer(1, 8))

        report_columns = report_payload.get("columns") or []
        report_rows = report_payload.get("rows") or []
        if report_columns:
            elements.append(
                FinancialReportService._build_schedule_pdf_data_table(
                    report_columns=report_columns,
                    report_rows=report_rows,
                    available_width=available_width,
                    header_style=table_header_style,
                    cell_style=table_cell_style,
                    cell_center_style=table_cell_center_style,
                    cell_currency_style=table_cell_currency_style,
                )
            )
        else:
            empty_style = ParagraphStyle(
                "SchedulePdfEmpty",
                parent=styles["BodyText"],
                fontSize=9,
                leading=11,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#475569"),
            )
            elements.append(Paragraph("Nenhum dado encontrado para os filtros informados.", empty_style))

        return elements

    @staticmethod
    def _build_schedule_pdf_filter_cards(*, report_filters: List[Dict[str, Any]], available_width: float, content_style) -> Table:
        items = report_filters or [{"label": "Resumo", "value": "Sem filtros adicionais."}]
        cols = 3
        gutter = 6
        col_width = (available_width - (gutter * (cols - 1))) / cols
        cells: List[Any] = []
        for item in items:
            label = str(item.get("label") or "").strip()
            value = str(item.get("value") or "-").strip()
            cells.append(Paragraph(f"<b>{label}</b><br/>{value}", content_style))
        while len(cells) % cols != 0:
            cells.append(Paragraph("", content_style))
        matrix = [cells[index:index + cols] for index in range(0, len(cells), cols)]
        table = Table(matrix, colWidths=[col_width] * cols, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#e2e8f0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table

    @staticmethod
    def _build_schedule_pdf_summary_cards(*, report_summary_cards: List[Dict[str, Any]], available_width: float, label_style, value_style) -> Table:
        cards = report_summary_cards or []
        cols = 4
        gutter = 6
        col_width = (available_width - (gutter * (cols - 1))) / cols
        rows: List[List[Any]] = []
        current_row: List[Any] = []
        tone_color_codes = {
            "positive": "#16a34a",
            "negative": "#dc2626",
            "primary": "#2563eb",
            "neutral": "#0f172a",
        }
        for card in cards:
            tone = str(card.get("tone") or "neutral").lower()
            value = Paragraph(
                f"<font color='{tone_color_codes.get(tone, '#0f172a')}'>{card.get('value', '-')}</font>",
                value_style,
            )
            label = Paragraph(str(card.get("label") or "-").upper(), label_style)
            current_row.append(Table([[value], [label]], colWidths=[col_width]))
            if len(current_row) == cols:
                rows.append(current_row)
                current_row = []
        if current_row:
            while len(current_row) < cols:
                current_row.append(Paragraph("", value_style))
            rows.append(current_row)

        table = Table(rows, colWidths=[col_width] * cols, hAlign="LEFT")
        base_styles = [
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for row_index, row in enumerate(rows):
            for col_index, cell in enumerate(row):
                if isinstance(cell, Table):
                    cell.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
                                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
                                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                                ("TOPPADDING", (0, 0), (-1, -1), 6),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ]
                        )
                    )
        table.setStyle(TableStyle(base_styles))
        return table

    @staticmethod
    def _build_schedule_pdf_data_table(
        *,
        report_columns: List[Dict[str, Any]],
        report_rows: List[Dict[str, Any]],
        available_width: float,
        header_style,
        cell_style,
        cell_center_style,
        cell_currency_style,
    ) -> Table:
        width_ratio_map = {
            "title_number": 1.0,
            "counterparty": 1.7,
            "title_amount": 1.0,
            "balance_amount": 1.0,
            "competence_date": 1.0,
            "due_date": 1.0,
            "settlement_date": 1.15,
        }
        total_ratio = sum(width_ratio_map.get(column.get("key"), 1.0) for column in report_columns) or 1.0
        col_widths = [
            available_width * (width_ratio_map.get(column.get("key"), 1.0) / total_ratio)
            for column in report_columns
        ]

        header_row = [Paragraph(str(column.get("label") or ""), header_style) for column in report_columns]
        body_rows: List[List[Any]] = []
        for item in report_rows:
            row_cells: List[Any] = []
            for column in report_columns:
                key = column.get("key")
                raw_value = str(item.get(key, "") or "")
                if key in {"title_amount", "balance_amount"}:
                    style = cell_currency_style
                elif key in {"competence_date", "due_date", "settlement_date"}:
                    style = cell_center_style
                else:
                    style = cell_style
                row_cells.append(Paragraph(raw_value, style))
            body_rows.append(row_cells)

        data = [header_row] + body_rows
        table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
        table_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for row_index in range(1, len(data)):
            background = colors.HexColor("#ffffff") if row_index % 2 else colors.HexColor("#f8fafc")
            table_styles.append(("BACKGROUND", (0, row_index), (-1, row_index), background))
        table.setStyle(TableStyle(table_styles))
        return table
