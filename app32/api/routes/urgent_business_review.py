from __future__ import annotations

from typing import Any

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from api.routes.projects import get_active_company
from services.business_review_read_model_service import BusinessReviewReadModelService
from services.business_review_service import BusinessReviewService
from services.structural_learning_service import StructuralLearningService
from services.urgent_business_review_common import UrgentBusinessReviewError
from services.urgent_need_service import UrgentNeedService
from utils.permissions import has_company_full_access


urgent_business_review_bp = Blueprint("urgent_business_review", __name__)


def _active_company_or_400():
    company = get_active_company()
    if company is None:
        abort(400, description="Empresa ativa não encontrada para camada consultiva.")
    return company


def _payload() -> dict[str, Any]:
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        abort(400, description="Payload JSON inválido.")
    return data


def _ensure_write_access(company_id: int) -> None:
    if not has_company_full_access(company_id):
        abort(403, description="Acesso negado: operação consultiva exige permissão plena na empresa.")


def _error_response(exc: Exception, status_code: int = 400):
    return jsonify({"error": str(exc)}), status_code


@urgent_business_review_bp.route("/api/consultive/cockpit", methods=["GET"])
@login_required
def get_consultive_cockpit():
    company = _active_company_or_400()
    try:
        result = BusinessReviewReadModelService.get_cockpit(
            company_id=company.id,
            limit=request.args.get("limit", default=20, type=int) or 20,
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify(result)


@urgent_business_review_bp.route("/api/consultive/cockpit/structural-fronts/<front_key>/analysis", methods=["GET"])
@login_required
def get_consultive_structural_front_analysis(front_key: str):
    company = _active_company_or_400()
    try:
        result = BusinessReviewReadModelService.get_structural_front_analysis(
            company_id=company.id,
            front_key=front_key,
        )
    except ValueError as exc:
        return _error_response(exc, status_code=404)
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify(result)


@urgent_business_review_bp.route("/consultive/cockpit", methods=["GET"])
@login_required
def consultive_cockpit_page():
    company = get_active_company()
    if company is None:
        return redirect(url_for("auth.portal"))
    return render_template(
        "modules/consultive/business_review_cockpit.html",
        company=company,
        active_company=company,
        company_id=company.id,
        page_title="Cockpit Consultivo",
    )


@urgent_business_review_bp.route("/api/consultive/urgent-needs", methods=["GET"])
@login_required
def list_urgent_needs():
    company = _active_company_or_400()
    try:
        result = UrgentNeedService.list_urgent_needs(
            company_id=company.id,
            status=request.args.get("status") or None,
            urgency_level=request.args.get("urgency_level") or None,
            limit=request.args.get("limit", default=100, type=int) or 100,
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify({"items": result})


@urgent_business_review_bp.route("/api/consultive/urgent-needs", methods=["POST"])
@login_required
def create_urgent_need():
    company = _active_company_or_400()
    _ensure_write_access(company.id)
    data = _payload()
    try:
        row = UrgentNeedService.create_urgent_need(
            company_id=company.id,
            title=data.get("title"),
            description=data.get("description"),
            urgency_level=data.get("urgency_level") or "medium",
            criticality_level=data.get("criticality_level") or "operational",
            origin_channel=data.get("origin_channel"),
            origin_summary=data.get("origin_summary"),
            project_id=data.get("project_id"),
            project_task_id=data.get("project_task_id"),
            process_id=data.get("process_id"),
            process_instance_id=data.get("process_instance_id"),
            routine_id=data.get("routine_id"),
            indicator_id=data.get("indicator_id"),
            meeting_id=data.get("meeting_id"),
            occurrence_id=data.get("occurrence_id"),
            financial_ref_id=data.get("financial_ref_id"),
            source_type=data.get("source_type"),
            source_ref_id=data.get("source_ref_id"),
            source_payload=data.get("source_payload") if isinstance(data.get("source_payload"), dict) else None,
            business_impact_summary=data.get("business_impact_summary"),
            operational_impact_summary=data.get("operational_impact_summary"),
            risk_summary=data.get("risk_summary"),
            responsible_employee_id=data.get("responsible_employee_id"),
            created_by_user_id=getattr(current_user, "id", None),
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify(row.to_dict()), 201


@urgent_business_review_bp.route("/api/consultive/urgent-needs/<int:urgent_need_id>/decision", methods=["POST"])
@login_required
def update_urgent_need_decision(urgent_need_id: int):
    company = _active_company_or_400()
    _ensure_write_access(company.id)
    data = _payload()
    try:
        row = UrgentNeedService.update_decision(
            company_id=company.id,
            urgent_need_id=urgent_need_id,
            decision_status=data.get("decision_status") or "pending",
            decision_summary=data.get("decision_summary"),
            updated_by_user_id=getattr(current_user, "id", None),
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify(row.to_dict())


@urgent_business_review_bp.route("/api/consultive/urgent-needs/<int:urgent_need_id>/status", methods=["POST"])
@login_required
def change_urgent_need_status(urgent_need_id: int):
    company = _active_company_or_400()
    _ensure_write_access(company.id)
    data = _payload()
    try:
        row = UrgentNeedService.change_status(
            company_id=company.id,
            urgent_need_id=urgent_need_id,
            status=data.get("status") or "inbox",
            updated_by_user_id=getattr(current_user, "id", None),
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify(row.to_dict())


@urgent_business_review_bp.route("/api/consultive/business-reviews", methods=["GET"])
@login_required
def list_business_reviews():
    company = _active_company_or_400()
    try:
        result = BusinessReviewService.list_reviews(
            company_id=company.id,
            status=request.args.get("status") or None,
            review_type=request.args.get("review_type") or None,
            urgent_need_id=request.args.get("urgent_need_id", type=int),
            limit=request.args.get("limit", default=100, type=int) or 100,
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify({"items": result})


@urgent_business_review_bp.route("/api/consultive/business-reviews", methods=["POST"])
@login_required
def create_business_review():
    company = _active_company_or_400()
    _ensure_write_access(company.id)
    data = _payload()
    try:
        row = BusinessReviewService.create_review(
            company_id=company.id,
            title=data.get("title"),
            review_type=data.get("review_type") or "urgent_need",
            status=data.get("status") or "draft",
            urgent_need_id=data.get("urgent_need_id"),
            project_id=data.get("project_id"),
            project_task_id=data.get("project_task_id"),
            process_id=data.get("process_id"),
            indicator_id=data.get("indicator_id"),
            meeting_id=data.get("meeting_id"),
            cost_to_act=data.get("cost_to_act"),
            cost_to_not_act=data.get("cost_to_not_act"),
            required_investment=data.get("required_investment"),
            expected_gain=data.get("expected_gain"),
            expected_return=data.get("expected_return"),
            risk_level=data.get("risk_level") or "medium",
            risk_acceptance_decision=bool(data.get("risk_acceptance_decision")),
            risk_acceptance_reason=data.get("risk_acceptance_reason"),
            decision_summary=data.get("decision_summary"),
            structural_learning_summary=data.get("structural_learning_summary"),
            next_action=data.get("next_action"),
            responsible_employee_id=data.get("responsible_employee_id"),
            created_by_user_id=getattr(current_user, "id", None),
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify(row.to_dict()), 201


@urgent_business_review_bp.route("/api/consultive/business-reviews/<int:review_id>/decision", methods=["POST"])
@login_required
def update_business_review_decision(review_id: int):
    company = _active_company_or_400()
    _ensure_write_access(company.id)
    data = _payload()
    try:
        row = BusinessReviewService.update_review_decision(
            company_id=company.id,
            review_id=review_id,
            status=data.get("status") or "pending_decision",
            title=data.get("title"),
            decision_summary=data.get("decision_summary"),
            structural_learning_summary=data.get("structural_learning_summary"),
            next_action=data.get("next_action"),
            risk_acceptance_decision=data.get("risk_acceptance_decision"),
            risk_acceptance_reason=data.get("risk_acceptance_reason"),
            reviewed_by_user_id=getattr(current_user, "id", None),
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify(row.to_dict())


@urgent_business_review_bp.route("/api/consultive/structural-learning-links", methods=["GET"])
@login_required
def list_structural_learning_links():
    company = _active_company_or_400()
    try:
        result = StructuralLearningService.list_learning_links(
            company_id=company.id,
            business_review_id=request.args.get("business_review_id", type=int),
            urgent_need_id=request.args.get("urgent_need_id", type=int),
            limit=request.args.get("limit", default=100, type=int) or 100,
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify({"items": result})


@urgent_business_review_bp.route("/api/consultive/structural-learning-links", methods=["POST"])
@login_required
def create_structural_learning_link():
    company = _active_company_or_400()
    _ensure_write_access(company.id)
    data = _payload()
    try:
        row = StructuralLearningService.create_learning_link(
            company_id=company.id,
            business_review_id=data.get("business_review_id"),
            urgent_need_id=data.get("urgent_need_id"),
            target_project_id=data.get("target_project_id"),
            target_project_task_id=data.get("target_project_task_id"),
            target_process_id=data.get("target_process_id"),
            target_routine_id=data.get("target_routine_id"),
            target_indicator_id=data.get("target_indicator_id"),
            target_meeting_id=data.get("target_meeting_id"),
            learning_type=data.get("learning_type"),
            action_decision=data.get("action_decision") or "recommended",
            accepted_risk_reason=data.get("accepted_risk_reason"),
            recommended_change=data.get("recommended_change"),
            created_project_id=data.get("created_project_id"),
            created_task_id=data.get("created_task_id"),
            created_by_user_id=getattr(current_user, "id", None),
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify(row.to_dict()), 201


@urgent_business_review_bp.route(
    "/api/consultive/structural-learning-links/<int:learning_link_id>/decision",
    methods=["POST"],
)
@login_required
def update_structural_learning_decision(learning_link_id: int):
    company = _active_company_or_400()
    _ensure_write_access(company.id)
    data = _payload()
    try:
        row = StructuralLearningService.update_action_decision(
            company_id=company.id,
            learning_link_id=learning_link_id,
            action_decision=data.get("action_decision") or "recommended",
            accepted_risk_reason=data.get("accepted_risk_reason"),
            recommended_change=data.get("recommended_change"),
            updated_by_user_id=getattr(current_user, "id", None),
        )
    except UrgentBusinessReviewError as exc:
        return _error_response(exc)
    return jsonify(row.to_dict())


__all__ = ["urgent_business_review_bp"]
