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


@internal_audit_bp.route("/internal-audit/executions")
@login_required
def executions_page():
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template("modules/internal_audit/executions.html", company=company, company_id=company.id)


@internal_audit_bp.route("/internal-audit/executions/<int:execution_id>")
@login_required
def execution_detail_page(execution_id: int):
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template(
        "modules/internal_audit/execution_detail.html",
        company=company,
        company_id=company.id,
        execution_id=execution_id,
    )


@internal_audit_bp.route("/internal-audit/points")
@login_required
def points_page():
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template("modules/internal_audit/points.html", company=company, company_id=company.id)


@internal_audit_bp.route("/internal-audit/workpapers")
@login_required
def workpapers_page():
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template("modules/internal_audit/workpapers.html", company=company, company_id=company.id)


@internal_audit_bp.route("/internal-audit/findings")
@login_required
def findings_page():
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template("modules/internal_audit/findings.html", company=company, company_id=company.id)


@internal_audit_bp.route("/internal-audit/findings/<int:finding_id>")
@login_required
def finding_detail_page(finding_id: int):
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template(
        "modules/internal_audit/findings.html",
        company=company,
        company_id=company.id,
        finding_id=finding_id,
    )


@internal_audit_bp.route("/internal-audit/reports")
@login_required
def reports_page():
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template("modules/internal_audit/reports.html", company=company, company_id=company.id)


@internal_audit_bp.route("/internal-audit/reports/<int:report_id>/print")
@login_required
def report_print_page(report_id: int):
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    try:
        report = InternalAuditService.get_report(company.id, report_id)
    except InternalAuditServiceError:
        abort(404, description="Relatório de auditoria não encontrado.")
    return render_template(
        "modules/internal_audit/report_print.html",
        company=company,
        company_id=company.id,
        report=report,
    )


@internal_audit_bp.route("/internal-audit/follow-ups")
@login_required
def follow_ups_page():
    company = _active_company_or_redirect()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template("modules/internal_audit/follow_ups.html", company=company, company_id=company.id)


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


@internal_audit_bp.route("/api/internal-audit/executions", methods=["GET", "POST"])
@login_required
def api_executions():
    company = _active_company_or_400()
    if request.method == "GET":
        return jsonify({"success": True, "data": InternalAuditService.list_executions(company.id)})
    _ensure_manage(company.id)
    return _json_result(
        lambda: InternalAuditService.create_execution(
            company.id,
            _payload(),
            current_user_id=getattr(current_user, "id", None),
        ),
        status=201,
    )


@internal_audit_bp.route("/api/internal-audit/executions/<int:execution_id>", methods=["GET"])
@login_required
def api_execution_detail(execution_id: int):
    company = _active_company_or_400()
    return _json_result(lambda: InternalAuditService.get_execution(company.id, execution_id))


@internal_audit_bp.route("/api/internal-audit/execution-items/<int:execution_item_id>", methods=["PATCH", "POST"])
@login_required
def api_execution_item_update(execution_item_id: int):
    company = _active_company_or_400()
    _ensure_manage(company.id)
    return _json_result(
        lambda: InternalAuditService.update_execution_item(
            company.id,
            execution_item_id,
            _payload(),
            current_user_id=getattr(current_user, "id", None),
        )
    )


@internal_audit_bp.route("/api/internal-audit/points", methods=["GET", "POST"])
@login_required
def api_points():
    company = _active_company_or_400()
    if request.method == "GET":
        return jsonify({"success": True, "data": InternalAuditService.list_points(company.id, request.args.get("status"))})
    _ensure_manage(company.id)
    return _json_result(
        lambda: InternalAuditService.create_point(
            company.id,
            _payload(),
            current_user_id=getattr(current_user, "id", None),
        ),
        status=201,
    )


@internal_audit_bp.route("/api/internal-audit/points/<int:point_id>", methods=["GET", "PATCH", "POST"])
@login_required
def api_point_detail(point_id: int):
    company = _active_company_or_400()
    if request.method == "GET":
        return _json_result(lambda: InternalAuditService.get_point(company.id, point_id))
    _ensure_manage(company.id)
    return _json_result(lambda: InternalAuditService.update_point(company.id, point_id, _payload()))


