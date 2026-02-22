"""
API Endpoints para Colaboradores de Atividades de Projeto
Baseado no padrão de process_instance_collaborators
"""
from flask import jsonify, request
from flask_login import login_required
from database.postgres_helper import connect as pg_connect
import logging

logger = logging.getLogger(__name__)


def _fetch_project_activity(cursor, company_id: int, project_id: int, activity_id: int):
    """Return a normalized activity row by primary or legacy ID."""
    legacy_lookup = str(activity_id)
    cursor.execute(
        """
        SELECT pa.*
        FROM project_activities pa
        JOIN company_projects cp ON pa.project_id = cp.id
        WHERE pa.project_id = %s
          AND cp.company_id = %s
          AND pa.is_deleted = FALSE
          AND (
              pa.id = %s
              OR (pa.metadata ->> 'legacy_id') = %s
          )
        LIMIT 1
        """,
        (project_id, company_id, activity_id, legacy_lookup),
    )
    return cursor.fetchone()


@login_required
def api_project_activity_collaborators(company_id: int, project_id: int, activity_id: int):
    """
    GET: Lista colaboradores de uma atividade
    POST: Adiciona/atualiza colaborador e suas horas
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        activity = _fetch_project_activity(cursor, company_id, project_id, activity_id)
        if not activity:
            return jsonify({"success": False, "error": "Activity not found"}), 404
        db_activity_id = activity["id"]
        
        if request.method == "GET":
            # Listar colaboradores
            cursor.execute("""
                SELECT 
                    pac.*,
                    e.name as employee_name,
                    e.email as employee_email
                FROM project_activity_collaborators pac
                JOIN employees e ON pac.employee_id = e.id
                WHERE pac.activity_id = %s AND pac.is_deleted = FALSE
                ORDER BY pac.role, e.name
            """, (db_activity_id,))
            
            collaborators = [dict(row) for row in cursor.fetchall()]
            return jsonify({"success": True, "data": collaborators})
        
        elif request.method == "POST":
            # Adicionar/atualizar colaborador
            data = request.json or {}
            employee_id = data.get("employee_id")
            role = data.get("role", "executor")
            hours = float(data.get("hours", 0))
            notes = data.get("notes", "")
            
            if not employee_id:
                return jsonify({"success": False, "error": "employee_id required"}), 400
            
            # Verificar se colaborador já existe
            cursor.execute("""
                SELECT id, worked_hours 
                FROM project_activity_collaborators
                WHERE activity_id = %s AND employee_id = %s AND role = %s
                  AND is_deleted = FALSE
            """, (db_activity_id, employee_id, role))
            
            existing = cursor.fetchone()
            
            if existing:
                # Atualizar horas (incrementar)
                new_hours = float(existing['worked_hours'] or 0) + hours
                cursor.execute("""
                    UPDATE project_activity_collaborators
                    SET worked_hours = %s,
                        notes = COALESCE(%s, notes),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                """, (new_hours, notes if notes else None, existing['id']))
            else:
                # Inserir novo colaborador
                cursor.execute("""
                    INSERT INTO project_activity_collaborators
                    (activity_id, employee_id, role, worked_hours, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                """, (db_activity_id, employee_id, role, hours, notes))
            
            result = dict(cursor.fetchone())
            conn.commit()
            
            # Buscar nome do colaborador
            cursor.execute("SELECT name FROM employees WHERE id = %s", (employee_id,))
            emp = cursor.fetchone()
            if emp:
                result['employee_name'] = emp['name']
            
            return jsonify({"success": True, "data": result})
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in api_project_activity_collaborators: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@login_required
def api_project_activity_hours_summary(company_id: int, project_id: int, activity_id: int):
    """
    GET: Retorna resumo de horas da atividade
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Buscar atividade com horas agregadas
        activity = _fetch_project_activity(cursor, company_id, project_id, activity_id)
        if not activity:
            return jsonify({"success": False, "error": "Activity not found"}), 404
        db_activity_id = activity["id"]
        
        # Buscar detalhes por colaborador
        cursor.execute("""
            SELECT 
                pac.employee_id,
                e.name as employee_name,
                pac.role,
                pac.worked_hours,
                pac.notes
            FROM project_activity_collaborators pac
            JOIN employees e ON pac.employee_id = e.id
            WHERE pac.activity_id = %s AND pac.is_deleted = FALSE
            ORDER BY pac.worked_hours DESC
        """, (db_activity_id,))
        
        collaborators = [dict(row) for row in cursor.fetchall()]
        
        worked_hours_value = activity.get("worked_hours")
        estimated_hours_value = activity.get("estimated_hours")
        total_worked = float(worked_hours_value) if worked_hours_value is not None else 0
        estimated_hours = float(estimated_hours_value) if estimated_hours_value is not None else 0
        progress_percent = (
            round((total_worked / estimated_hours) * 100, 2) if estimated_hours else 0
        )

        summary = {
            "id": activity["id"],
            "title": activity.get("title"),
            "estimated_hours": estimated_hours_value,
            "worked_hours": worked_hours_value,
            "total_worked": total_worked,
            "progress_percent": progress_percent,
            "collaborators": collaborators,
            "collaborator_count": len(collaborators),
        }
        
        return jsonify({"success": True, "data": summary})
    
    except Exception as e:
        logger.error(f"Error in api_project_activity_hours_summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


# Funções auxiliares para registrar no blueprint
def register_project_hours_routes(bp):
    """Registra as rotas no blueprint GRV"""
    
    bp.add_url_rule(
        "/api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/collaborators",
        "api_project_activity_collaborators",
        api_project_activity_collaborators,
        methods=["GET", "POST"]
    )
    
    bp.add_url_rule(
        "/api/companies/<int:company_id>/projects/<int:project_id>/activities/<int:activity_id>/hours-summary",
        "api_project_activity_hours_summary",
        api_project_activity_hours_summary,
        methods=["GET"]
    )
