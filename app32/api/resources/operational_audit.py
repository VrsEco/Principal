from __future__ import annotations

from flask import request
from flask_restful import Resource
from pydantic import ValidationError

from schemas.operational_audit import OperationalAuditPanelQuery
from services.operational_audit_service import OperationalAuditService
from utils.company_access import get_accessible_company_ids
from utils.permissions import permission_required

from .process import get_request_company_id


class OperationalAuditPanelResource(Resource):
    """API REST do painel unificado de auditoria operacional."""

    @permission_required("financial", "view")
    def get(self):
        try:
            filters = OperationalAuditPanelQuery(**request.args.to_dict(flat=True))
        except ValidationError as exc:
            return {"error": "Filtros inválidos para auditoria operacional.", "details": exc.errors()}, 400

        company_id = filters.company_id or get_request_company_id()
        if not company_id:
            return {"error": "Informe a empresa para consultar a auditoria operacional."}, 400

        result, error = OperationalAuditService.build_panel(
            company_id=company_id,
            allowed_company_ids=get_accessible_company_ids(),
            source=filters.source,
            limit=filters.limit,
        )
        if error:
            return {"error": error}, 400
        return result, 200
