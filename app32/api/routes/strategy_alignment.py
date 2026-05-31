from __future__ import annotations

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from api.routes.projects import get_active_company
from services.strategy_alignment_n1_service import StrategyAlignmentN1Error, StrategyAlignmentN1Service
from utils.permissions import has_company_full_access


strategy_alignment_bp = Blueprint("strategy_alignment", __name__)


def _active_company_or_400():
    company = get_active_company()
    if company is None:
        abort(400, description="Empresa ativa não encontrada para alinhamento estratégico.")
    return company


def _ensure_write_access(company_id: int) -> None:
    if not has_company_full_access(company_id):
        abort(403, description="Acesso negado: revisão estratégica exige permissão plena na empresa.")


@strategy_alignment_bp.route("/strategy/alignment-n1/maturation")
@login_required
def strategy_alignment_n1_maturation_page():
    company = get_active_company()
    if not company:
        return redirect(url_for("auth.portal"))
    return render_template(
        "modules/strategy/alignment_n1_maturation.html",
        company=company,
        company_id=company.id,
    )


@strategy_alignment_bp.route("/api/strategy-alignment-n1/maturation", methods=["GET"])
@login_required
def list_strategy_alignment_n1_maturation():
    company = _active_company_or_400()
    try:
        result = StrategyAlignmentN1Service.list_maturation_backlog(
            company_id=company.id,
            status=request.args.get("status") or None,
            block_type=request.args.get("block_type") or None,
            source=request.args.get("source") or None,
            state=request.args.get("state") or None,
            limit=request.args.get("limit", default=200, type=int) or 200,
        )
    except StrategyAlignmentN1Error as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@strategy_alignment_bp.route("/api/strategy-alignment-n1/maturation/<int:item_id>/review", methods=["POST"])
@login_required
def review_strategy_alignment_n1_maturation_item(item_id: int):
    company = _active_company_or_400()
    _ensure_write_access(company.id)
    payload = request.get_json(silent=True) or {}
    try:
        result = StrategyAlignmentN1Service.review_maturation_item(
            company_id=company.id,
            item_id=item_id,
            decision=str(payload.get("decision") or "").strip().lower(),
            reviewer_user_id=getattr(current_user, "id", None),
            notes=payload.get("notes"),
        )
    except StrategyAlignmentN1Error as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)
