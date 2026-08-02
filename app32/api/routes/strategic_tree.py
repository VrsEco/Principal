from __future__ import annotations

import secrets

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required

from services.knowledge.strategic_tree_policy import StrategicTreeActor
from services.knowledge.strategic_tree_service import StrategicTreeError, StrategicTreeService
from utils.company_access import get_accessible_company_ids
from utils.permissions import can_access_company, get_access_profile


strategic_tree_bp = Blueprint(
    "strategic_tree",
    __name__,
    url_prefix="/api/knowledge/strategic-trees",
)
service = StrategicTreeService()


def _actor() -> StrategicTreeActor:
    company_id = session.get("active_company_id")
    try:
        company_id = int(company_id)
    except (TypeError, ValueError):
        raise PermissionError("Selecione uma empresa antes de acessar a Árvore Estratégica.")
    if not can_access_company(company_id, user=current_user):
        raise PermissionError("Empresa fora do escopo autorizado.")
    accessible = get_accessible_company_ids(current_user)
    return StrategicTreeActor(
        user_id=int(current_user.id),
        company_id=company_id,
        profile=str(get_access_profile(company_id, user=current_user) or "collaborator"),
        accessible_company_ids=tuple(accessible or ()),
    )


def _error_response(exc: Exception):
    if isinstance(exc, PermissionError):
        return jsonify({"success": False, "error": str(exc)}), 403
    if isinstance(exc, StrategicTreeError):
        return jsonify({"success": False, "error": str(exc)}), 400
    raise exc


def _require_csrf() -> None:
    expected = str(session.get("strategic_tree_csrf_token") or "")
    received = str(request.headers.get("X-CSRF-Token") or "")
    if not expected or not received or not secrets.compare_digest(expected, received):
        raise PermissionError("Token de segurança inválido. Recarregue a página e tente novamente.")


@strategic_tree_bp.get("")
@login_required
def list_strategic_trees():
    try:
        return jsonify({"success": True, **service.list_trees(_actor())})
    except (PermissionError, StrategicTreeError) as exc:
        return _error_response(exc)


@strategic_tree_bp.post("")
@login_required
def create_strategic_tree():
    data = request.get_json(silent=True) or {}
    try:
        _require_csrf()
        result = service.create_tree(
            _actor(),
            title=data.get("title"),
            purpose=data.get("purpose"),
            surface="app32",
        )
        return jsonify({"success": True, **result}), 201
    except (PermissionError, StrategicTreeError) as exc:
        return _error_response(exc)


@strategic_tree_bp.get("/<int:tree_id>")
@login_required
def get_strategic_tree(tree_id: int):
    try:
        return jsonify({"success": True, **service.get_tree(_actor(), tree_id)})
    except (PermissionError, StrategicTreeError) as exc:
        return _error_response(exc)


@strategic_tree_bp.get("/<int:tree_id>/nodes/<int:node_id>")
@login_required
def get_strategic_tree_branch(tree_id: int, node_id: int):
    try:
        return jsonify({"success": True, **service.get_branch(_actor(), tree_id=tree_id, node_id=node_id)})
    except (PermissionError, StrategicTreeError) as exc:
        return _error_response(exc)


@strategic_tree_bp.post("/<int:tree_id>/contributions")
@login_required
def add_strategic_tree_contribution(tree_id: int):
    data = request.get_json(silent=True) or {}
    idempotency_key = request.headers.get("Idempotency-Key") or data.get("idempotency_key")
    try:
        _require_csrf()
        result = service.add_contribution(
            _actor(),
            tree_id=tree_id,
            node_id=data.get("node_id"),
            content=data.get("content"),
            attribution_mode=data.get("attribution_mode", "identified"),
            visibility_scope=data.get("visibility_scope", "company_authorized"),
            source_type="app32",
            idempotency_key=idempotency_key,
            surface="app32",
        )
        return jsonify({"success": True, **result}), 201 if result.get("created") else 200
    except (PermissionError, StrategicTreeError) as exc:
        return _error_response(exc)
