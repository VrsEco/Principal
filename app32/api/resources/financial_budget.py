from __future__ import annotations

from flask import request
from flask_login import current_user
from flask_restful import Resource
from pydantic import ValidationError

from services.financial_budget_import_service import FinancialBudgetImportService
from services.financial_budget_service import FinancialBudgetService
from services.financial_budget_version_clone_service import FinancialBudgetVersionCloneService
from services.financial_budget_workspace_service import FinancialBudgetWorkspaceService
from utils.company_access import get_accessible_company_ids
from utils.permissions import permission_required

from .process import get_request_company_id


def _get_company_id_or_error():
    company_id = get_request_company_id()
    if not company_id:
        return None, ({"error": "company_id é obrigatório."}, 400)
    return company_id, None


def _parse_bool_arg(name: str, default: bool = False) -> bool:
    raw = (request.args.get(name) or "").strip().lower()
    if raw in {"1", "true", "yes", "sim", "on"}:
        return True
    if raw in {"0", "false", "no", "nao", "não", "off"}:
        return False
    return default


class FinancialBudgetVersionListResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        budget_cycle = request.args.get("budget_cycle")
        budget_category = request.args.get("budget_category")
        budget_group = request.args.get("budget_group")
        consolidated = _parse_bool_arg("consolidated", default=False)
        group_by_cycle = _parse_bool_arg("group_by_cycle", default=False)
        group_by_category = _parse_bool_arg("group_by_category", default=False)
        include_summary = _parse_bool_arg("include_summary", default=False)
        result, service_error = FinancialBudgetService.list_versions(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
            budget_cycle=budget_cycle,
            budget_category=budget_category,
            budget_group=budget_group,
            consolidated=consolidated,
            group_by_cycle=group_by_cycle,
            group_by_category=group_by_category,
            include_summary=include_summary,
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200

    @permission_required("financial", "create")
    def post(self):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        try:
            payload = request.get_json(silent=True) or {}
            payload["company_id"] = company_id
            payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
            result, service_error = FinancialBudgetService.create_version(
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 201
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400


class FinancialBudgetVersionResource(Resource):
    @permission_required("financial", "view")
    def get(self, version_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetService.get_version(
            company_id=company_id,
            version_id=version_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 404
        return result, 200

    @permission_required("financial", "edit")
    def put(self, version_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        try:
            payload = request.get_json(silent=True) or {}
            result, service_error = FinancialBudgetService.update_version(
                company_id=company_id,
                version_id=version_id,
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 200
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400

    @permission_required("financial", "delete")
    def delete(self, version_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetService.delete_version(
            company_id=company_id,
            version_id=version_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200


class FinancialBudgetMatrixResource(Resource):
    @permission_required("financial", "view")
    def get(self, version_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetService.get_matrix(
            company_id=company_id,
            version_id=version_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200

    @permission_required("financial", "edit")
    def put(self, version_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        try:
            payload = request.get_json(silent=True) or {}
            payload["company_id"] = company_id
            payload["version_id"] = version_id
            result, service_error = FinancialBudgetService.upsert_matrix(
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 200
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400


class FinancialBudgetOptionsResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetWorkspaceService.list_options(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200


class FinancialBudgetImportResource(Resource):
    @permission_required("financial", "edit")
    def post(self, version_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error

        upload = request.files.get("file")
        if not upload:
            return {"error": "Arquivo da matriz orçamentária não informado."}, 400

        result, service_error = FinancialBudgetImportService.import_matrix_file(
            company_id=company_id,
            version_id=version_id,
            file_name=upload.filename or "orcamento.xlsx",
            file_bytes=upload.read(),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200


class FinancialBudgetVersionDuplicateResource(Resource):
    @permission_required("financial", "create")
    def post(self, version_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error

        try:
            payload = request.get_json(silent=True) or {}
            payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
            result, service_error = FinancialBudgetVersionCloneService.duplicate_version(
                company_id=company_id,
                source_version_id=version_id,
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 201
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400


class FinancialBudgetPlanningWorkspaceResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetWorkspaceService.get_planning_workspace(
            company_id=company_id,
            version_id=request.args.get("version_id", type=int),
            budget_cycle=request.args.get("budget_cycle"),
            budget_category=request.args.get("budget_category"),
            budget_group=request.args.get("budget_group"),
            consolidated=_parse_bool_arg("consolidated", default=False),
            group_by_cycle=_parse_bool_arg("group_by_cycle", default=False),
            group_by_category=_parse_bool_arg("group_by_category", default=False),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200


class FinancialBudgetExecutionWorkspaceResource(Resource):
    @permission_required("financial", "view")
    def get(self):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetWorkspaceService.get_execution_workspace(
            company_id=company_id,
            version_id=request.args.get("version_id", type=int),
            line_id=request.args.get("line_id", type=int),
            contract_id=request.args.get("contract_id", type=int),
            document_id=request.args.get("document_id", type=int),
            schedule_id=request.args.get("schedule_id", type=int),
            budget_cycle=request.args.get("budget_cycle"),
            budget_category=request.args.get("budget_category"),
            budget_group=request.args.get("budget_group"),
            consolidated=_parse_bool_arg("consolidated", default=False),
            group_by_cycle=_parse_bool_arg("group_by_cycle", default=False),
            group_by_category=_parse_bool_arg("group_by_category", default=False),
            include_operational_queue=_parse_bool_arg("include_operational_queue", default=False),
            queue_limit=request.args.get("queue_limit", type=int) or 50,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200


class FinancialBudgetLineListResource(Resource):
    @permission_required("financial", "create")
    def post(self, version_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        try:
            payload = request.get_json(silent=True) or {}
            payload["company_id"] = company_id
            payload["budget_version_id"] = version_id
            result, service_error = FinancialBudgetWorkspaceService.create_line(
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 201
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400


class FinancialBudgetLineResource(Resource):
    @permission_required("financial", "edit")
    def put(self, line_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        try:
            payload = request.get_json(silent=True) or {}
            result, service_error = FinancialBudgetWorkspaceService.update_line(
                company_id=company_id,
                line_id=line_id,
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 200
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400

    @permission_required("financial", "delete")
    def delete(self, line_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetWorkspaceService.delete_line(
            company_id=company_id,
            line_id=line_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200


class FinancialBudgetContractListResource(Resource):
    @permission_required("financial", "create")
    def post(self, line_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        try:
            payload = request.get_json(silent=True) or {}
            payload["company_id"] = company_id
            payload["budget_line_id"] = line_id
            payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
            result, service_error = FinancialBudgetWorkspaceService.create_contract(
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 201
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400


class FinancialBudgetContractResource(Resource):
    @permission_required("financial", "edit")
    def put(self, contract_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        try:
            payload = request.get_json(silent=True) or {}
            result, service_error = FinancialBudgetWorkspaceService.update_contract(
                company_id=company_id,
                contract_id=contract_id,
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 200
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400

    @permission_required("financial", "delete")
    def delete(self, contract_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetWorkspaceService.delete_contract(
            company_id=company_id,
            contract_id=contract_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200


class FinancialBudgetDocumentListResource(Resource):
    @permission_required("financial", "create")
    def post(self, contract_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        try:
            payload = request.get_json(silent=True) or {}
            payload["company_id"] = company_id
            payload["budget_contract_id"] = contract_id
            payload.setdefault("created_by_user_id", getattr(current_user, "id", None))
            result, service_error = FinancialBudgetWorkspaceService.create_document(
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 201
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400


class FinancialBudgetDocumentResource(Resource):
    @permission_required("financial", "edit")
    def put(self, document_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        try:
            payload = request.get_json(silent=True) or {}
            result, service_error = FinancialBudgetWorkspaceService.update_document(
                company_id=company_id,
                document_id=document_id,
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 200
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400

    @permission_required("financial", "delete")
    def delete(self, document_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetWorkspaceService.delete_document(
            company_id=company_id,
            document_id=document_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200


class FinancialBudgetDocumentScheduleListResource(Resource):
    @permission_required("financial", "view")
    def get(self, document_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetWorkspaceService.list_document_schedules(
            company_id=company_id,
            document_id=document_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200

    @permission_required("financial", "create")
    def post(self, document_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        try:
            payload = request.get_json(silent=True) or {}
            result, service_error = FinancialBudgetWorkspaceService.create_document_schedules(
                company_id=company_id,
                document_id=document_id,
                payload=payload,
                allowed_company_ids=get_accessible_company_ids(),
            )
            if service_error:
                return {"error": service_error}, 400
            return result, 201
        except ValidationError as exc:
            return {"errors": exc.errors()}, 400


class FinancialBudgetDocumentScheduleResource(Resource):
    @permission_required("financial", "delete")
    def delete(self, document_id: int, schedule_id: int):
        company_id, error = _get_company_id_or_error()
        if error:
            return error
        result, service_error = FinancialBudgetWorkspaceService.delete_document_schedule(
            company_id=company_id,
            document_id=document_id,
            schedule_id=schedule_id,
            allowed_company_ids=get_accessible_company_ids(),
        )
        if service_error:
            return {"error": service_error}, 400
        return result, 200
