"""
Notes API endpoints for the Principal view.
"""

import logging

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from services.notes_service import (
    get_user_notes_payload,
    create_note,
    delete_note,
    update_note,
)

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


@notes_bp.route("/", methods=["POST"])
@login_required
def create_note_endpoint():
    """Create a new note for the current user."""
    try:
        data = request.get_json()
        
        if not data:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Dados inválidos. Envie um JSON válido.",
                    }
                ),
                400,
            )
        
        text = data.get("text", "").strip()
        location = data.get("location", "").strip() or None
        
        if not text:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "O texto da nota é obrigatório.",
                    }
                ),
                400,
            )
        
        note = create_note(
            user_id=current_user.id,
            text=text,
            location=location
        )
        
        return jsonify(
            {
                "success": True,
                "message": "Nota criada com sucesso!",
                "note": {
                    "id": note.id,
                    "code": note.code,
                    "text": note.text,
                    "location": note.location or "",
                    "status": note.status,
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                },
            }
        ), 201
    except ValueError as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(exc),
                }
            ),
            400,
        )
    except Exception as exc:
        logger.exception("Erro ao criar nota: %s", exc)
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Erro ao criar nota. Tente novamente.",
                }
            ),
            500,
        )


@notes_bp.route("/<int:note_id>", methods=["DELETE"])
@login_required
def delete_note_endpoint(note_id):
    """Delete a note if it belongs to the current user."""
    try:
        delete_note(note_id=note_id, user_id=current_user.id)
        
        return jsonify(
            {
                "success": True,
                "message": "Nota excluída com sucesso!",
            }
        )
    except ValueError as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(exc),
                }
            ),
            404 if "não encontrada" in str(exc) else 403,
        )
    except Exception as exc:
        logger.exception("Erro ao excluir nota %s: %s", note_id, exc)
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Erro ao excluir nota. Tente novamente.",
                }
            ),
            500,
        )


@notes_bp.route("/<int:note_id>", methods=["PUT"])
@login_required
def update_note_endpoint(note_id):
    """Update a note if it belongs to the current user."""
    try:
        data = request.get_json()
        
        if not data:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Dados inválidos. Envie um JSON válido.",
                    }
                ),
                400,
            )
        
        text = data.get("text")
        location = data.get("location")
        
        # At least one field must be provided
        if text is None and location is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Forneça pelo menos um campo para atualizar (text ou location).",
                    }
                ),
                400,
            )
        
        # Strip text if provided
        if text is not None:
            text = text.strip()
            if not text:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "O texto da nota não pode estar vazio.",
                        }
                    ),
                    400,
                )
        
        # Strip location if provided
        if location is not None:
            location = location.strip() or None
        
        note = update_note(
            note_id=note_id,
            user_id=current_user.id,
            text=text,
            location=location
        )
        
        return jsonify(
            {
                "success": True,
                "message": "Nota atualizada com sucesso!",
                "note": {
                    "id": note.id,
                    "code": note.code,
                    "text": note.text,
                    "location": note.location or "",
                    "status": note.status,
                    "created_at": note.created_at.isoformat() if note.created_at else None,
                },
            }
        )
    except ValueError as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(exc),
                }
            ),
            404 if "não encontrada" in str(exc) else 403,
        )
    except Exception as exc:
        logger.exception("Erro ao atualizar nota %s: %s", note_id, exc)
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Erro ao atualizar nota. Tente novamente.",
                }
            ),
            500,
        )

