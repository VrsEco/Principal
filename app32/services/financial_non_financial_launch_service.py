from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import Project, Process, db
from models.financial import (
    FinancialChartAccount,
    FinancialCostCenter,
    FinancialCounterparty,
    FinancialDomainEnablement,
    FinancialEntry,
    FinancialNonFinancialLaunch,
)
from schemas.financial import FinancialNonFinancialLaunchInput
from services.financial_catalog_service import FinancialCatalogService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_service import FinancialService


class FinancialNonFinancialLaunchService:
    @staticmethod
    def list_options(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        counterparties, error = FinancialCatalogService.list_items(
            catalog_type="counterparties",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        chart_accounts, error = FinancialCatalogService.list_items(
            catalog_type="chart_accounts",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        cost_centers, error = FinancialCatalogService.list_items(
            catalog_type="cost_centers",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        enabled_domains, error = FinancialScheduleService.list_enabled_domains(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        parent_cost_center_ids = {
            int(item.get("parent_id"))
            for item in cost_centers or []
            if item.get("parent_id")
        }

        return {
            "counterparties": [item for item in counterparties or [] if item.get("is_active", True)],
            "chart_accounts": [
                item for item in chart_accounts or []
                if item.get("is_active", True) and item.get("accepts_posting")
            ],
            "cost_centers": [
                item for item in cost_centers or []
                if item.get("is_active", True) and int(item.get("id") or 0) not in parent_cost_center_ids
            ],
            "enabled_domains": enabled_domains or [],
        }, None

    @staticmethod
    def list_launches(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        query: Optional[str] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        launches_query = FinancialNonFinancialLaunch.query.filter(
            FinancialNonFinancialLaunch.company_id == company_id,
            FinancialNonFinancialLaunch.deleted_at.is_(None),
        )

        text = (query or "").strip().lower()
        if text:
            launches_query = launches_query.filter(
                db.or_(
                    db.func.lower(FinancialNonFinancialLaunch.launch_code).like(f"%{text}%"),
                    db.func.lower(FinancialNonFinancialLaunch.description).like(f"%{text}%"),
                    db.func.lower(db.func.coalesce(FinancialNonFinancialLaunch.title_number, "")).like(f"%{text}%"),
                    db.func.lower(db.func.coalesce(FinancialNonFinancialLaunch.installment_number, "")).like(f"%{text}%"),
                )
            )

        launches = launches_query.order_by(
            FinancialNonFinancialLaunch.launch_date.desc(),
            FinancialNonFinancialLaunch.id.desc(),
        ).all()
        return [FinancialNonFinancialLaunchService._serialize_launch(item) for item in launches], None

    @staticmethod
    def get_launch(
        *,
        company_id: int,
        launch_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        launch = FinancialNonFinancialLaunch.query.filter(
            FinancialNonFinancialLaunch.company_id == company_id,
            FinancialNonFinancialLaunch.id == launch_id,
            FinancialNonFinancialLaunch.deleted_at.is_(None),
        ).first()
        if not launch:
            return None, "Lançamento não financeiro não encontrado."
        return FinancialNonFinancialLaunchService._serialize_launch(launch, include_entries=True), None

    @staticmethod
    def create_launch(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialNonFinancialLaunchInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para lançamento não financeiro: {exc}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        counterparty_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            counterparty_id=data.counterparty_id,
        )
        if counterparty_error:
            return None, counterparty_error

        debit_error = FinancialNonFinancialLaunchService._validate_side(
            company_id=data.company_id,
            chart_account_id=data.debit_chart_account_id,
            cost_center_id=data.debit_cost_center_id,
            side_label="débito",
        )
        if debit_error:
            return None, debit_error

        credit_error = FinancialNonFinancialLaunchService._validate_side(
            company_id=data.company_id,
            chart_account_id=data.credit_chart_account_id,
            cost_center_id=data.credit_cost_center_id,
            side_label="crédito",
        )
        if credit_error:
            return None, credit_error

        debit_domain_label, error = FinancialNonFinancialLaunchService._validate_enabled_domain(
            company_id=data.company_id,
            domain_type=data.debit_domain_type,
            source_id=data.debit_domain_source_id,
            side_label="débito",
        )
        if error:
            return None, error

        credit_domain_label, error = FinancialNonFinancialLaunchService._validate_enabled_domain(
            company_id=data.company_id,
            domain_type=data.credit_domain_type,
            source_id=data.credit_domain_source_id,
            side_label="crédito",
        )
        if error:
            return None, error

        launch_code = FinancialNonFinancialLaunchService._generate_launch_code(data.company_id)
        debit_entry: Optional[FinancialEntry] = None
        credit_entry: Optional[FinancialEntry] = None

        try:
            debit_entry, error = FinancialService.create_entry(
                payload=FinancialNonFinancialLaunchService._build_entry_payload(
                    data=data,
                    launch_code=launch_code,
                    side="debit",
                    domain_label=debit_domain_label,
                ),
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                return None, error

            credit_entry, error = FinancialService.create_entry(
                payload=FinancialNonFinancialLaunchService._build_entry_payload(
                    data=data,
                    launch_code=launch_code,
                    side="credit",
                    domain_label=credit_domain_label,
                ),
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                FinancialNonFinancialLaunchService._cleanup_entries(
                    company_id=data.company_id,
                    debit_entry_id=debit_entry.id if debit_entry else None,
                )
                return None, error

            error = FinancialNonFinancialLaunchService._create_entry_allocation(
                company_id=data.company_id,
                entry_id=debit_entry.id,
                chart_account_id=data.debit_chart_account_id,
                cost_center_id=data.debit_cost_center_id,
                amount=data.amount,
                domain_type=data.debit_domain_type,
                domain_source_id=data.debit_domain_source_id,
                domain_label=debit_domain_label,
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                FinancialNonFinancialLaunchService._cleanup_entries(
                    company_id=data.company_id,
                    debit_entry_id=debit_entry.id if debit_entry else None,
                    credit_entry_id=credit_entry.id if credit_entry else None,
                )
                return None, error

            error = FinancialNonFinancialLaunchService._create_entry_allocation(
                company_id=data.company_id,
                entry_id=credit_entry.id,
                chart_account_id=data.credit_chart_account_id,
                cost_center_id=data.credit_cost_center_id,
                amount=data.amount,
                domain_type=data.credit_domain_type,
                domain_source_id=data.credit_domain_source_id,
                domain_label=credit_domain_label,
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                FinancialNonFinancialLaunchService._cleanup_entries(
                    company_id=data.company_id,
                    debit_entry_id=debit_entry.id if debit_entry else None,
                    credit_entry_id=credit_entry.id if credit_entry else None,
                )
                return None, error

            launch = FinancialNonFinancialLaunch(
                company_id=data.company_id,
                launch_code=launch_code,
                launch_status="posted",
                description=data.description,
                title_number=data.title_number,
                installment_number=data.installment_number,
                launch_date=data.launch_date,
                amount=data.amount,
                counterparty_id=data.counterparty_id,
                debit_chart_account_id=data.debit_chart_account_id,
                debit_cost_center_id=data.debit_cost_center_id,
                debit_domain_type=data.debit_domain_type,
                debit_domain_source_id=data.debit_domain_source_id,
                credit_chart_account_id=data.credit_chart_account_id,
                credit_cost_center_id=data.credit_cost_center_id,
                credit_domain_type=data.credit_domain_type,
                credit_domain_source_id=data.credit_domain_source_id,
                debit_entry_id=debit_entry.id,
                credit_entry_id=credit_entry.id,
                created_by_user_id=data.created_by_user_id,
                created_by_employee_id=data.created_by_employee_id,
                created_by_agent=data.created_by_agent,
                notes=data.notes,
                metadata_json={
                    **(data.metadata_json or {}),
                    "title_number": data.title_number,
                    "installment_number": data.installment_number,
                    "debit_domain_label": debit_domain_label,
                    "credit_domain_label": credit_domain_label,
                },
            )
            db.session.add(launch)
            db.session.flush()

            debit_entry.metadata_json = {
                **(debit_entry.metadata_json or {}),
                "non_financial_launch_id": launch.id,
                "non_financial_launch_code": launch.launch_code,
                "non_financial_side": "debit",
            }
            credit_entry.metadata_json = {
                **(credit_entry.metadata_json or {}),
                "non_financial_launch_id": launch.id,
                "non_financial_launch_code": launch.launch_code,
                "non_financial_side": "credit",
            }
            db.session.commit()
            return FinancialNonFinancialLaunchService._serialize_launch(launch, include_entries=True), None
        except Exception as exc:
            db.session.rollback()
            FinancialNonFinancialLaunchService._cleanup_entries(
                company_id=data.company_id,
                debit_entry_id=debit_entry.id if debit_entry else None,
                credit_entry_id=credit_entry.id if credit_entry else None,
            )
            return None, f"Erro ao criar lançamento não financeiro: {exc}"

    @staticmethod
    def _create_entry_allocation(
        *,
        company_id: int,
        entry_id: int,
        chart_account_id: int,
        cost_center_id: int,
        amount: Decimal,
        domain_type: Optional[str],
        domain_source_id: Optional[int],
        domain_label: Optional[str],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Optional[str]:
        _, error = FinancialService.replace_allocations(
            payload={
                "company_id": company_id,
                "financial_entry_id": entry_id,
                "allocations": [
                    {
                        "company_id": company_id,
                        "financial_entry_id": entry_id,
                        "chart_account_id": chart_account_id,
                        "cost_center_id": cost_center_id,
                        "allocation_type": "percentage",
                        "percentage": Decimal("100"),
                        "allocated_amount": amount,
                        "notes": None,
                        "metadata_json": {
                            "domain_type": domain_type,
                            "domain_source_id": domain_source_id,
                            "domain_label": domain_label,
                        },
                    }
                ],
            },
            allowed_company_ids=allowed_company_ids,
        )
        return error

    @staticmethod
    def _cleanup_entries(
        *,
        company_id: int,
        debit_entry_id: Optional[int] = None,
        credit_entry_id: Optional[int] = None,
    ) -> None:
        try:
            for entry_id in (credit_entry_id, debit_entry_id):
                if not entry_id:
                    continue
                entry = FinancialEntry.query.filter(
                    FinancialEntry.company_id == company_id,
                    FinancialEntry.id == entry_id,
                ).first()
                if entry:
                    db.session.delete(entry)
            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def _build_entry_payload(
        *,
        data: FinancialNonFinancialLaunchInput,
        launch_code: str,
        side: str,
        domain_label: Optional[str],
    ) -> Dict[str, Any]:
        is_debit = side == "debit"
        chart_account_id = data.debit_chart_account_id if is_debit else data.credit_chart_account_id
        cost_center_id = data.debit_cost_center_id if is_debit else data.credit_cost_center_id
        domain_type = data.debit_domain_type if is_debit else data.credit_domain_type
        domain_source_id = data.debit_domain_source_id if is_debit else data.credit_domain_source_id
        document_number = FinancialNonFinancialLaunchService._compose_document_number(
            data.title_number,
            data.installment_number,
        )
        return {
            "company_id": data.company_id,
            "entry_code": f"{launch_code}-{'D' if is_debit else 'C'}",
            "entry_type": "adjustment",
            "movement_nature": "debit" if is_debit else "credit",
            "origin_type": "manual",
            "status": "settled",
            "review_status": "approved",
            "description": data.description,
            "document_number": document_number,
            "external_reference": f"non_financial_launch:{launch_code}:{side}",
            "origin_reference": launch_code,
            "competence_date": data.launch_date,
            "due_date": data.launch_date,
            "occurred_on": data.launch_date,
            "original_amount": data.amount,
            "counterparty_id": data.counterparty_id,
            "chart_account_id": chart_account_id,
            "cost_center_id": cost_center_id,
            "created_by_user_id": data.created_by_user_id,
            "created_by_employee_id": data.created_by_employee_id,
            "created_by_agent": data.created_by_agent,
            "approved_by_user_id": data.created_by_user_id,
            "notes": data.notes,
            "metadata_json": {
                **(data.metadata_json or {}),
                "non_financial_launch": True,
                "launch_code": launch_code,
                "side": side,
                "title_number": data.title_number,
                "installment_number": data.installment_number,
                "domain_type": domain_type,
                "domain_source_id": domain_source_id,
                "domain_label": domain_label,
            },
        }

    @staticmethod
    def _compose_document_number(title_number: Optional[str], installment_number: Optional[str]) -> Optional[str]:
        if title_number and installment_number:
            return f"{title_number}/{installment_number}"
        return title_number or installment_number

    @staticmethod
    def _generate_launch_code(company_id: int) -> str:
        last_number = 0
        codes = (
            FinancialNonFinancialLaunch.query.with_entities(FinancialNonFinancialLaunch.launch_code)
            .filter(
                FinancialNonFinancialLaunch.company_id == company_id,
                FinancialNonFinancialLaunch.deleted_at.is_(None),
            )
            .all()
        )
        for (code,) in codes:
            digits = "".join(ch for ch in str(code or "") if ch.isdigit())
            if digits:
                last_number = max(last_number, int(digits))
        return f"LNF-{last_number + 1:06d}"

    @staticmethod
    def _validate_side(
        *,
        company_id: int,
        chart_account_id: int,
        cost_center_id: int,
        side_label: str,
    ) -> Optional[str]:
        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            chart_account_id=chart_account_id,
            cost_center_id=cost_center_id,
        )
        if reference_error:
            return f"Referências inválidas no lado {side_label}. {reference_error}"

        chart_account = FinancialChartAccount.query.filter(
            FinancialChartAccount.company_id == company_id,
            FinancialChartAccount.id == chart_account_id,
            FinancialChartAccount.deleted_at.is_(None),
        ).first()
        if not chart_account or not chart_account.accepts_posting:
            return f"O plano de contas do lado {side_label} precisa ser analítico."

        cost_center = FinancialCostCenter.query.filter(
            FinancialCostCenter.company_id == company_id,
            FinancialCostCenter.id == cost_center_id,
            FinancialCostCenter.deleted_at.is_(None),
        ).first()
        if not cost_center:
            return f"O centro de resultado do lado {side_label} é inválido."

        child_center = FinancialCostCenter.query.filter(
            FinancialCostCenter.company_id == company_id,
            FinancialCostCenter.parent_id == cost_center.id,
            FinancialCostCenter.deleted_at.is_(None),
        ).first()
        if child_center:
            return f"O centro de resultado do lado {side_label} precisa ser final/analítico."

        return None

    @staticmethod
    def _validate_enabled_domain(
        *,
        company_id: int,
        domain_type: Optional[str],
        source_id: Optional[int],
        side_label: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        if not domain_type or not source_id:
            return None, None

        enabled = FinancialDomainEnablement.query.filter(
            FinancialDomainEnablement.company_id == company_id,
            FinancialDomainEnablement.domain_type == domain_type,
            FinancialDomainEnablement.source_id == int(source_id),
            FinancialDomainEnablement.deleted_at.is_(None),
            FinancialDomainEnablement.is_enabled.is_(True),
        ).first()
        if not enabled:
            label = "projeto" if domain_type == "project" else "processo"
            return None, f"O {label} selecionado no lado {side_label} não está habilitado no Financeiro."

        source_label = FinancialNonFinancialLaunchService._resolve_domain_label(
            company_id=company_id,
            domain_type=domain_type,
            source_id=int(source_id),
        )
        return source_label, None

    @staticmethod
    def _resolve_domain_label(*, company_id: int, domain_type: str, source_id: int) -> Optional[str]:
        if domain_type == "project":
            project = Project.query.filter(
                Project.company_id == company_id,
                Project.id == source_id,
            ).first()
            if not project:
                return None
            project_code = getattr(project, "code", None)
            return f"{project_code + ' - ' if project_code else ''}{project.name}"

        process = Process.query.filter(
            Process.company_id == company_id,
            Process.id == source_id,
        ).first()
        if not process:
            return None
        return f"{process.code + ' - ' if getattr(process, 'code', None) else ''}{process.name}"

    @staticmethod
    def _serialize_launch(
        launch: FinancialNonFinancialLaunch,
        *,
        include_entries: bool = False,
    ) -> Dict[str, Any]:
        payload = launch.to_dict()
        payload["counterparty_label"] = FinancialNonFinancialLaunchService._counterparty_label(launch.counterparty)
        payload["debit_chart_account_label"] = FinancialNonFinancialLaunchService._account_label(launch.debit_chart_account)
        payload["credit_chart_account_label"] = FinancialNonFinancialLaunchService._account_label(launch.credit_chart_account)
        payload["debit_cost_center_label"] = FinancialNonFinancialLaunchService._cost_center_label(launch.debit_cost_center)
        payload["credit_cost_center_label"] = FinancialNonFinancialLaunchService._cost_center_label(launch.credit_cost_center)
        payload["debit_domain_label"] = FinancialNonFinancialLaunchService._domain_label_from_launch(launch, side="debit")
        payload["credit_domain_label"] = FinancialNonFinancialLaunchService._domain_label_from_launch(launch, side="credit")
        payload["title_installment_label"] = FinancialNonFinancialLaunchService._compose_document_number(
            launch.title_number,
            launch.installment_number,
        )
        if include_entries:
            payload["debit_entry"] = FinancialService.serialize_entry(launch.debit_entry) if launch.debit_entry else None
            payload["credit_entry"] = FinancialService.serialize_entry(launch.credit_entry) if launch.credit_entry else None
        return payload

    @staticmethod
    def _counterparty_label(counterparty: Optional[FinancialCounterparty]) -> Optional[str]:
        if not counterparty:
            return None
        return f"{counterparty.code} - {counterparty.name}" if counterparty.code else counterparty.name

    @staticmethod
    def _account_label(account: Optional[FinancialChartAccount]) -> Optional[str]:
        if not account:
            return None
        return f"{account.code} - {account.name}" if account.code else account.name

    @staticmethod
    def _cost_center_label(center: Optional[FinancialCostCenter]) -> Optional[str]:
        if not center:
            return None
        return f"{center.code} - {center.name}" if center.code else center.name

    @staticmethod
    def _domain_label_from_launch(launch: FinancialNonFinancialLaunch, *, side: str) -> Optional[str]:
        metadata_key = f"{side}_domain_label"
        metadata_label = (launch.metadata_json or {}).get(metadata_key)
        if metadata_label:
            return metadata_label

        domain_type = getattr(launch, f"{side}_domain_type", None)
        domain_source_id = getattr(launch, f"{side}_domain_source_id", None)
        if not domain_type or not domain_source_id:
            return None

        return FinancialNonFinancialLaunchService._resolve_domain_label(
            company_id=launch.company_id,
            domain_type=domain_type,
            source_id=int(domain_source_id),
        )