@internal_audit_bp.route("/api/internal-audit/workpapers", methods=["GET", "POST"])
@login_required
def api_workpapers():
    company = _active_company_or_400()
    if request.method == "GET":
        return jsonify({"success": True, "data": InternalAuditService.list_workpapers(company.id)})
    _ensure_manage(company.id)
    return _json_result(
        lambda: InternalAuditService.create_workpaper(
            company.id,
            _payload(),
            current_user_id=getattr(current_user, "id", None),
        ),
        status=201,
    )


@internal_audit_bp.route("/api/internal-audit/workpapers/<int:workpaper_id>", methods=["GET"])
@login_required
def api_workpaper_detail(workpaper_id: int):
    company = _active_company_or_400()
    return _json_result(lambda: InternalAuditService.get_workpaper(company.id, workpaper_id))


@internal_audit_bp.route("/api/internal-audit/findings", methods=["GET", "POST"])
@login_required
def api_findings():
    company = _active_company_or_400()
    if request.method == "GET":
        return jsonify({"success": True, "data": InternalAuditService.list_findings(company.id, request.args.get("status"))})
    _ensure_manage(company.id)
    return _json_result(
        lambda: InternalAuditService.create_finding(
            company.id,
            _payload(),
            current_user_id=getattr(current_user, "id", None),
        ),
        status=201,
    )


@internal_audit_bp.route("/api/internal-audit/findings/<int:finding_id>", methods=["GET", "PATCH", "POST"])
@login_required
def api_finding_detail(finding_id: int):
    company = _active_company_or_400()
    if request.method == "GET":
        return _json_result(lambda: InternalAuditService.get_finding(company.id, finding_id))
    _ensure_manage(company.id)
    return _json_result(lambda: InternalAuditService.update_finding(company.id, finding_id, _payload()))


@internal_audit_bp.route("/api/internal-audit/evidence-links", methods=["POST"])
@login_required
def api_evidence_links():
    company = _active_company_or_400()
    _ensure_manage(company.id)
    return _json_result(
        lambda: InternalAuditService.create_evidence_link(
            company.id,
            _payload(),
            current_user_id=getattr(current_user, "id", None),
        ),
        status=201,
    )


@internal_audit_bp.route("/api/internal-audit/reports", methods=["GET", "POST"])
@login_required
def api_reports():
    company = _active_company_or_400()
    if request.method == "GET":
        return jsonify({"success": True, "data": InternalAuditService.list_reports(company.id)})
    _ensure_manage(company.id)
    return _json_result(
        lambda: InternalAuditService.create_report(
            company.id,
            _payload(),
            current_user_id=getattr(current_user, "id", None),
        ),
        status=201,
    )


@internal_audit_bp.route("/api/internal-audit/reports/<int:report_id>", methods=["GET", "PATCH", "POST"])
@login_required
def api_report_detail(report_id: int):
    company = _active_company_or_400()
    if request.method == "GET":
        return _json_result(lambda: InternalAuditService.get_report(company.id, report_id))
    _ensure_manage(company.id)
    return _json_result(lambda: InternalAuditService.update_report(company.id, report_id, _payload()))


@internal_audit_bp.route("/api/internal-audit/reports/<int:report_id>/issue", methods=["POST"])
@login_required
def api_report_issue(report_id: int):
    company = _active_company_or_400()
    _ensure_manage(company.id)
    return _json_result(
        lambda: InternalAuditService.issue_report(
            company.id,
            report_id,
            current_user_id=getattr(current_user, "id", None),
        )
    )


@internal_audit_bp.route("/api/internal-audit/follow-ups", methods=["GET", "POST"])
@login_required
def api_follow_ups():
    company = _active_company_or_400()
    if request.method == "GET":
        finding_id = request.args.get("finding_id", type=int)
        return jsonify(
            {"success": True, "data": InternalAuditService.list_follow_ups(company.id, finding_id)}
        )
    _ensure_manage(company.id)
    return _json_result(
        lambda: InternalAuditService.create_follow_up(
            company.id,
            _payload(),
            current_user_id=getattr(current_user, "id", None),
        ),
        status=201,
    )
