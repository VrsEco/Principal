from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialClassificationRule, FinancialImportBatch, FinancialImportRow
from schemas.financial import FinancialClassificationRuleInput, FinancialClassificationRuleUpdateInput
from services.financial_catalog_service import FinancialCatalogService
from services.financial_service import FinancialService


logger = logging.getLogger(__name__)


class FinancialClassificationService:
    """Camada determinística de classificação automática sobre staging/importação."""

    @staticmethod
    def create_rule(
        *,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        try:
            data = FinancialClassificationRuleInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para regra de classificação: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            chart_account_id=data.chart_account_id,
            cost_center_id=data.cost_center_id,
        )
        if reference_error:
            return None, reference_error

        try:
            rule = FinancialClassificationRule(**data.model_dump())
            db.session.add(rule)
            db.session.commit()
            return rule.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar regra de classificação financeira")
            return None, f"Erro ao criar regra de classificação: {str(exc)}"

    @staticmethod
    def list_rules(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        rules = FinancialClassificationRule.query.filter(
            FinancialClassificationRule.company_id == company_id,
            FinancialClassificationRule.deleted_at.is_(None),
        ).order_by(FinancialClassificationRule.priority.asc(), FinancialClassificationRule.id.asc()).all()
        return [rule.to_dict() for rule in rules], None

    @staticmethod
    def update_rule(
        *,
        rule_id: int,
        company_id: int,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        try:
            data = FinancialClassificationRuleUpdateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para atualização da regra: {str(exc)}"

        rule = FinancialClassificationRule.query.filter(
            FinancialClassificationRule.id == rule_id,
            FinancialClassificationRule.company_id == company_id,
            FinancialClassificationRule.deleted_at.is_(None),
        ).first()
        if not rule:
            return None, "Regra de classificação não encontrada no escopo da empresa."

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            chart_account_id=data.model_dump(exclude_unset=True).get("chart_account_id", rule.chart_account_id),
            cost_center_id=data.model_dump(exclude_unset=True).get("cost_center_id", rule.cost_center_id),
        )
        if reference_error:
            return None, reference_error

        try:
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(rule, key, value)
            db.session.commit()
            return rule.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao atualizar regra de classificação financeira %s", rule_id)
            return None, f"Erro ao atualizar regra de classificação: {str(exc)}"

    @staticmethod
    def toggle_rule(
        *,
        rule_id: int,
        company_id: int,
        is_active: bool,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        rule = FinancialClassificationRule.query.filter(
            FinancialClassificationRule.id == rule_id,
            FinancialClassificationRule.company_id == company_id,
            FinancialClassificationRule.deleted_at.is_(None),
        ).first()
        if not rule:
            return None, "Regra de classificação não encontrada no escopo da empresa."

        try:
            rule.is_active = bool(is_active)
            db.session.commit()
            return rule.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao alterar status da regra de classificação financeira %s", rule_id)
            return None, f"Erro ao alterar status da regra de classificação: {str(exc)}"

    @staticmethod
    def _row_field_value(row: FinancialImportRow, field_name: str) -> str:
        field = (field_name or "").strip()
        if hasattr(row, field):
            value = getattr(row, field, None)
        else:
            value = (row.normalized_payload or {}).get(field)
            if value is None:
                value = (row.raw_payload or {}).get(field)
        return str(value or "").strip().lower()

    @staticmethod
    def _matches_rule(rule: FinancialClassificationRule, row: FinancialImportRow, batch: FinancialImportBatch) -> bool:
        if rule.source_type and (rule.source_type != batch.source_type):
            return False

        haystack = FinancialClassificationService._row_field_value(row, rule.field_name)
        needle = str(rule.match_value or "").strip().lower()
        if not haystack or not needle:
            return False

        if rule.operator == "contains":
            return needle in haystack
        if rule.operator == "equals":
            return haystack == needle
        if rule.operator == "starts_with":
            return haystack.startswith(needle)
        return False

    @staticmethod
    def classify_batch(
        *,
        batch_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        batch = FinancialImportBatch.query.filter(
            FinancialImportBatch.id == batch_id,
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
        ).first()
        if not batch:
            return None, "Lote de importação não encontrado no escopo da empresa."

        rules = FinancialClassificationRule.query.filter(
            FinancialClassificationRule.company_id == company_id,
            FinancialClassificationRule.is_active.is_(True),
            FinancialClassificationRule.deleted_at.is_(None),
        ).order_by(FinancialClassificationRule.priority.asc(), FinancialClassificationRule.id.asc()).all()

        rows = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.import_batch_id == batch_id,
            FinancialImportRow.deleted_at.is_(None),
        ).order_by(FinancialImportRow.row_number.asc()).all()

        classified_count = 0

        try:
            for row in rows:
                for rule in rules:
                    if not FinancialClassificationService._matches_rule(rule, row, batch):
                        continue

                    normalized = dict(row.normalized_payload or {})
                    if rule.entry_type:
                        normalized["entry_type"] = rule.entry_type
                    if rule.movement_nature:
                        normalized["movement_nature"] = rule.movement_nature
                    if rule.chart_account_id:
                        normalized["chart_account_id"] = rule.chart_account_id
                    if rule.cost_center_id:
                        normalized["cost_center_id"] = rule.cost_center_id
                    if rule.activity_id:
                        normalized["activity_id"] = rule.activity_id
                    if rule.process_instance_id:
                        normalized["process_instance_id"] = rule.process_instance_id
                    if rule.routine_id:
                        normalized["routine_id"] = rule.routine_id
                    if rule.counterparty_hint:
                        normalized["counterparty_hint"] = rule.counterparty_hint
                    normalized["classification_rule_id"] = rule.id
                    normalized["classification_rule_name"] = rule.name
                    normalized = FinancialCatalogService.enrich_reference_payload(
                        company_id=company_id,
                        payload=normalized,
                        counterparty_text=row.counterparty_name,
                        description_text=row.description,
                        bank_reference=row.bank_reference,
                    )

                    row.normalized_payload = normalized
                    if row.processing_status == "staged":
                        row.processing_status = "validated"
                    classified_count += 1
                    break

            db.session.commit()
            return {
                "batch_id": batch_id,
                "classified_count": classified_count,
                "rule_count": len(rules),
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao classificar lote financeiro %s", batch_id)
            return None, f"Erro ao classificar lote: {str(exc)}"
