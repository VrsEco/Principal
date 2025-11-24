import logging
from typing import List, Optional

from models.note import Note

logger = logging.getLogger(__name__)


def _serialize_note(note: Note) -> dict:
    """Return a JSON-serializable representation of a note."""
    return {
        "id": note.id,
        "code": note.code,
        "text": note.text,
        "location": note.location or "",
        "status": note.status,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


def get_user_notes(user_id: int, status: Optional[str] = "ativa") -> List[Note]:
    """
    Fetch notes belonging to the provided user.

    Args:
        user_id: ID of the logged user.
        status: Optional filter by status (default is 'ativa').

    Returns:
        List of Note instances ordered by creation date desc.
    """
    query = Note.query.filter(Note.user_id == user_id)
    if status:
        query = query.filter(Note.status == status)
    return query.order_by(Note.created_at.desc()).all()


def get_user_notes_payload(user_id: int, status: Optional[str] = "ativa") -> List[dict]:
    """Return serialized notes data for APIs."""
    try:
        notes = get_user_notes(user_id=user_id, status=status)
        return [_serialize_note(note) for note in notes]
    except Exception as exc:
        logger.exception("Erro ao listar notas do usuário %s: %s", user_id, exc)
        raise
