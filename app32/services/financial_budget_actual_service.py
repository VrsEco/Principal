from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


class FinancialBudgetActualService:
    """Serviço de preparação gerencial para Orçado x Realizado.

    Este serviço nasce sem acoplar UI a query ou rota: primeiro fixa o contrato
    funcional/UX e, na sequência, expõe agregações tenant-safe consumíveis pela
    tela orçamentária e por relatórios executivos.
    """

    DIMENSIONS: tuple[str, ...] = ("chart_account_id", "cost_center_id", "project_id", "process_id")
    PERIOD_VIEWS: tuple[str, ...] = ("period", "competence", "executive")

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal("0.00")

    @staticmethod
    def _float(value: Any) -> float:
        return float(FinancialBudgetActualService._decimal(value))

    @staticmethod
    def _month_key(value: Any) -> Optional[str]:
        """Normaliza datas para a competência mensal AAAA-MM.

        O serviço aceita registros vindos de títulos, baixas e orçamento. Cada
        origem pode entregar `date`, ISO date ou uma competência já normalizada.
        A regra aqui é somente formatação para comparativo; a data-base deve
        continuar sendo decidida na camada de compilação de cada fonte.
        """

        if not value:
            return None
        if isinstance(value, date):
            return value.strftime("%Y-%m")
        text = str(value).strip()
        if not text:
            return None
        if len(text) >= 7 and text[4] == "-":
            return text[:7]
        if len(text) == 6 and text.isdigit():
            return f"{text[:4]}-{text[4:]}"
        return text

    @staticmethod
    def build_workspace_model() -> Dict[str, Any]:
        return {
            "contract_version": "financial_budget_actual_workspace_v1",
            "title": "Orçado x Realizado",
            "subtitle": "Comparativo gerencial entre valores orçados e realizados por período, competência e visão executiva.",
            "dimensions": [
                {"key": "chart_account_id", "label": "Plano de contas", "required": True},
                {"key": "cost_center_id", "label": "Centro de resultado", "required": False},
                {"key": "project_id", "label": "Projeto", "required": False},
                {"key": "process_id", "label": "Processo", "required": False},
            ],
            "measures": [
                {"key": "planned_amount", "label": "Orçado"},
                {"key": "actual_amount", "label": "Realizado"},
                {"key": "variance_amount", "label": "Variação"},
                {"key": "consumption_rate", "label": "% Consumo"},
            ],
            "views": [
                {"key": "period", "label": "Período", "description": "Consolidação pelo intervalo filtrado."},
                {"key": "competence", "label": "Competência", "description": "Apuração por data de competência."},
                {"key": "executive", "label": "Executiva", "description": "Resumo para empresários e gestores."},
            ],
            "ux": {
                "primary_filter": "period",
                "default_grouping": ["chart_account_id", "cost_center_id"],
                "drilldown_order": ["chart_account_id", "cost_center_id", "project_id", "process_id"],
                "empty_state": "Nenhum item orçado ou realizado encontrado para os filtros informados.",
            },
        }

    @staticmethod
    def _dimension_key(record: Mapping[str, Any], dimensions: Sequence[str] | None = None) -> Tuple[Any, ...]:
        selected_dimensions = tuple(dimensions or FinancialBudgetActualService.DIMENSIONS)
        return tuple(record.get(dimension) for dimension in selected_dimensions)

    @staticmethod
    def aggregate_actual_records(
        records: Iterable[Mapping[str, Any]],
        *,
        dimensions: Sequence[str] | None = None,
    ) -> Dict[Tuple[Any, ...], Dict[str, Any]]:
        selected_dimensions = tuple(dimensions or FinancialBudgetActualService.DIMENSIONS)
        grouped: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
        for record in records:
            key = FinancialBudgetActualService._dimension_key(record, selected_dimensions)
            slot = grouped.setdefault(
                key,
                {
                    "dimensions": dict(zip(selected_dimensions, key)),
                    "actual_amount": Decimal("0.00"),
                    "record_count": 0,
                    "sources": set(),
                },
            )
            slot["actual_amount"] += FinancialBudgetActualService._decimal(
                record.get("signed_amount", record.get("actual_amount", record.get("amount")))
            )
            slot["record_count"] += 1
            if record.get("source"):
                slot["sources"].add(str(record.get("source")))

        return {
            key: {
                **value,
                "actual_amount": FinancialBudgetActualService._float(value["actual_amount"]),
                "sources": sorted(value["sources"]),
            }
            for key, value in grouped.items()
        }

    @staticmethod
    def _aggregate_amount_records(
        records: Iterable[Mapping[str, Any]],
        *,
        amount_fields: Sequence[str],
        dimensions: Sequence[str],
        date_field: str | None = None,
        company_id: Any | None = None,
    ) -> Dict[Tuple[Any, ...], Dict[str, Any]]:
        grouped: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
        for record in records:
            if company_id is not None and record.get("company_id") not in (None, company_id):
                raise ValueError("Registro orçamentário/realizado fora do tenant informado.")

            key_values = list(FinancialBudgetActualService._dimension_key(record, dimensions))
            period_key = None
            if date_field:
                period_key = FinancialBudgetActualService._month_key(record.get(date_field))
                key_values.append(period_key)

            key = tuple(key_values)
            amount = Decimal("0.00")
            for field in amount_fields:
                if field in record:
                    amount = FinancialBudgetActualService._decimal(record.get(field))
                    break

            slot = grouped.setdefault(
                key,
                {
                    "dimensions": dict(zip(dimensions, key_values[: len(dimensions)])),
                    "period_key": period_key,
                    "amount": Decimal("0.00"),
                    "record_count": 0,
                    "sources": set(),
                },
            )
            slot["amount"] += amount
            slot["record_count"] += 1
            if record.get("source"):
                slot["sources"].add(str(record.get("source")))
        return grouped

    @staticmethod
    def _status_for(planned: Decimal, actual: Decimal) -> str:
        if planned == Decimal("0.00") and actual != Decimal("0.00"):
            return "no_budget"
        if planned == Decimal("0.00"):
            return "on_track"
        consumption = (actual / planned) * Decimal("100")
        if consumption > Decimal("100"):
            return "overrun"
        if consumption >= Decimal("90"):
            return "attention"
        return "on_track"

    @staticmethod
    def _comparison_row(
        *,
        key: Tuple[Any, ...],
        dimensions: Sequence[str],
        period_key: str | None,
        planned_bucket: Mapping[str, Any] | None,
        actual_bucket: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        planned = (planned_bucket or {}).get("amount", Decimal("0.00"))
        actual = (actual_bucket or {}).get("amount", Decimal("0.00"))
        planned = FinancialBudgetActualService._decimal(planned)
        actual = FinancialBudgetActualService._decimal(actual)
        variance = planned - actual
        consumption_rate = Decimal("0.00")
        if planned != Decimal("0.00"):
            consumption_rate = ((actual / planned) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        dimension_values = dict(zip(dimensions, key[: len(dimensions)]))
        return {
            "dimensions": dimension_values,
            "period_key": period_key,
            "planned_amount": FinancialBudgetActualService._float(planned),
            "actual_amount": FinancialBudgetActualService._float(actual),
            "variance_amount": FinancialBudgetActualService._float(variance),
            "consumption_rate": FinancialBudgetActualService._float(consumption_rate),
            "status": FinancialBudgetActualService._status_for(planned, actual),
            "planned_record_count": int((planned_bucket or {}).get("record_count", 0)),
            "actual_record_count": int((actual_bucket or {}).get("record_count", 0)),
            "sources": {
                "planned": sorted((planned_bucket or {}).get("sources", set())),
                "actual": sorted((actual_bucket or {}).get("sources", set())),
            },
        }

    @staticmethod
    def build_comparison_rows(
        planned_records: Iterable[Mapping[str, Any]],
        actual_records: Iterable[Mapping[str, Any]],
        *,
        view: str = "period",
        dimensions: Sequence[str] | None = None,
        company_id: Any | None = None,
    ) -> List[Dict[str, Any]]:
        """Constrói comparativos por período, competência ou visão executiva.

        - `period`: consolida no intervalo filtrado sem quebrar por mês.
        - `competence`: quebra por mês usando `competence_date`/`competence`.
        - `executive`: consolida como `period`, pronto para sumarização.
        """

        if view not in FinancialBudgetActualService.PERIOD_VIEWS:
            raise ValueError(f"Visão inválida para Orçado x Realizado: {view}")

        selected_dimensions = tuple(dimensions or FinancialBudgetActualService.DIMENSIONS)
        date_field = "competence_date" if view == "competence" else None

        normalized_planned = []
        for record in planned_records:
            normalized_planned.append(
                {
                    **record,
                    "competence_date": record.get("competence_date", record.get("competence", record.get("period"))),
                }
            )
        normalized_actual = []
        for record in actual_records:
            normalized_actual.append(
                {
                    **record,
                    "competence_date": record.get("competence_date", record.get("competence", record.get("date"))),
                }
            )

        planned_grouped = FinancialBudgetActualService._aggregate_amount_records(
            normalized_planned,
            amount_fields=("planned_amount", "budget_amount", "amount"),
            dimensions=selected_dimensions,
            date_field=date_field,
            company_id=company_id,
        )
        actual_grouped = FinancialBudgetActualService._aggregate_amount_records(
            normalized_actual,
            amount_fields=("actual_amount", "signed_amount", "amount"),
            dimensions=selected_dimensions,
            date_field=date_field,
            company_id=company_id,
        )

        all_keys = sorted(set(planned_grouped) | set(actual_grouped), key=lambda item: tuple("" if value is None else str(value) for value in item))
        rows = []
        for key in all_keys:
            period_key = key[-1] if date_field else None
            rows.append(
                FinancialBudgetActualService._comparison_row(
                    key=key,
                    dimensions=selected_dimensions,
                    period_key=period_key,
                    planned_bucket=planned_grouped.get(key),
                    actual_bucket=actual_grouped.get(key),
                )
            )
        return rows

    @staticmethod
    def build_executive_summary(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
        planned = Decimal("0.00")
        actual = Decimal("0.00")
        status_counts: Dict[str, int] = defaultdict(int)
        row_count = 0
        for row in rows:
            row_count += 1
            planned += FinancialBudgetActualService._decimal(row.get("planned_amount"))
            actual += FinancialBudgetActualService._decimal(row.get("actual_amount"))
            status_counts[str(row.get("status") or "on_track")] += 1

        variance = planned - actual
        consumption_rate = Decimal("0.00")
        if planned != Decimal("0.00"):
            consumption_rate = ((actual / planned) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "contract_version": "financial_budget_actual_executive_summary_v1",
            "row_count": row_count,
            "planned_amount": FinancialBudgetActualService._float(planned),
            "actual_amount": FinancialBudgetActualService._float(actual),
            "variance_amount": FinancialBudgetActualService._float(variance),
            "consumption_rate": FinancialBudgetActualService._float(consumption_rate),
            "status": FinancialBudgetActualService._status_for(planned, actual),
            "status_counts": dict(sorted(status_counts.items())),
        }
