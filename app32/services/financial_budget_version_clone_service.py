from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Dict, Optional, Sequence, Tuple

from models import db, FinancialBudgetAmount, FinancialBudgetLine, FinancialBudgetVersion
from schemas.financial_budget import FinancialBudgetVersionDuplicateInput
from services.financial_service import FinancialService


class FinancialBudgetVersionCloneService:
    @staticmethod
    def duplicate_version(
        *,
        company_id: int,
        source_version_id: int,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        source = (
            FinancialBudgetVersion.query.filter(
                FinancialBudgetVersion.id == source_version_id,
                FinancialBudgetVersion.company_id == company_id,
                FinancialBudgetVersion.deleted_at.is_(None),
            )
            .first()
        )
        if not source:
            return None, "Versão orçamentária de origem não encontrada no escopo da empresa."

        data = FinancialBudgetVersionDuplicateInput.model_validate(
            {
                **payload,
                "company_id": company_id,
            }
        )

        code = data.code or FinancialBudgetVersionCloneService._build_unique_code(company_id=company_id, base_code=source.code)
        name = data.name or f"{source.name} (Cópia)"

        existing = (
            FinancialBudgetVersion.query.filter(
                FinancialBudgetVersion.company_id == company_id,
                FinancialBudgetVersion.code == code,
                FinancialBudgetVersion.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            return None, f"Já existe versão orçamentária com código {code} para esta empresa."

        duplicated = FinancialBudgetVersion(
            company_id=company_id,
            code=code,
            name=name,
            scenario_type=data.scenario_type or source.scenario_type,
            status=data.status,
            period_start=source.period_start,
            period_end=source.period_end,
            notes=data.notes if data.notes is not None else source.notes,
            metadata_json=deepcopy(source.metadata_json or {}),
            created_by_user_id=data.created_by_user_id,
        )
        db.session.add(duplicated)
        db.session.flush()

        source_lines = (
            FinancialBudgetLine.query.filter(
                FinancialBudgetLine.company_id == company_id,
                FinancialBudgetLine.budget_version_id == source_version_id,
                FinancialBudgetLine.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetLine.line_order.asc(), FinancialBudgetLine.id.asc())
            .all()
        )
        for source_line in source_lines:
            duplicated_line = FinancialBudgetLine(
                company_id=company_id,
                budget_version_id=duplicated.id,
                line_code=source_line.line_code,
                line_name=source_line.line_name,
                line_order=source_line.line_order,
                budget_view=source_line.budget_view,
                movement_nature=source_line.movement_nature,
                chart_account_id=source_line.chart_account_id,
                cost_center_id=source_line.cost_center_id,
                activity_id=source_line.activity_id,
                process_instance_id=source_line.process_instance_id,
                routine_id=source_line.routine_id,
                notes=source_line.notes,
                is_active=source_line.is_active,
                metadata_json=deepcopy(source_line.metadata_json or {}),
            )
            db.session.add(duplicated_line)
            db.session.flush()

            source_amounts = (
                FinancialBudgetAmount.query.filter(
                    FinancialBudgetAmount.company_id == company_id,
                    FinancialBudgetAmount.budget_line_id == source_line.id,
                    FinancialBudgetAmount.deleted_at.is_(None),
                )
                .order_by(FinancialBudgetAmount.period_month.asc(), FinancialBudgetAmount.id.asc())
                .all()
            )
            for source_amount in source_amounts:
                db.session.add(
                    FinancialBudgetAmount(
                        company_id=company_id,
                        budget_line_id=duplicated_line.id,
                        period_month=source_amount.period_month,
                        budget_amount=source_amount.budget_amount,
                        notes=source_amount.notes,
                        metadata_json=deepcopy(source_amount.metadata_json or {}),
                    )
                )

        if duplicated.status == "active":
            FinancialBudgetVersionCloneService._deactivate_other_versions(
                company_id=company_id,
                exclude_version_id=duplicated.id,
            )

        try:
            db.session.commit()
            return duplicated.to_dict(), None
        except Exception:
            db.session.rollback()
            return None, "Não foi possível duplicar a versão orçamentária."

    @staticmethod
    def _build_unique_code(*, company_id: int, base_code: str) -> str:
        base = (base_code or "BUD").strip()[:38]
        timestamp = datetime.utcnow().strftime("%m%d%H%M")
        candidate = f"{base}-CP{timestamp}"[:50]
        counter = 2
        while (
            FinancialBudgetVersion.query.filter(
                FinancialBudgetVersion.company_id == company_id,
                FinancialBudgetVersion.code == candidate,
                FinancialBudgetVersion.deleted_at.is_(None),
            ).first()
            is not None
        ):
            suffix = f"-{counter}"
            candidate = f"{base[: 50 - len(suffix)]}{suffix}"
            counter += 1
        return candidate

    @staticmethod
    def _deactivate_other_versions(*, company_id: int, exclude_version_id: int) -> None:
        (
            FinancialBudgetVersion.query.filter(
                FinancialBudgetVersion.company_id == company_id,
                FinancialBudgetVersion.deleted_at.is_(None),
                FinancialBudgetVersion.id != exclude_version_id,
                FinancialBudgetVersion.status == "active",
            )
            .update({"status": "draft"}, synchronize_session=False)
        )
