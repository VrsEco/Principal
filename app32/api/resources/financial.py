from __future__ import annotations

import logging
from datetime import datetime

from flask import request
from flask_restful import Resource
from flask_login import current_user

from models import db, FinancialEntry, FinancialEntryAllocation, FinancialSchedule, FinancialSettlement
from schemas.financial import (
    financial_entry_allocation_schema,
    financial_entry_allocations_schema,
    financial_settlement_schema,
)
from services.financial_service import FinancialService
from services.financial_import_service import FinancialImportService
from services.financial_ingestion_service import FinancialIngestionService
from services.financial_direct_entry_service import FinancialDirectEntryService
from services.financial_classification_service import FinancialClassificationService
from services.financial_classification_hybrid_service import FinancialClassificationHybridService
from services.financial_classification_dashboard_service import FinancialClassificationDashboardService
from services.financial_catalog_service import FinancialCatalogService
from services.financial_closing_service import FinancialClosingService
from services.financial_domain_enablement_service import FinancialDomainEnablementService
from services.financial_report_service import FinancialReportService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_automation_service import FinancialAutomationService
from services.financial_process_trigger_service import FinancialProcessTriggerService
from services.financial_executive_dashboard_service import FinancialExecutiveDashboardService
from services.financial_ai_classification_service import FinancialAIClassificationService
from services.financial_classification_question_service import FinancialClassificationQuestionService
from services.financial_reconciliation_service import FinancialReconciliationService
from utils.company_access import get_accessible_company_ids
from utils.permissions import permission_required

from .process import get_request_company_id


logger = logging.getLogger(__name__)

PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."


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
        return [FinancialService.serialize_entry(entry, include_children=False) for entry in entries], 200

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
        payload = request.get_json(silent=True) or {}
        payload.pop("company_id", None)
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
        payload = request.get_json(silent=True) or {}
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
        payload = request.get_json(silent=True) or {}
        result, error = FinancialIngestionService.update_record(
            record_id=record_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
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

        return {
            "counterparties": counterparties,
            "chart_accounts": chart_accounts,
            "cost_centers": cost_centers,
            "correction_indexes": correction_indexes,
            "discount_rules": discount_rules,
            "enabled_domains": enabled_domains,
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
        payload = request.get_json(silent=True) or {}
        payload.pop("company_id", None)
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
        payload = request.get_json(silent=True) or {}
        payload.pop("company_id", None)
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
        payload = request.get_json() or {}
        payload.pop("company_id", None)

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
        return financial_settlements_schema.dump(settlements), 200

    @permission_required("financial", "create")
    def post(self, entry_id: int):
        payload = request.get_json() or {}
        company_id = get_request_company_id()
        payload["company_id"] = company_id
        payload["financial_entry_id"] = entry_id

        settlement, error = FinancialService.create_settlement(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400

        return financial_settlement_schema.dump(settlement), 201


class FinancialSettlementResource(Resource):
    @permission_required("financial", "view")
    def get(self, settlement_id: int):
        company_id = get_request_company_id()
        settlement = FinancialSettlement.query.filter(
            FinancialSettlement.id == settlement_id,
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
        ).first_or_404()
        return financial_settlement_schema.dump(settlement), 200

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
            return {"message": "Liquidação removida com sucesso.", "id": settlement.id}, 200
        except Exception:
            db.session.rollback()
            logger.exception("Erro ao remover liquidação financeira %s", settlement_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


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

        payload = {
            "company_id": company_id,
            "batch_code": request.form.get("batch_code"),
            "source_type": request.form.get("source_type"),
            "file_name": upload.filename,
            "uploaded_by_user_id": request.form.get("uploaded_by_user_id", type=int),
            "uploaded_by_employee_id": request.form.get("uploaded_by_employee_id", type=int),
            "created_by_agent": request.form.get("created_by_agent"),
            "notes": request.form.get("notes"),
            "metadata_json": {},
        }

        result, error = FinancialImportService.create_import_batch(
            payload=payload,
            file_bytes=upload.read(),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
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
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


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
        payload = request.get_json(silent=True) or {}
        payload.pop("company_id", None)
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


class FinancialClosingListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialClosingService.list_closings(
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
        result, error = FinancialClosingService.create_closing(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialClosingPreviewResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        period_start = request.args.get("period_start")
        period_end = request.args.get("period_end")
        if not period_start or not period_end:
            return {"error": "Informe period_start e period_end."}, 400

        from datetime import datetime

        try:
            period_start_date = datetime.strptime(period_start, "%Y-%m-%d").date()
            period_end_date = datetime.strptime(period_end, "%Y-%m-%d").date()
        except ValueError:
            return {"error": "Datas inválidas. Use YYYY-MM-DD."}, 400

        result, error = FinancialClosingService.preview_closing(
            company_id=company_id,
            period_start=period_start_date,
            period_end=period_end_date,
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
