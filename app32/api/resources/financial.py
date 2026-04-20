from __future__ import annotations

import logging
from datetime import datetime

from flask import current_app, request
from flask_restful import Resource
from flask_login import current_user

from models import (
    db,
    FinancialBudgetContract,
    FinancialBudgetDocument,
    FinancialBudgetLine,
    FinancialBudgetVersion,
    FinancialEntry,
    FinancialEntryAllocation,
    FinancialSchedule,
    FinancialSettlement,
)
from schemas.financial import (
    financial_entry_allocation_schema,
    financial_entry_allocations_schema,
)
from services.financial_service import FinancialService
from services.financial_import_service import FinancialImportService
from services.financial_ingestion_service import FinancialIngestionService
from services.financial_direct_entry_service import FinancialDirectEntryService
from services.financial_classification_service import FinancialClassificationService
from services.financial_classification_hybrid_service import FinancialClassificationHybridService
from services.financial_classification_dashboard_service import FinancialClassificationDashboardService
from services.financial_catalog_service import FinancialCatalogService
from services.financial_domain_enablement_service import FinancialDomainEnablementService
from services.financial_report_service import FinancialReportService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_title_calculation_service import FinancialTitleCalculationService
from services.financial_settlement_composition_service import FinancialSettlementCompositionService
from services.financial_automation_service import FinancialAutomationService
from services.financial_process_trigger_service import FinancialProcessTriggerService
from services.financial_executive_dashboard_service import FinancialExecutiveDashboardService
from services.financial_ai_classification_service import FinancialAIClassificationService
from services.financial_classification_question_service import FinancialClassificationQuestionService
from services.financial_reconciliation_service import FinancialReconciliationService
from services.financial_reconciliation_workspace_service import FinancialReconciliationWorkspaceService
from services.financial_bordero_service import FinancialBorderoService
from utils.company_access import get_accessible_company_ids
from utils.permissions import permission_required

from .process import get_request_company_id


logger = logging.getLogger(__name__)

PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."


def _sanitize_update_payload(payload: dict | None, *extra_fields: str) -> dict:
    sanitized = dict(payload or {})
    for field in {"company_id", "id", "created_at", "updated_at", "deleted_at", *extra_fields}:
        sanitized.pop(field, None)
    return sanitized


def _attach_financial_actor_context(payload: dict | None, *, default_agent: str = "app32") -> dict:
    normalized = dict(payload or {})
    user_id = getattr(current_user, "id", None)
    employee_id = getattr(current_user, "employee_id", None)
    actor_name = str(getattr(current_user, "name", "") or getattr(current_user, "email", "") or "").strip() or None
    normalized.setdefault("created_by_user_id", user_id)
    if employee_id is not None:
        normalized.setdefault("created_by_employee_id", employee_id)
    normalized.setdefault("created_by_agent", default_agent)

    metadata = dict(normalized.get("metadata_json") or {})
    audit = dict(metadata.get("audit") or {})
    actor = dict(audit.get("actor") or {})
    if user_id is not None:
        actor.setdefault("user_id", user_id)
    if employee_id is not None:
        actor.setdefault("employee_id", employee_id)
    if actor_name:
        actor.setdefault("user_name", actor_name)
    if normalized.get("created_by_agent"):
        actor.setdefault("agent", normalized.get("created_by_agent"))
    audit["actor"] = actor
    audit.setdefault("channel", default_agent)
    metadata["audit"] = audit
    normalized["metadata_json"] = metadata
    return normalized


def _serialize_entry(entry: FinancialEntry) -> dict:
    return FinancialService.serialize_entry(entry)


def _recalculate_entry_status(entry: FinancialEntry) -> None:
    total_liquidated = (
        db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.principal_amount), 0))
        .filter(
            FinancialSettlement.company_id == entry.company_id,
            FinancialSettlement.financial_entry_id == entry.id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
        )
        .scalar()
    ) or 0

    original_amount = entry.original_amount or 0
    if total_liquidated >= original_amount and original_amount > 0:
        entry.status = "settled"
        return

    if total_liquidated > 0:
        entry.status = "partially_settled"
        return

    if entry.status in {"partially_settled", "settled"}:
        entry.status = "posted"


class FinancialEntryListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        if not company_id:
            return [], 200

        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        )

        status = request.args.get("status")
        entry_type = request.args.get("entry_type")
        origin_type = request.args.get("origin_type")
        activity_id = request.args.get("activity_id", type=int)
        process_instance_id = request.args.get("process_instance_id", type=int)
        due_date_from = request.args.get("due_date_from")
        due_date_to = request.args.get("due_date_to")
        competence_date_from = request.args.get("competence_date_from")
        competence_date_to = request.args.get("competence_date_to")

        if status:
            query = query.filter(FinancialEntry.status == status)
        if entry_type:
            query = query.filter(FinancialEntry.entry_type == entry_type)
        if origin_type:
            query = query.filter(FinancialEntry.origin_type == origin_type)
        if activity_id:
            query = query.filter(FinancialEntry.activity_id == activity_id)
        if process_instance_id:
            query = query.filter(FinancialEntry.process_instance_id == process_instance_id)
        if due_date_from:
            query = query.filter(FinancialEntry.due_date >= due_date_from)
        if due_date_to:
            query = query.filter(FinancialEntry.due_date <= due_date_to)
        if competence_date_from:
            query = query.filter(FinancialEntry.competence_date >= competence_date_from)
        if competence_date_to:
            query = query.filter(FinancialEntry.competence_date <= competence_date_to)

        entries = query.order_by(FinancialEntry.competence_date.desc(), FinancialEntry.id.desc()).all()
        return FinancialService.serialize_entry_list(entries), 200

    @permission_required("financial", "create")
    def post(self):
        payload = request.get_json() or {}
        company_id = get_request_company_id()
        if company_id:
            payload["company_id"] = company_id

        entry, error = FinancialService.create_entry(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400

        return _serialize_entry(entry), 201


class FinancialDirectEntryOptionsResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialDirectEntryService.list_options(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialDirectEntryCreateResource(Resource):
    @permission_required("financial", "create")
    def post(self):
        payload = request.get_json(silent=True) or {}
        payload["company_id"] = get_request_company_id()
        payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
        result, error = FinancialDirectEntryService.create_direct_entry(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialCatalogListResource(Resource):
    @permission_required("financial", "view")
    def get(self, catalog_type: str):
        company_id = get_request_company_id()
        result, error = FinancialCatalogService.list_items(
            catalog_type=catalog_type,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "create")
    def post(self, catalog_type: str):
        payload = request.get_json(silent=True) or {}
        payload["company_id"] = get_request_company_id()
        result, error = FinancialCatalogService.create_item(
            catalog_type=catalog_type,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialCatalogResource(Resource):
    @permission_required("financial", "edit")
    def put(self, catalog_type: str, item_id: int):
        company_id = get_request_company_id()
        payload = _sanitize_update_payload(request.get_json(silent=True))
        result, error = FinancialCatalogService.update_item(
            catalog_type=catalog_type,
            item_id=item_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "delete")
    def delete(self, catalog_type: str, item_id: int):
        company_id = get_request_company_id()
        result, error = FinancialCatalogService.delete_item(
            catalog_type=catalog_type,
            item_id=item_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialCatalogToggleResource(Resource):
    @permission_required("financial", "edit")
    def post(self, catalog_type: str, item_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialCatalogService.toggle_item(
            catalog_type=catalog_type,
            item_id=item_id,
            company_id=company_id,
            is_active=bool(payload.get("is_active")),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialDomainEnablementListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialDomainEnablementService.list_items(
            company_id=company_id,
            domain_type=request.args.get("domain_type"),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialDomainEnablementResource(Resource):
    @permission_required("financial", "edit")
    def post(self, domain_type: str, source_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialDomainEnablementService.upsert_item(
            company_id=company_id,
            domain_type=domain_type,
            source_id=source_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "edit")
    def put(self, domain_type: str, source_id: int):
        company_id = get_request_company_id()
        payload = _sanitize_update_payload(request.get_json(silent=True), "domain_type", "source_id")
        result, error = FinancialDomainEnablementService.update_item(
            company_id=company_id,
            domain_type=domain_type,
            source_id=source_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialDomainEnablementToggleResource(Resource):
    @permission_required("financial", "edit")
    def post(self, domain_type: str, source_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialDomainEnablementService.toggle_item(
            company_id=company_id,
            domain_type=domain_type,
            source_id=source_id,
            is_enabled=bool(payload.get("is_enabled")),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialIngestionRecordListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialIngestionService.list_records(
            company_id=company_id,
            origin_type=request.args.get("origin_type"),
            completion_status=request.args.get("completion_status"),
            review_status=request.args.get("review_status"),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "create")
    def post(self):
        payload = request.get_json(silent=True) or {}
        payload["company_id"] = get_request_company_id()
        payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
        result, error = FinancialIngestionService.create_record(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialIngestionRecordResource(Resource):
    @permission_required("financial", "view")
    def get(self, record_id: int):
        company_id = get_request_company_id()
        result, error = FinancialIngestionService.get_record(
            record_id=record_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 404
        return result, 200

    @permission_required("financial", "edit")
    def put(self, record_id: int):
        company_id = get_request_company_id()
        payload = _sanitize_update_payload(request.get_json(silent=True), "record_id", "import_batch_id")
        result, error = FinancialIngestionService.update_record(
            record_id=record_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
            audit_context={
                "event_type": "guided_review_update",
                "description": "Atualização da revisão guiada da ingestão financeira.",
                "actor": {
                    "user_id": getattr(current_user, "id", None),
                    "user_email": getattr(current_user, "email", None),
                    "user_name": getattr(current_user, "name", None),
                    "endpoint": request.path,
                    "method": request.method,
                },
                "metadata": {
                    "channel": "financial_ingestions_ui",
                },
            },
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialIngestionRecordReviewResource(Resource):
    @permission_required("financial", "edit")
    def post(self, record_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialIngestionService.review_record(
            record_id=record_id,
            company_id=company_id,
            review_status=str(payload.get("review_status") or "reviewed").strip().lower(),
            review_notes=payload.get("review_notes"),
            completion_status=payload.get("completion_status"),
            reviewed_by_user_id=getattr(current_user, "id", None),
            allowed_company_ids=get_accessible_company_ids(),
            audit_context={
                "description": "Decisão de revisão humana da ingestão financeira.",
                "actor": {
                    "user_id": getattr(current_user, "id", None),
                    "user_email": getattr(current_user, "email", None),
                    "user_name": getattr(current_user, "name", None),
                    "endpoint": request.path,
                    "method": request.method,
                },
                "metadata": {
                    "channel": "financial_ingestions_ui",
                },
            },
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialIngestionRecordConvertResource(Resource):
    @permission_required("financial", "edit")
    def post(self, record_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialIngestionService.convert_record(
            record_id=record_id,
            company_id=company_id,
            target_type=str(payload.get("target_type") or "schedule").strip().lower(),
            allowed_company_ids=get_accessible_company_ids(),
            audit_context={
                "actor": {
                    "user_id": getattr(current_user, "id", None),
                    "user_email": getattr(current_user, "email", None),
                    "user_name": getattr(current_user, "name", None),
                    "endpoint": request.path,
                    "method": request.method,
                },
                "metadata": {
                    "channel": "financial_ingestions_ui",
                },
            },
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialScheduleListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialScheduleService.list_schedules(
            company_id=company_id,
            status=request.args.get("status"),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "create")
    def post(self):
        payload = request.get_json(silent=True) or {}
        payload["company_id"] = get_request_company_id()
        result, error = FinancialScheduleService.create_schedule(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialScheduleOptionsResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        allowed_company_ids = get_accessible_company_ids()

        counterparties, error = FinancialCatalogService.list_items(
            catalog_type="counterparties",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return {"error": error}, 400

        chart_accounts, error = FinancialCatalogService.list_items(
            catalog_type="chart_accounts",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return {"error": error}, 400

        bank_accounts, error = FinancialCatalogService.list_items(
            catalog_type="bank_accounts",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return {"error": error}, 400

        cost_centers, error = FinancialCatalogService.list_items(
            catalog_type="cost_centers",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return {"error": error}, 400

        correction_indexes, error = FinancialCatalogService.list_items(
            catalog_type="correction_indexes",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return {"error": error}, 400

        discount_rules, error = FinancialCatalogService.list_items(
            catalog_type="discount_rules",
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return {"error": error}, 400

        enabled_domains, error = FinancialScheduleService.list_enabled_domains(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return {"error": error}, 400

        default_suggestions, error = FinancialScheduleService.list_default_suggestions(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return {"error": error}, 400

        budget_versions = (
            FinancialBudgetVersion.query.filter(
                FinancialBudgetVersion.company_id == company_id,
                FinancialBudgetVersion.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetVersion.period_start.desc(), FinancialBudgetVersion.id.desc())
            .all()
        )
        budget_lines = (
            FinancialBudgetLine.query.filter(
                FinancialBudgetLine.company_id == company_id,
                FinancialBudgetLine.deleted_at.is_(None),
                FinancialBudgetLine.is_active.is_(True),
            )
            .order_by(FinancialBudgetLine.line_order.asc(), FinancialBudgetLine.id.asc())
            .all()
        )
        budget_contracts = (
            FinancialBudgetContract.query.filter(
                FinancialBudgetContract.company_id == company_id,
                FinancialBudgetContract.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetContract.name.asc(), FinancialBudgetContract.id.asc())
            .all()
        )
        budget_documents = (
            FinancialBudgetDocument.query.filter(
                FinancialBudgetDocument.company_id == company_id,
                FinancialBudgetDocument.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetDocument.title.asc(), FinancialBudgetDocument.id.asc())
            .all()
        )

        return {
            "counterparties": counterparties,
            "chart_accounts": chart_accounts,
            "bank_accounts": bank_accounts,
            "cost_centers": cost_centers,
            "correction_indexes": correction_indexes,
            "discount_rules": discount_rules,
            "enabled_domains": enabled_domains,
            "default_suggestions": default_suggestions or {},
            "budget_versions": [
                {
                    "id": item.id,
                    "code": item.full_code or item.code,
                    "name": item.name,
                    "status": item.status,
                    "budget_category": getattr(item, "budget_category", None),
                    "is_default_suggestion": False,
                }
                for item in budget_versions
            ],
            "budget_lines": [
                {
                    "id": item.id,
                    "budget_version_id": item.budget_version_id,
                    "code": getattr(item, "full_code", None) or item.line_code,
                    "name": item.line_name,
                }
                for item in budget_lines
            ],
            "budget_contracts": [
                {
                    "id": item.id,
                    "budget_line_id": item.budget_line_id,
                    "code": getattr(item, "full_code", None) or item.contract_code,
                    "name": item.name,
                }
                for item in budget_contracts
            ],
            "budget_documents": [
                {
                    "id": item.id,
                    "budget_contract_id": item.budget_contract_id,
                    "code": getattr(item, "full_code", None) or item.document_code,
                    "name": item.title,
                    "is_default_suggestion": bool(getattr(item, "is_default_suggestion", False)),
                }
                for item in budget_documents
            ],
        }, 200


class FinancialScheduleResource(Resource):
    @permission_required("financial", "view")
    def get(self, schedule_id: int):
        company_id = get_request_company_id()
        result, error = FinancialScheduleService.get_schedule_detail(
            schedule_id=schedule_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 404
        return result, 200

    @permission_required("financial", "edit")
    def put(self, schedule_id: int):
        company_id = get_request_company_id()
        payload = _sanitize_update_payload(
            request.get_json(silent=True),
            "schedule_id",
            "schedule_code",
            "created_by_user_id",
            "created_by_employee_id",
            "created_by_agent",
        )
        result, error = FinancialScheduleService.update_schedule(
            schedule_id=schedule_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "delete")
    def delete(self, schedule_id: int):
        company_id = get_request_company_id()
        result, error = FinancialScheduleService.delete_schedule(
            schedule_id=schedule_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialScheduleToggleResource(Resource):
    @permission_required("financial", "edit")
    def post(self, schedule_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialScheduleService.toggle_schedule(
            schedule_id=schedule_id,
            company_id=company_id,
            status=str(payload.get("status") or "paused").strip().lower(),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialScheduleGenerateResource(Resource):
    @permission_required("financial", "edit")
    def post(self):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        run_until = payload.get("run_until") or request.args.get("run_until")
        schedule_id = payload.get("schedule_id") or request.args.get("schedule_id", type=int)
        run_until_date = None
        if run_until:
            try:
                run_until_date = datetime.strptime(str(run_until), "%Y-%m-%d").date()
            except ValueError:
                return {"error": "run_until inválido. Use YYYY-MM-DD."}, 400

        result, error = FinancialScheduleService.generate_due_entries(
            company_id=company_id,
            schedule_id=schedule_id,
            run_until=run_until_date,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialScheduleCreateEntryResource(Resource):
    @permission_required("financial", "edit")
    def post(self, schedule_id: int):
        company_id = get_request_company_id()
        result, error = FinancialScheduleService.create_entry_from_schedule(
            schedule_id=schedule_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialScheduleSettlementResource(Resource):
    @permission_required("financial", "edit")
    def post(self, schedule_id: int):
        company_id = get_request_company_id()
        payload = _attach_financial_actor_context(request.get_json(silent=True) or {})
        result, error = FinancialScheduleService.create_settlement_from_schedule(
            schedule_id=schedule_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialScheduleSettlementSimulationResource(Resource):
    @permission_required("financial", "view")
    def post(self, schedule_id: int):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "Empresa não informada."}, 400
        payload = request.get_json(silent=True) or {}
        result, error = FinancialSettlementCompositionService.simulate_settlement(
            company_id=company_id,
            schedule_id=schedule_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialScheduleAssistedSettlementResource(Resource):
    @permission_required("financial", "create")
    def post(self, schedule_id: int):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "Empresa não informada."}, 400
        payload = _attach_financial_actor_context(request.get_json(silent=True) or {})
        result, error = FinancialSettlementCompositionService.create_assisted_settlement(
            company_id=company_id,
            schedule_id=schedule_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialScheduleCalculationLogListResource(Resource):
    @permission_required("financial", "view")
    def get(self, schedule_id: int):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "Empresa não informada."}, 400

        result, error = FinancialTitleCalculationService.list_title_calculation_logs(
            company_id=company_id,
            schedule_id=schedule_id,
            allowed_company_ids=get_accessible_company_ids(),
            limit=request.args.get("limit", type=int),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialScheduleAttachmentListResource(Resource):
    @permission_required("financial", "edit")
    def post(self, schedule_id: int):
        company_id = get_request_company_id()
        uploaded_file = request.files.get("file")
        attachment, error = FinancialScheduleService.upload_attachment(
            schedule_id=schedule_id,
            company_id=company_id,
            file=uploaded_file,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return attachment, 201


class FinancialScheduleAttachmentResource(Resource):
    @permission_required("financial", "edit")
    def delete(self, schedule_id: int, attachment_id: str):
        company_id = get_request_company_id()
        result, error = FinancialScheduleService.delete_attachment(
            schedule_id=schedule_id,
            company_id=company_id,
            attachment_id=attachment_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialBorderoListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialBorderoService.list_borderos(
            company_id=company_id,
            bordero_type=request.args.get("bordero_type"),
            status=request.args.get("status"),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "create")
    def post(self):
        payload = request.get_json(silent=True) or {}
        payload["company_id"] = get_request_company_id()
        payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
        result, error = FinancialBorderoService.create_bordero(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialBorderoResource(Resource):
    @permission_required("financial", "view")
    def get(self, bordero_id: int):
        company_id = get_request_company_id()
        result, error = FinancialBorderoService.get_bordero_detail(
            bordero_id=bordero_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 404
        return result, 200

    @permission_required("financial", "edit")
    def put(self, bordero_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialBorderoService.update_bordero(
            bordero_id=bordero_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "delete")
    def delete(self, bordero_id: int):
        company_id = get_request_company_id()
        result, error = FinancialBorderoService.delete_bordero(
            bordero_id=bordero_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialBorderoSettlementListResource(Resource):
    @permission_required("financial", "create")
    def post(self, bordero_id: int):
        payload = request.get_json(silent=True) or {}
        payload["company_id"] = get_request_company_id()
        payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
        result, error = FinancialBorderoService.create_settlement(
            bordero_id=bordero_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialAutomationRuleListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialAutomationService.list_rules(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "create")
    def post(self):
        payload = request.get_json(silent=True) or {}
        payload["company_id"] = get_request_company_id()
        result, error = FinancialAutomationService.create_rule(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialAutomationRuleResource(Resource):
    @permission_required("financial", "edit")
    def put(self, rule_id: int):
        company_id = get_request_company_id()
        payload = _sanitize_update_payload(request.get_json(silent=True), "rule_id", "rule_code")
        result, error = FinancialAutomationService.update_rule(
            rule_id=rule_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialAutomationExecutionListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialAutomationService.list_executions(
            company_id=company_id,
            rule_id=request.args.get("rule_id", type=int),
            process_instance_id=request.args.get("process_instance_id", type=int),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialAutomationApplyInstanceResource(Resource):
    @permission_required("financial", "edit")
    def post(self, rule_id: int, process_instance_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialAutomationService.apply_rules_to_instance(
            company_id=company_id,
            rule_id=rule_id,
            process_instance_id=process_instance_id,
            trigger_status=payload.get("trigger_status"),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialProcessTriggerDispatchResource(Resource):
    @permission_required("financial", "edit")
    def post(self, process_instance_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialProcessTriggerService.dispatch_for_instance(
            company_id=company_id,
            process_instance_id=process_instance_id,
            trigger_status=payload.get("trigger_status"),
            event_name=str(payload.get("event_name") or "manual_dispatch"),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialEntryResource(Resource):
    @permission_required("financial", "view")
    def get(self, entry_id: int):
        company_id = get_request_company_id()
        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first_or_404()
        return _serialize_entry(entry), 200

    @permission_required("financial", "edit")
    def put(self, entry_id: int):
        company_id = get_request_company_id()
        payload = _sanitize_update_payload(
            request.get_json(),
            "entry_id",
            "entry_code",
            "created_by_user_id",
            "created_by_employee_id",
            "created_by_agent",
        )

        entry, error = FinancialService.update_entry(
            entry_id=entry_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400

        return _serialize_entry(entry), 200

    @permission_required("financial", "delete")
    def delete(self, entry_id: int):
        company_id = get_request_company_id()
        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first_or_404()

        try:
            entry.deleted_at = datetime.utcnow()
            db.session.commit()
            return {"message": "Lançamento financeiro removido com sucesso.", "id": entry.id}, 200
        except Exception:
            db.session.rollback()
            logger.exception("Erro ao remover lançamento financeiro %s", entry_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class FinancialEntryAllocationListResource(Resource):
    @permission_required("financial", "view")
    def get(self, entry_id: int):
        company_id = get_request_company_id()
        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first_or_404()

        allocations = FinancialEntryAllocation.query.filter(
            FinancialEntryAllocation.company_id == company_id,
            FinancialEntryAllocation.financial_entry_id == entry.id,
            FinancialEntryAllocation.deleted_at.is_(None),
        ).order_by(FinancialEntryAllocation.id.asc()).all()
        return financial_entry_allocations_schema.dump(allocations), 200

    @permission_required("financial", "edit")
    def put(self, entry_id: int):
        company_id = get_request_company_id()
        payload = request.get_json() or {}
        payload["company_id"] = company_id
        payload["financial_entry_id"] = entry_id

        allocations, error = FinancialService.replace_allocations(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400

        return financial_entry_allocations_schema.dump(allocations), 200


class FinancialEntrySettlementListResource(Resource):
    @permission_required("financial", "view")
    def get(self, entry_id: int):
        company_id = get_request_company_id()
        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first_or_404()

        settlements = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.financial_entry_id == entry.id,
            FinancialSettlement.deleted_at.is_(None),
        ).order_by(FinancialSettlement.settlement_date.asc(), FinancialSettlement.id.asc()).all()
        return FinancialService.serialize_settlement_list(
            settlements,
            include_components=True,
            entry_by_id={entry.id: entry},
        ), 200

    @permission_required("financial", "create")
    def post(self, entry_id: int):
        payload = _attach_financial_actor_context(request.get_json() or {})
        company_id = get_request_company_id()
        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first_or_404()
        linked_schedule_id = getattr(entry, "financial_schedule_id", None)
        if not linked_schedule_id:
            external_reference = str(getattr(entry, "external_reference", "") or "").strip()
            if external_reference.startswith("financial_schedule:"):
                raw_schedule_id = external_reference.split(":", 1)[1].strip()
                if raw_schedule_id.isdigit():
                    linked_schedule_id = int(raw_schedule_id)
        if linked_schedule_id:
            return {
                "error": "Este lançamento está vinculado a um Título Financeiro. Faça a baixa pelo fluxo do título.",
                "redirect_url": f"/financial/schedules/{linked_schedule_id}?company_id={company_id}&open_tab=baixas&entry_id={entry.id}",
            }, 409
        payload["company_id"] = company_id
        payload["financial_entry_id"] = entry_id

        settlement, error = FinancialService.create_settlement(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400

        return FinancialService.serialize_settlement(settlement, include_components=True), 201


class FinancialSettlementResource(Resource):
    @permission_required("financial", "view")
    def get(self, settlement_id: int):
        company_id = get_request_company_id()
        settlement = FinancialSettlement.query.filter(
            FinancialSettlement.id == settlement_id,
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
        ).first_or_404()
        return FinancialService.serialize_settlement(settlement, include_components=True), 200

    @permission_required("financial", "delete")
    def delete(self, settlement_id: int):
        company_id = get_request_company_id()
        settlement = FinancialSettlement.query.filter(
            FinancialSettlement.id == settlement_id,
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
        ).first_or_404()

        try:
            settlement.deleted_at = datetime.utcnow()
            entry = FinancialEntry.query.filter(
                FinancialEntry.id == settlement.financial_entry_id,
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
            ).first()
            if entry:
                _recalculate_entry_status(entry)
            db.session.commit()
            return {"message": "Baixa removida com sucesso.", "id": settlement.id}, 200
        except Exception:
            db.session.rollback()
            logger.exception("Erro ao remover baixa financeira %s", settlement_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class FinancialSettlementAttachmentListResource(Resource):
    @permission_required("financial", "create")
    def post(self, settlement_id: int):
        company_id = get_request_company_id()
        upload = request.files.get("file")
        if not upload:
            return {"error": "Arquivo não informado."}, 400

        attachment, error = FinancialService.upload_settlement_attachment(
            settlement_id=settlement_id,
            company_id=company_id,
            file=upload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return attachment, 201


class FinancialSettlementAttachmentResource(Resource):
    @permission_required("financial", "delete")
    def delete(self, settlement_id: int, attachment_id: str):
        company_id = get_request_company_id()
        removed, error = FinancialService.delete_settlement_attachment(
            settlement_id=settlement_id,
            company_id=company_id,
            attachment_id=attachment_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return removed, 200


class FinancialImportBatchListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        batches, error = FinancialImportService.list_import_batches(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return batches, 200

    @permission_required("financial", "create")
    def post(self):
        company_id = get_request_company_id()
        upload = request.files.get("file")
        if not upload:
            return {"error": "Arquivo de importação não informado."}, 400
        reconciliation_mode_raw = str(request.form.get("reconciliation_mode") or "").strip().lower()
        reconciliation_mode = reconciliation_mode_raw in {"1", "true", "yes", "on", "sim"}

        payload = {
            "company_id": company_id,
            "batch_code": request.form.get("batch_code"),
            "source_type": request.form.get("source_type"),
            "file_name": upload.filename,
            "uploaded_by_user_id": request.form.get("uploaded_by_user_id", type=int),
            "uploaded_by_employee_id": request.form.get("uploaded_by_employee_id", type=int),
            "created_by_agent": request.form.get("created_by_agent"),
            "notes": request.form.get("notes"),
            "metadata_json": {
                "bank_account_id": request.form.get("bank_account_id", type=int),
                "integration_channel": request.form.get("integration_channel"),
                "reconciliation_mode": reconciliation_mode,
            },
        }

        result, error = FinancialImportService.create_import_batch(
            payload=payload,
            file_bytes=upload.read(),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        if reconciliation_mode and result.get("batch", {}).get("id"):
            reconciliation_result, reconciliation_error = FinancialReconciliationService.auto_match_batch(
                batch_id=result["batch"]["id"],
                company_id=company_id,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if reconciliation_error:
                result["reconciliation_warning"] = reconciliation_error
            else:
                result["reconciliation"] = reconciliation_result
        return result, 201


class FinancialImportBatchResource(Resource):
    @permission_required("financial", "view")
    def get(self, batch_id: int):
        company_id = get_request_company_id()
        result, error = FinancialImportService.get_import_batch(
            batch_id=batch_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialImportBatchProcessResource(Resource):
    @permission_required("financial", "edit")
    def post(self, batch_id: int):
        company_id = get_request_company_id()
        result, error = FinancialImportService.process_import_batch(
            batch_id=batch_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialImportBatchReconcileResource(Resource):
    @permission_required("financial", "edit")
    def post(self, batch_id: int):
        company_id = get_request_company_id()
        result, error = FinancialReconciliationService.auto_match_batch(
            batch_id=batch_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialReconciliationMatchReviewResource(Resource):
    @permission_required("financial", "edit")
    def post(self, match_id: int):
        company_id = get_request_company_id()
        payload = request.get_json() or {}
        result, error = FinancialReconciliationService.review_match(
            match_id=match_id,
            company_id=company_id,
            decision=str(payload.get("decision") or "").strip().lower(),
            selected_entry_id=payload.get("selected_entry_id"),
            adjustments={
                "principal_amount": payload.get("principal_amount"),
                "interest_amount": payload.get("interest_amount"),
                "penalty_amount": payload.get("penalty_amount"),
                "discount_amount": payload.get("discount_amount"),
                "fee_amount": payload.get("fee_amount"),
                "other_adjustments_amount": payload.get("other_adjustments_amount"),
            },
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialBankReconciliationOverviewResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialReconciliationWorkspaceService.get_overview(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialBankReconciliationWorkspaceResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        bank_account_id = request.args.get("bank_account_id", type=int)
        if not bank_account_id:
            return {"error": "Conta bancária é obrigatória para abrir a conciliação."}, 400
        result, error = FinancialReconciliationWorkspaceService.get_workspace(
            company_id=company_id,
            bank_account_id=bank_account_id,
            batch_id=request.args.get("batch_id", type=int),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialBankReconciliationRowCandidatesResource(Resource):
    @permission_required("financial", "view")
    def get(self, row_id: int):
        company_id = get_request_company_id()
        result, error = FinancialReconciliationWorkspaceService.list_row_candidates(
            company_id=company_id,
            row_id=row_id,
            limit=request.args.get("limit", type=int) or 8,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return {"items": result, "count": len(result)}, 200


class FinancialBankReconciliationRowMatchResource(Resource):
    @permission_required("financial", "edit")
    def post(self, row_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialReconciliationService.manually_match_row(
            company_id=company_id,
            row_id=row_id,
            financial_entry_id=int(payload.get("financial_entry_id") or 0),
            adjustments={
                "principal_amount": payload.get("principal_amount"),
                "interest_amount": payload.get("interest_amount"),
                "penalty_amount": payload.get("penalty_amount"),
                "discount_amount": payload.get("discount_amount"),
                "fee_amount": payload.get("fee_amount"),
                "other_adjustments_amount": payload.get("other_adjustments_amount"),
            },
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialBankReconciliationCreateEntryResource(Resource):
    @permission_required("financial", "create")
    def post(self, row_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialReconciliationWorkspaceService.create_entry_from_row(
            company_id=company_id,
            row_id=row_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialClassificationRuleListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialClassificationService.list_rules(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "create")
    def post(self):
        payload = request.get_json() or {}
        payload["company_id"] = get_request_company_id()
        result, error = FinancialClassificationService.create_rule(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialClassificationRuleResource(Resource):
    @permission_required("financial", "edit")
    def put(self, rule_id: int):
        company_id = get_request_company_id()
        payload = _sanitize_update_payload(request.get_json(silent=True), "rule_id")
        result, error = FinancialClassificationService.update_rule(
            rule_id=rule_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialClassificationRuleToggleResource(Resource):
    @permission_required("financial", "edit")
    def post(self, rule_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialClassificationService.toggle_rule(
            rule_id=rule_id,
            company_id=company_id,
            is_active=bool(payload.get("is_active")),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialImportBatchClassifyResource(Resource):
    @permission_required("financial", "edit")
    def post(self, batch_id: int):
        company_id = get_request_company_id()
        result, error = FinancialClassificationService.classify_batch(
            batch_id=batch_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialClassificationMemoryListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialClassificationHybridService.list_memories(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialClassificationMemoryResource(Resource):
    @permission_required("financial", "edit")
    def put(self, memory_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialClassificationHybridService.update_memory(
            memory_id=memory_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialClassificationMemoryToggleResource(Resource):
    @permission_required("financial", "edit")
    def post(self, memory_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialClassificationHybridService.toggle_memory(
            memory_id=memory_id,
            company_id=company_id,
            is_active=bool(payload.get("is_active")),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialImportBatchSuggestionResource(Resource):
    @permission_required("financial", "edit")
    def post(self, batch_id: int):
        company_id = get_request_company_id()
        result, error = FinancialClassificationHybridService.suggest_from_memory(
            batch_id=batch_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialClassificationSuggestionListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        batch_id = request.args.get("batch_id", type=int)
        result, error = FinancialClassificationHybridService.list_suggestions(
            company_id=company_id,
            batch_id=batch_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialClassificationSuggestionReviewResource(Resource):
    @permission_required("financial", "edit")
    def post(self, suggestion_id: int):
        company_id = get_request_company_id()
        payload = request.get_json() or {}
        result, error = FinancialClassificationHybridService.review_suggestion(
            suggestion_id=suggestion_id,
            company_id=company_id,
            decision=str(payload.get("decision") or "").strip().lower(),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialClassificationPendingQueueResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        batch_id = request.args.get("batch_id", type=int)
        result, error = FinancialClassificationHybridService.list_pending_queue(
            company_id=company_id,
            batch_id=batch_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialClassificationDashboardResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialClassificationDashboardService.get_dashboard(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialClassificationAskUserResource(Resource):
    @permission_required("financial", "edit")
    def post(self, import_row_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        preferred_channel = str(payload.get("channel") or "").strip().lower() or None
        result, error = FinancialClassificationQuestionService.dispatch_question_to_user(
            company_id=company_id,
            import_row_id=import_row_id,
            user_id=current_user.id,
            preferred_channel=preferred_channel,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialClassificationResolveAnswerResource(Resource):
    @permission_required("financial", "edit")
    def post(self, import_row_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialClassificationHybridService.resolve_user_answer(
            company_id=company_id,
            import_row_id=import_row_id,
            answer_payload=payload,
            user_id=getattr(current_user, "id", None),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialImportBatchAIRankingResource(Resource):
    @permission_required("financial", "edit")
    def post(self, batch_id: int):
        company_id = get_request_company_id()
        result, error = FinancialAIClassificationService.rank_batch_with_ai(
            batch_id=batch_id,
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialReportTypeListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialReportService.list_report_types(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialReportGenerateResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        report_type = request.args.get("report_type")
        period_start = request.args.get("period_start")
        period_end = request.args.get("period_end")
        result, error = FinancialReportService.generate_report(
            company_id=company_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialExecutiveDashboardResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialExecutiveDashboardService.get_dashboard(
            company_id=company_id,
            period_start=request.args.get("period_start"),
            period_end=request.args.get("period_end"),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200
