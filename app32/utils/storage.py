import io
import mimetypes
import os
import uuid
import logging
from pathlib import Path
from flask import current_app, session, send_file, send_from_directory
from flask_login import current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename
from models import db
from utils.gcs_utils import upload_to_gcs, delete_from_gcs, download_from_gcs, get_gcs_config
from utils.permissions import can_access_company, get_default_company_id, is_platform_admin
from utils.security import normalize_relative_upload_path

logger = logging.getLogger(__name__)

def save_file(file, subfolder=""):
    """
    Saves a file to local storage or GCS depending on configuration.
    Returns the relative path to be stored in the database.
    """
    if not file or not file.filename:
        return None
    
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    
    # Try GCS first if configured
    if get_gcs_config():
        gcs_path = upload_to_gcs(file, unique_name, subfolder=subfolder)
        if gcs_path:
            return gcs_path
            
    # Local fallback
    upload_base = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    upload_dir = os.path.join(upload_base, subfolder) if subfolder else upload_base
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)
    
    # Return path relative to UPLOAD_FOLDER
    rel_path = os.path.join(subfolder, unique_name).replace("\\", "/") if subfolder else unique_name
    return rel_path

def delete_file(relative_path):
    """
    Deletes a file from either GCS or local storage.
    """
    if not relative_path:
        return False
        
    if get_gcs_config():
        return delete_from_gcs(relative_path)
        
    # Local fallback
    try:
        upload_base = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        full_path = os.path.join(upload_base, relative_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
    except Exception as e:
        logger.error(f"Error deleting local file {relative_path}: {e}")
        
    return False

def get_file_url(relative_path):
    """
    Converts relative path from database to a public URL.
    """
    if not relative_path:
        return None
    
    # If it's a full URL already (e.g. stored in DB from GCS directly)
    if relative_path.startswith(('http://', 'https://')):
        return relative_path
        
    return f"/uploads/{relative_path}"


def build_upload_file_response(relative_path):
    """
    Entrega upload a partir do disco local ou, em fallback, do GCS.

    Mantém a rota /uploads tenant-safe enquanto corrige mídias que foram
    persistidas apenas no bucket.
    """
    normalized_path = normalize_relative_upload_path(relative_path)
    if not normalized_path:
        raise FileNotFoundError("Invalid upload path")

    upload_base = current_app.config.get("UPLOAD_FOLDER", "uploads")
    absolute_path = os.path.join(upload_base, normalized_path)

    if os.path.exists(absolute_path):
        return send_from_directory(upload_base, normalized_path)

    gcs_payload = download_from_gcs(normalized_path) if get_gcs_config() else None
    if not gcs_payload:
        raise FileNotFoundError(normalized_path)

    content_type = gcs_payload.get("content_type") or mimetypes.guess_type(normalized_path)[0] or "application/octet-stream"
    return send_file(
        io.BytesIO(gcs_payload["bytes"]),
        mimetype=content_type,
        download_name=Path(normalized_path).name,
        conditional=False,
    )


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _current_company_context_id():
    """Resolve a empresa ativa da sessão, com fallback seguro para usuários monoempresa."""
    active_company_id = _as_int(session.get("active_company_id"))
    if active_company_id:
        return active_company_id
    return _as_int(get_default_company_id())


def _path_candidates(normalized_path):
    return {
        normalized_path,
        f"uploads/{normalized_path}",
        f"/uploads/{normalized_path}",
    }


def _query_upload_owner_company_ids(normalized_path):
    """
    Retorna empresas que referenciam o arquivo em entidades tenant-scoped.

    A rota /uploads não possui company_id na URL; portanto a autorização é
    derivada das tabelas que guardam o caminho do arquivo.
    """
    candidates = list(_path_candidates(normalized_path))

    query = text(
        """
        SELECT DISTINCT company_id
        FROM (
            SELECT p.company_id
              FROM processes p
             WHERE p.flow_document IN (:path_0, :path_1, :path_2)

            UNION ALL

            SELECT pr.company_id
              FROM process_steps ps
              JOIN process_routines pr ON pr.id = ps.routine_id
             WHERE ps.image_path IN (:path_0, :path_1, :path_2)
                OR ps.video_path IN (:path_0, :path_1, :path_2)

            UNION ALL

            SELECT r.company_id
              FROM process_steps ps
              JOIN routines r ON r.id = ps.routine_id
             WHERE ps.image_path IN (:path_0, :path_1, :path_2)
                OR ps.video_path IN (:path_0, :path_1, :path_2)

            UNION ALL

            SELECT c.id AS company_id
              FROM companies c
             WHERE c.logo_primary IN (:path_0, :path_1, :path_2)
                OR c.logo_secondary IN (:path_0, :path_1, :path_2)
                OR c.logo_icon IN (:path_0, :path_1, :path_2)

            UNION ALL

            SELECT fad.company_id
              FROM financial_automation_documents fad
             WHERE fad.deleted_at IS NULL
               AND (
                    fad.stored_relative_path IN (:path_0, :path_1, :path_2)
                 OR fad.original_relative_path IN (:path_0, :path_1, :path_2)
                 OR fad.optimized_relative_path IN (:path_0, :path_1, :path_2)
                 OR fad.preview_relative_path IN (:path_0, :path_1, :path_2)
               )
        ) upload_owners
        WHERE company_id IS NOT NULL
        """
    )

    try:
        rows = db.session.execute(
            query,
            {
                "path_0": candidates[0],
                "path_1": candidates[1],
                "path_2": candidates[2],
            },
        ).scalars()
        return {_as_int(row) for row in rows if _as_int(row)}
    except SQLAlchemyError as exc:
        logger.warning("Erro ao verificar escopo tenant de upload '%s': %s", normalized_path, exc)
        db.session.rollback()
        return set()


def _company_is_allowed(company_id):
    company_id = _as_int(company_id)
    if not company_id:
        return False
    if is_platform_admin():
        return True

    active_company_id = _current_company_context_id()
    if active_company_id and company_id != active_company_id:
        return False

    return can_access_company(company_id)


def user_can_access_upload(relative_path):
    """
    Autoriza arquivos servidos pela rota /uploads com isolamento por empresa.

    Corrige a renderização de prints do POP colados via Ctrl+V sem transformar a
    pasta de uploads em recurso público. Um arquivo só é entregue se estiver
    referenciado por Processo/POP/Logo de uma empresa acessível ao usuário.
    """
    if not current_user or not getattr(current_user, "is_authenticated", False):
        return False

    normalized_path = normalize_relative_upload_path(relative_path)
    if not normalized_path:
        return False

    owner_company_ids = _query_upload_owner_company_ids(normalized_path)
    return any(_company_is_allowed(company_id) for company_id in owner_company_ids)
