from __future__ import annotations

from flask import request
from flask_login import current_user
from flask_restful import Resource
from pydantic import ValidationError

from services.financial_budget_import_service import FinancialBudgetImportService
from services.financial_budget_service import FinancialBudgetService
from services.financial_budget_version_clone_service import FinancialBudgetVersionCloneService
from utils.company_access import get_accessible_company_ids
from utils.permissions import permission_required

from .process import get_request_company_id


class FinancialBudgetVersionListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório."}, 400
        result, error = FinancialBudgetService.list_versions(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "create")
    def post(self):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório."}, 400
        try:
            payload = request.get_json(silent=True) or {}
            payload["company_id"] = company_id
            payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
            result, error = FinancialBudgetService.create_version(
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if error:
                return {"error": error}, 400
            return result, 201
        except ValidationError as e:
            return {"errors": e.errors()}, 400


class FinancialBudgetVersionResource(Resource):
    @permission_required("financial", "view")
    def get(self, version_id: int):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório."}, 400
        result, error = FinancialBudgetService.get_version(
            company_id=company_id,
            version_id=version_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 404
        return result, 200

    @permission_required("financial", "edit")
    def put(self, version_id: int):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório."}, 400
        try:
            payload = request.get_json(silent=True) or {}
            result, error = FinancialBudgetService.update_version(
                company_id=company_id,
                version_id=version_id,
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if error:
                return {"error": error}, 400
            return result, 200
        except ValidationError as e:
            return {"errors": e.errors()}, 400

    @permission_required("financial", "delete")
    def delete(self, version_id: int):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório."}, 400
        result, error = FinancialBudgetService.delete_version(
            company_id=company_id,
            version_id=version_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialBudgetMatrixResource(Resource):
    @permission_required("financial", "view")
    def get(self, version_id: int):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório."}, 400
        result, error = FinancialBudgetService.get_matrix(
            company_id=company_id,
            version_id=version_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200

    @permission_required("financial", "edit")
    def put(self, version_id: int):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório."}, 400
        try:
            payload = request.get_json(silent=True) or {}
            payload["company_id"] = company_id
            payload["version_id"] = version_id
            result, error = FinancialBudgetService.upsert_matrix(
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if error:
                return {"error": error}, 400
            return result, 200
        except ValidationError as e:
            return {"errors": e.errors()}, 400


class FinancialBudgetOptionsResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório."}, 400
        result, error = FinancialBudgetService.list_options(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialBudgetImportResource(Resource):
    @permission_required("financial", "edit")
    def post(self, version_id: int):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório."}, 400

        upload = request.files.get("file")
        if not upload:
            return {"error": "Arquivo da matriz orçamentária não informado."}, 400

        result, error = FinancialBudgetImportService.import_matrix_file(
            company_id=company_id,
            version_id=version_id,
            file_name=upload.filename or "orcamento.xlsx",
            file_bytes=upload.read(),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            return {"error": error}, 400
        return result, 200


class FinancialBudgetVersionDuplicateResource(Resource):
    @permission_required("financial", "create")
    def post(self, version_id: int):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório."}, 400

        try:
            payload = request.get_json(silent=True) or {}
            payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
            result, error = FinancialBudgetVersionCloneService.duplicate_version(
                company_id=company_id,
                source_version_id=version_id,
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if error:
                return {"error": error}, 400
            return result, 201
        except ValidationError as e:
            return {"errors": e.errors()}, 400
