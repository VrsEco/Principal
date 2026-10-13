"""Regras de negócio SOMENTE LEITURA das ferramentas financeiras que exigem aprovação humana.

A aprovação vale só para o conteúdo exato da chamada: se o serviço recusa o conteúdo depois, ela já foi consumida e se
perde. Estas funções antecipam a recusa (registro inexistente, conteúdo inválido, regra de saldo) antes de abrir ou
consumir a aprovação. Nenhuma grava nada e nenhuma bloqueia linhas. São consultivas: o serviço real valida de novo e é
quem decide.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple


def settlement_request_rules(company_id: Any, payload: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Regras da ferramenta ``create_financial_settlement`` (as mesmas antes e depois da aprovação)."""
    if isinstance(company_id, bool) or not isinstance(company_id, int) or company_id <= 0:
        return None, "company_id válido é obrigatório"
    normalized = dict(payload or {})
    payload_company_id = normalized.get("company_id")
    if payload_company_id not in (None, ""):
        try:
            if int(payload_company_id) != company_id:
                return None, "company_id do payload diverge do tenant da requisição"
        except (TypeError, ValueError):
            return None, "company_id do payload é inválido"
    normalized["company_id"] = company_id
    if not normalized.get("financial_entry_id"):
        return None, "financial_entry_id é obrigatório para a baixa."
    if not normalized.get("bank_account_id"):
        return None, "bank_account_id é obrigatório para registrar uma baixa bancária vinculada."
    if str(normalized.get("settlement_status") or "posted").strip().lower() != "posted":
        return None, "A baixa MCP deve ser registrada com settlement_status=posted."
    return normalized, None


def settlement_read_only(normalized: Dict[str, Any]) -> Optional[str]:
    """Validação de leitura da baixa: formato, lançamento da empresa, bloqueio de borderô, banco e saldo."""
    from models import db
    from models.financial import FinancialEntry, FinancialSchedule, FinancialSettlement
    from schemas.financial import FinancialSettlementInput
    from services.financial_bordero_service import FinancialBorderoService
    from services.financial_catalog_service import FinancialCatalogService
    from services.financial_service import FinancialService

    data_in = dict(normalized)
    data_in["settlement_code"] = str(data_in.get("settlement_code") or "").strip() or "AUTO-PENDING"
    try:
        data = FinancialSettlementInput(**data_in)
    except Exception as exc:
        return f"Payload inválido para baixa: {str(exc)}"

    entry = FinancialEntry.query.filter(
        FinancialEntry.id == data.financial_entry_id,
        FinancialEntry.company_id == data.company_id,
        FinancialEntry.deleted_at.is_(None),
    ).first()
    if not entry:
        return "Lançamento financeiro não encontrado para baixa."

    active_bordero = FinancialBorderoService.get_active_bordero_for_entry(company_id=data.company_id, entry=entry)
    if active_bordero:
        return f"Lançamento bloqueado pelo borderô {active_bordero.bordero_code}. Faça a baixa pelo borderô."

    if data.settlement_code != "AUTO-PENDING":
        existing = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == data.company_id,
            FinancialSettlement.settlement_code == data.settlement_code,
        ).first()
        if existing:
            return f"Já existe baixa com código {data.settlement_code} para esta empresa."

    reference_error = FinancialCatalogService.validate_reference_ids(
        company_id=data.company_id, bank_account_id=data.bank_account_id
    )
    if reference_error:
        return reference_error

    if data.principal_amount < Decimal("0"):
        return "Baixa inválida: o valor principal não pode ser negativo."
    if (data.gross_amount or data.net_amount or Decimal("0")) <= Decimal("0"):
        return "Baixa inválida: o valor da baixa deve ser maior que zero."

    schedule = None
    if getattr(entry, "financial_schedule_id", None):
        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == entry.financial_schedule_id,
            FinancialSchedule.company_id == entry.company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
    total_liquidated = (
        db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.principal_amount), 0))
        .filter(
            FinancialSettlement.company_id == data.company_id,
            FinancialSettlement.financial_entry_id == data.financial_entry_id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
        )
        .scalar()
    ) or Decimal("0")
    basis = FinancialService._resolve_entry_principal_basis_amount(entry, schedule=schedule)
    if Decimal(total_liquidated) + data.principal_amount > basis:
        return (
            "Baixa principal excede o valor principal do lançamento. "
            f"Baixado atual: {total_liquidated}. Principal: {basis}."
        )
    return None


def _exists(model: Any, company_id: int, record_id: Any) -> bool:
    try:
        record_id = int(record_id)
    except (TypeError, ValueError):
        return False
    query = model.query.filter(model.id == record_id, model.company_id == int(company_id))
    if hasattr(model, "deleted_at"):
        query = query.filter(model.deleted_at.is_(None))
    return query.first() is not None


def import_batch_exists(company_id: int, batch_id: Any) -> Optional[str]:
    from models.financial import FinancialImportBatch

    return None if _exists(FinancialImportBatch, company_id, batch_id) else "Lote de importação não encontrado nesta empresa."


def import_row_exists(company_id: int, row_id: Any) -> Optional[str]:
    from models.financial import FinancialImportRow

    return None if _exists(FinancialImportRow, company_id, row_id) else "Linha do extrato não encontrada nesta empresa."


def entry_exists(company_id: int, entry_id: Any) -> Optional[str]:
    from models.financial import FinancialEntry

    return None if _exists(FinancialEntry, company_id, entry_id) else "Lançamento financeiro não encontrado nesta empresa."


def bordero_exists(company_id: int, bordero_id: Any) -> Optional[str]:
    from models.financial import FinancialBordero

    return None if _exists(FinancialBordero, company_id, bordero_id) else "Borderô não encontrado nesta empresa."


def schedule_exists(company_id: int, schedule_id: Any) -> Optional[str]:
    from models.financial import FinancialSchedule

    return None if _exists(FinancialSchedule, company_id, schedule_id) else "Agendamento não encontrado nesta empresa."


def run_until_valid(run_until: Any) -> Optional[str]:
    if not run_until:
        return None
    try:
        datetime.strptime(str(run_until), "%Y-%m-%d")
    except ValueError:
        return "run_until inválido. Use YYYY-MM-DD."
    return None
