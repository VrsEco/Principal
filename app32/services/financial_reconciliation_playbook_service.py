"""Playbooks operacionais de conciliação, separados da execução financeira."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialBankAccount,
    FinancialImportBatch,
    FinancialImportRow,
    FinancialReconciliationPlaybook,
    FinancialSchedule,
)
from schemas.financial import FinancialReconciliationPlaybookInput, FinancialReconciliationPlaybookUpdateInput
from services.financial_classification_service import FinancialClassificationService
from services.financial_service import FinancialService


class FinancialReconciliationPlaybookService:
    """Armazena padrões por tenant e somente devolve sugestões; nunca baixa sozinho."""

    @staticmethod
    def _validate_action_targets(*, company_id: int, action_type: str, payload: Dict) -> Optional[str]:
        if action_type == "transfer":
            target = payload.get("destination_bank_account_id")
            if not target:
                return "Playbook de transferência exige destination_bank_account_id."
            account = FinancialBankAccount.query.filter_by(id=target, company_id=company_id, deleted_at=None).first()
            if not account:
                return "Conta destino do playbook não encontrada no escopo da empresa."
        if action_type == "schedule_settlement":
            target = payload.get("financial_schedule_id")
            if not target:
                return "Playbook de baixa de agendamento exige financial_schedule_id."
            schedule = FinancialSchedule.query.filter_by(id=target, company_id=company_id, deleted_at=None).first()
            if not schedule:
                return "Agendamento do playbook não encontrado no escopo da empresa."
        return None

    @staticmethod
    def create_playbook(*, payload: Dict, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            data = FinancialReconciliationPlaybookInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para playbook de conciliação: {exc}"
        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        target_error = FinancialReconciliationPlaybookService._validate_action_targets(
            company_id=data.company_id, action_type=data.action_type, payload=data.action_payload_json,
        )
        if target_error:
            return None, target_error
        duplicate = FinancialReconciliationPlaybook.query.filter_by(
            company_id=data.company_id, playbook_code=data.playbook_code, deleted_at=None,
        ).first()
        if duplicate:
            return None, "Já existe playbook com este código na empresa."
        item = FinancialReconciliationPlaybook(**data.model_dump())
        db.session.add(item)
        db.session.commit()
        return item.to_dict(), None

    @staticmethod
    def list_playbooks(*, company_id: int, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        items = FinancialReconciliationPlaybook.query.filter_by(company_id=company_id, deleted_at=None).order_by(
            FinancialReconciliationPlaybook.priority.asc(), FinancialReconciliationPlaybook.id.asc(),
        ).all()
        return [item.to_dict() for item in items], None

    @staticmethod
    def update_playbook(*, company_id: int, playbook_id: int, payload: Dict, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        try:
            changes = FinancialReconciliationPlaybookUpdateInput(**payload).model_dump(exclude_unset=True)
        except Exception as exc:
            return None, f"Payload inválido para playbook de conciliação: {exc}"
        item = FinancialReconciliationPlaybook.query.filter_by(id=playbook_id, company_id=company_id, deleted_at=None).first()
        if not item:
            return None, "Playbook de conciliação não encontrado no escopo da empresa."
        action_type = changes.get("action_type", item.action_type)
        action_payload = changes.get("action_payload_json", item.action_payload_json)
        target_error = FinancialReconciliationPlaybookService._validate_action_targets(
            company_id=company_id, action_type=action_type, payload=action_payload or {},
        )
        if target_error:
            return None, target_error
        for key, value in changes.items():
            setattr(item, key, value)
        db.session.commit()
        return item.to_dict(), None

    @staticmethod
    def suggest_for_row(*, company_id: int, import_row_id: int, allowed_company_ids: Optional[Sequence[int]] = None) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        row = FinancialImportRow.query.filter_by(id=import_row_id, company_id=company_id, deleted_at=None).first()
        if not row:
            return None, "Linha do extrato não encontrada no escopo da empresa."
        batch = FinancialImportBatch.query.filter_by(id=row.import_batch_id, company_id=company_id, deleted_at=None).first()
        if not batch:
            return None, "Lote da linha do extrato não encontrado no escopo da empresa."
        items = FinancialReconciliationPlaybook.query.filter_by(company_id=company_id, is_active=True, deleted_at=None).order_by(
            FinancialReconciliationPlaybook.priority.asc(), FinancialReconciliationPlaybook.id.asc(),
        ).all()
        matches = []
        for item in items:
            if FinancialClassificationService._matches_rule(item, row, batch):
                matches.append({
                    "playbook": item.to_dict(),
                    "import_row_id": row.id,
                    "requires_human_confirmation": item.confirmation_policy != "never",
                    "execution": "suggestion_only",
                })
        return {"import_row_id": row.id, "suggestions": matches}, None
