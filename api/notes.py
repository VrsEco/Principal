"""
Notes API endpoints for the Ecossistema view.
"""

import logging

from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from services.notes_service import get_user_notes_payload

logger = logging.getLogger(__name__)

notes_bp = Blueprint("notes", __name__, url_prefix="/api/notes")


@notes_bp.route("/", methods=["GET"])
@login_required
def list_notes():
    """Return notes linked to the current user."""
    try:
        notes = get_user_notes_payload(current_user.id)
        return jsonify({"success": True, "notes": notes})
    except Exception as exc:
        logger.exception("Erro ao listar notas: %s", exc)
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Erro ao recuperar notas. Tente novamente.",
                }
            ),
            500,
        )
