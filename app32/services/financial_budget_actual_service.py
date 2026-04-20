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
