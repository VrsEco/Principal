from __future__ import annotations

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from api.routes.projects import get_active_company
from services.internal_audit_service import InternalAuditService, InternalAuditServiceError
from utils.permissions import can_access_company, has_company_full_access


internal_audit_bp = Blueprint("internal_audit", __name__)


def _active_company_or_400():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não encontrada para Auditoria Interna.")
    if not can_access_company(company.id):
        abort(403, description="Acesso negado à empresa ativa.")
    return company


def _active_company_or_redirect():
    company = get_active_company()
    if not company:
        return None
    if not can_access_company(company.id):
        abort(403, description="Acesso negado à empresa ativa.")
    return company


def _can_manage(company_id: int) -> bool:
    return has_company_full_access(company_id) or InternalAuditService.is_auditor(
        company_id,
        getattr(current_user, "id", None),
        roles={"auditor_admin", "auditor"},
    )


def _ensure_manage(company_id: int) -> None:
    if not _can_manage(company_id):
        abort(403, description="Acesso negado: operação exige perfil de auditoria com escrita.")


def _payload() -> dict:
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def _json_result(factory, status=200):
    try:
        return jsonify({"success": True, "data": factory()}), status
    except InternalAuditServiceError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@internal_audit_bp.route("/internal-audit")
@login_required
def dashboard_page():
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template(
        "modules/internal_audit/dashboard.html",
        company=company,
        company_id=company.id,
        summary=InternalAuditService.summary(company.id),
    )


@internal_audit_bp.route("/internal-audit/areas")
@login_required
def areas_page():
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template("modules/internal_audit/areas.html", company=company, company_id=company.id)


@internal_audit_bp.route("/internal-audit/auditors")
@login_required
def auditors_page():
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template("modules/internal_audit/auditors.html", company=company, company_id=company.id)


@internal_audit_bp.route("/internal-audit/checklists")
@login_required
def checklists_page():
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template("modules/internal_audit/checklists.html", company=company, company_id=company.id)


@internal_audit_bp.route("/api/internal-audit/summary")
@login_required
def api_summary():
    company = _active_company_or_400()
    return jsonify({"success": True, "data": InternalAuditService.summary(company.id)})


@internal_audit_bp.route("/api/internal-audit/options")
@login_required
def api_options():
    company = _active_company_or_400()
    return jsonify(
        {
            "success": True,
            "data": {
                "areas": InternalAuditService.list_areas(company.id),
                "auditors": InternalAuditService.list_auditors(company.id),
                "users": InternalAuditService.list_candidate_users(company.id),
            },
        }
    )


@internal_audit_bp.route("/api/internal-audit/areas", methods=["GET", "POST"])
@login_required
def api_areas():
    company = _active_company_or_400()
    if request.method == "GET":
        return jsonify({"success": True, "data": InternalAuditService.list_areas(company.id)})
    _ensure_manage(company.id)
    return _json_result(lambda: InternalAuditService.create_area(company.id, _payload()), status=201)


@internal_audit_bp.route("/api/internal-audit/auditors", methods=["GET", "POST"])
@login_required
def api_auditors():
    company = _active_company_or_400()
    if request.method == "GET":
        return jsonify({"success": True, "data": InternalAuditService.list_auditors(company.id)})
    _ensure_manage(company.id)
    return _json_result(lambda: InternalAuditService.create_auditor(company.id, _payload()), status=201)


@internal_audit_bp.route("/api/internal-audit/checklists", methods=["GET", "POST"])
@login_required
def api_checklists():
    company = _active_company_or_400()
    if request.method == "GET":
        return jsonify({"success": True, "data": InternalAuditService.list_checklists(company.id)})
    _ensure_manage(company.id)
    return _json_result(lambda: InternalAuditService.create_checklist(company.id, _payload()), status=201)


@internal_audit_bp.route("/api/internal-audit/checklists/<int:checklist_id>", methods=["GET"])
@login_required
def api_checklist_detail(checklist_id: int):
    company = _active_company_or_400()
    return _json_result(lambda: InternalAuditService.get_checklist(company.id, checklist_id))


@internal_audit_bp.route("/api/internal-audit/checklists/<int:checklist_id>/items", methods=["POST"])
@login_required
def api_checklist_items(checklist_id: int):
    company = _active_company_or_400()
    _ensure_manage(company.id)
    return _json_result(
        lambda: InternalAuditService.create_checklist_item(company.id, checklist_id, _payload()),
        status=201,
    )
