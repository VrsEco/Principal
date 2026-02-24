# Adicionar este código no app_pev.py após a função api_company_project
from flask import request, jsonify, current_app as app
import logging

logger = logging.getLogger(__name__)

def _open_portfolio_connection():
    # Helper to open connection if used standalone (dummy for lint)
    from database import get_db
    return get_db()._get_connection()

@app.route(
    "/api/companies/<int:company_id>/projects/<int:project_id>/archive",
    methods=["POST"],
)
def api_archive_project(company_id: int, project_id: int):
    """
    Arquiva ou desarquiva um projeto
    
    Body JSON:
        {
            "archived": true/false
        }
    """
    try:
        payload = request.get_json(silent=True) or {}
        is_archived = payload.get("archived", True)  # Default: arquivar
        
        conn = _open_portfolio_connection()
        cursor = conn.cursor()
        
        # Verificar se o projeto existe
        cursor.execute(
            "SELECT id, title FROM company_projects WHERE company_id = %s AND id = %s",
            (company_id, project_id),
        )
        project = cursor.fetchone()
        
        if not project:
            conn.close()
            return jsonify({"success": False, "message": "Projeto não encontrado."}), 404
        
        # Atualizar is_archived
        cursor.execute(
            "UPDATE company_projects SET is_archived = %s, updated_at = NOW() WHERE company_id = %s AND id = %s",
            (is_archived, company_id, project_id),
        )
        conn.commit()
        conn.close()
        
        action = "arquivado" if is_archived else "desarquivado"
        return jsonify({
            "success": True,
            "message": f"Projeto {action} com sucesso.",
            "project_id": project_id,
            "is_archived": is_archived
        })
        
    except Exception as exc:
        logger.error(f"Erro ao arquivar/desarquivar projeto: {exc}")
        return jsonify({"success": False, "message": "Erro ao arquivar projeto."}), 500

