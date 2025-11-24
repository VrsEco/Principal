import logging
from typing import List, Optional
import random

from models.note import Note
from models import db

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


def _generate_note_code() -> str:
    """
    Generate a unique note code in the format NT-XXXX.
    
    Returns:
        A unique note code string.
    """
    max_attempts = 100
    for _ in range(max_attempts):
        # Generate random 4-digit number
        number = random.randint(1000, 9999)
        code = f"NT-{number}"
        
        # Check if code already exists
        existing = Note.query.filter_by(code=code).first()
        if not existing:
            return code
    
    # Fallback: use timestamp-based code if random fails
    import time
    timestamp_suffix = str(int(time.time()))[-4:]
    return f"NT-{timestamp_suffix}"


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


def create_note(user_id: int, text: str, location: Optional[str] = None) -> Note:
    """
    Create a new note for the user.
    
    Args:
        user_id: ID of the user creating the note.
        text: Content of the note.
        location: Optional location/context information.
    
    Returns:
        The created Note instance.
    
    Raises:
        ValueError: If text is empty or invalid.
    """
    if not text or not text.strip():
        raise ValueError("O texto da nota não pode estar vazio.")
    
    try:
        code = _generate_note_code()
        
        note = Note(
            code=code,
            user_id=user_id,
            text=text.strip(),
            location=location.strip() if location else None,
            status="ativa"
        )
        
        db.session.add(note)
        db.session.commit()
        
        logger.info("Nota %s criada com sucesso para usuário %s", code, user_id)
        return note
    except Exception as exc:
        db.session.rollback()
        logger.exception("Erro ao criar nota para usuário %s: %s", user_id, exc)
        raise


def delete_note(note_id: int, user_id: int) -> bool:
    """
    Delete a note if it belongs to the user.
    
    Args:
        note_id: ID of the note to delete.
        user_id: ID of the user requesting deletion.
    
    Returns:
        True if deleted successfully.
    
    Raises:
        ValueError: If note doesn't exist or doesn't belong to user.
    """
    try:
        note = Note.query.filter_by(id=note_id).first()
        
        if not note:
            raise ValueError("Nota não encontrada.")
        
        if note.user_id != user_id:
            raise ValueError("Você não tem permissão para excluir esta nota.")
        
        db.session.delete(note)
        db.session.commit()
        
        logger.info("Nota %s excluída com sucesso pelo usuário %s", note.code, user_id)
        return True
    except Exception as exc:
        db.session.rollback()
        logger.exception("Erro ao excluir nota %s: %s", note_id, exc)
        raise


def update_note(
    note_id: int, user_id: int, text: Optional[str] = None, location: Optional[str] = None
) -> Note:
    """
    Update an existing note if it belongs to the user.
    
    Args:
        note_id: ID of the note to update.
        user_id: ID of the user requesting update.
        text: New text content (optional, keeps current if None).
        location: New location (optional, keeps current if None).
    
    Returns:
        The updated Note instance.
    
    Raises:
        ValueError: If note doesn't exist, doesn't belong to user, or data is invalid.
    """
    try:
        note = Note.query.filter_by(id=note_id).first()
        
        if not note:
            raise ValueError("Nota não encontrada.")
        
        if note.user_id != user_id:
            raise ValueError("Você não tem permissão para editar esta nota.")
        
        # Update text if provided
        if text is not None:
            text_stripped = text.strip()
            if not text_stripped:
                raise ValueError("O texto da nota não pode estar vazio.")
            note.text = text_stripped
        
        # Update location if provided (can be empty string to clear)
        if location is not None:
            note.location = location.strip() if location else None
        
        db.session.commit()
        
        logger.info("Nota %s atualizada com sucesso pelo usuário %s", note.code, user_id)
        return note
    except Exception as exc:
        db.session.rollback()
        logger.exception("Erro ao atualizar nota %s: %s", note_id, exc)
        raise

