"""Regra de rateio obrigatório para títulos financeiros criados via MCP (contas a pagar e a receber).

Todo título a pagar ou a receber exige rateio: a soma fecha em 100% (ou, se por valor, no valor do título) e cada
linha traz plano de contas e centro de resultado analíticos. A regra é a mesma do agendamento e do lançamento direto
(``FinancialScheduleService._validate_schedule_allocations``); aqui ela passa a valer também para ``create_financial_entry``.

Este módulo é a única fonte da regra: a ferramenta MCP e o pré-validador (que roda antes de pedir a aprovação humana)
chamam as mesmas funções.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

RATEIO_REQUIRED_ENTRY_TYPES = ("payable", "receivable")

ALLOCATIONS_REQUIRED_MESSAGE = (
    "Informe o rateio do título em allocations: soma de 100% (ou valores somando o valor do título), com plano de "
    "contas e centro de resultado analíticos em cada linha. Exemplo: "
    '[{"allocation_type": "percentage", "percentage": 100, "chart_account_id": 217, "cost_center_id": 24}].'
)


def requires_allocations(entry_type: Any) -> bool:
    return str(entry_type or "").strip().lower() in RATEIO_REQUIRED_ENTRY_TYPES


def normalize_allocations(raw: Any) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Valida o formato das linhas e devolve dicionários prontos para a regra e para ``replace_allocations``."""
    from schemas.financial import FinancialDirectEntryAllocationInput

    if not isinstance(raw, list) or not raw:
        return None, ALLOCATIONS_REQUIRED_MESSAGE
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            return None, f"Linha {index} do rateio deve ser um objeto."
        try:
            parsed = FinancialDirectEntryAllocationInput.model_validate(item)
        except Exception as exc:
            return None, f"Linha {index} do rateio inválida: {exc}"
        normalized.append(parsed.model_dump())
    return normalized, None


def validate_allocations_rules(
    *, company_id: int, original_amount: Any, due_date: Any, allocations: List[Dict[str, Any]]
) -> Optional[str]:
    """Soma, plano de contas, centro de resultado analíticos e domínios, com as regras do agendamento."""
    from services.financial_schedule_service import FinancialScheduleService

    return FinancialScheduleService._validate_schedule_allocations(
        company_id=company_id,
        template_amount=original_amount,
        due_date=due_date,
        metadata_json={
            "allocations": [
                {
                    "chart_account_id": item.get("chart_account_id"),
                    "cost_center_id": item.get("cost_center_id"),
                    "budget_line_id": item.get("budget_line_id"),
                    "budget_contract_id": item.get("budget_contract_id"),
                    "budget_document_id": item.get("budget_document_id"),
                    "domain_source_kind": item.get("domain_source_kind") or "routine",
                    "domain_type": item.get("domain_type"),
                    "domain_source_id": item.get("domain_source_id"),
                    "domain_label": item.get("domain_label"),
                    "allocation_type": item.get("allocation_type"),
                    "percentage": item.get("percentage"),
                    "allocated_amount": item.get("allocated_amount"),
                }
                for item in allocations
            ]
        },
    )


def validate_title_creation(
    *, company_id: int, payload: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]], Optional[str]]:
    """Valida o título e o rateio SEM gravar nada.

    Devolve ``(payload sem allocations, rateio normalizado ou None, erro)``. O rateio é obrigatório para contas a
    pagar e a receber; para os demais tipos só é validado quando informado.
    """
    from services.financial_service import FinancialService

    data = dict(payload or {})
    raw_allocations = data.pop("allocations", None)
    needs_allocations = requires_allocations(data.get("entry_type")) or bool(raw_allocations)

    allocations: Optional[List[Dict[str, Any]]] = None
    if needs_allocations:
        allocations, error = normalize_allocations(raw_allocations)
        if error:
            return None, None, error

    entry_data, _links, error = FinancialService.validate_entry_creation(payload=data)
    if error:
        return None, None, error

    if allocations:
        error = validate_allocations_rules(
            company_id=company_id,
            original_amount=entry_data.original_amount,
            due_date=entry_data.due_date,
            allocations=allocations,
        )
        if error:
            return None, None, error
    return data, allocations, None


def to_replace_allocations_payload(
    *, company_id: int, entry_id: int, allocations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Formato de ``FinancialService.replace_allocations`` (campos de domínio e orçamento vão para o metadata)."""
    return {
        "company_id": company_id,
        "financial_entry_id": entry_id,
        "allocations": [
            {
                "company_id": company_id,
                "financial_entry_id": entry_id,
                "chart_account_id": item.get("chart_account_id"),
                "cost_center_id": item.get("cost_center_id"),
                "allocation_type": item.get("allocation_type"),
                "percentage": item.get("percentage"),
                "allocated_amount": item.get("allocated_amount"),
                "notes": item.get("notes"),
                "metadata_json": {
                    **(item.get("metadata_json") or {}),
                    "domain_source_kind": item.get("domain_source_kind") or "routine",
                    "domain_type": item.get("domain_type"),
                    "domain_source_id": item.get("domain_source_id"),
                    "domain_label": item.get("domain_label"),
                    "budget_version_id": item.get("budget_version_id"),
                    "budget_line_id": item.get("budget_line_id"),
                    "budget_contract_id": item.get("budget_contract_id"),
                    "budget_document_id": item.get("budget_document_id"),
                },
            }
            for item in allocations
        ],
    }


def create_title_with_allocations(
    *, payload: Dict[str, Any], allocations: List[Dict[str, Any]]
) -> Tuple[Optional[Any], Optional[str]]:
    """Cria o lançamento e aplica o rateio juntos; se o rateio falhar, o lançamento recém-criado é desfeito."""
    from models import db
    from models.financial import FinancialEntry
    from services.financial_service import FinancialService

    entry, error = FinancialService.create_entry(payload=payload)
    if error:
        return None, error
    _created, error = FinancialService.replace_allocations(
        payload=to_replace_allocations_payload(
            company_id=int(payload["company_id"]), entry_id=entry.id, allocations=allocations
        )
    )
    if error:
        try:
            created_entry = FinancialEntry.query.filter(
                FinancialEntry.company_id == int(payload["company_id"]), FinancialEntry.id == entry.id
            ).first()
            if created_entry is not None:
                db.session.delete(created_entry)
            db.session.commit()
        except Exception:
            db.session.rollback()
        return None, error
    return entry, None
