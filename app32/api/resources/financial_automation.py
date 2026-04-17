from __future__ import annotations

from flask import request
from flask_login import current_user
from flask_restful import Resource

from services.financial_automation_service import FinancialAutomationService
from utils.company_access import get_accessible_company_ids
from utils.permissions import permission_required

from .process import get_request_company_id


class FinancialAutomationOptionsResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialAutomationService.list_options(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialAutomationBatchListResource(Resource):
    @permission_required("financial", "create")
    def post(self):
        payload = request.get_json(silent=True) or {}
        payload["company_id"] = get_request_company_id()
        payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
        result, error = FinancialAutomationService.create_batch(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 201


class FinancialAutomationRecordListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        result, error = FinancialAutomationService.list_records(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
            status=request.args.get("status"),
            origin_type=request.args.get("origin_type"),
            batch_id=request.args.get("batch_id", type=int),
            competence_date_from=request.args.get("competence_date_from"),
            competence_date_to=request.args.get("competence_date_to"),
            due_date_from=request.args.get("due_date_from"),
            due_date_to=request.args.get("due_date_to"),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialAutomationRecordResource(Resource):
    @permission_required("financial", "view")
    def get(self, record_id: int):
        company_id = get_request_company_id()
        result, error = FinancialAutomationService.get_record(
            company_id=company_id,
            record_id=record_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 404
        return result, 200

    @permission_required("financial", "edit")
    def put(self, record_id: int):
        company_id = get_request_company_id()
        payload = request.get_json(silent=True) or {}
        result, error = FinancialAutomationService.update_record(
            company_id=company_id,
            record_id=record_id,
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
            performed_by_user_id=getattr(current_user, "id", None),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialAutomationBulkStatusResource(Resource):
    @permission_required("financial", "edit")
    def post(self):
        payload = request.get_json(silent=True) or {}
        payload["company_id"] = get_request_company_id()
        result, error = FinancialAutomationService.bulk_update_status(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
            performed_by_user_id=getattr(current_user, "id", None),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialAutomationGenerateResource(Resource):
    @permission_required("financial", "create")
    def post(self):
        payload = request.get_json(silent=True) or {}
        payload["company_id"] = get_request_company_id()
        payload.setdefault("generated_by_user_id", getattr(current_user, "id", None))
        result, error = FinancialAutomationService.generate_records(
            payload=payload,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialAutomationDocumentResource(Resource):
    @permission_required("financial", "view")
    def get(self, document_id: int):
        company_id = get_request_company_id()
        result, error = FinancialAutomationService.get_document(
            company_id=company_id,
            document_id=document_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 404
        return result, 200
