"""
API Endpoints para Colaboradores de Atividades de Projeto
Baseado no padrão de process_instance_collaborators
"""
from flask import jsonify, request
from flask_login import login_required
from database.postgres_helper import connect as pg_connect
import logging

logger = logging.getLogger(__name__)


@login_required
def api_project_activity_collaborators(company_id: int, project_id: int, activity_id: int):
    """
    GET: Lista colaboradores de uma atividade
    POST: Adiciona/atualiza colaborador e suas horas
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Verificar se atividade existe e pertence ao projeto
        cursor.execute("""
            SELECT pa.* 
            FROM project_activities pa
            JOIN company_projects cp ON pa.project_id = cp.id
            WHERE pa.id = %s AND pa.project_id = %s AND cp.company_id = %s
              AND pa.is_deleted = FALSE
        """, (activity_id, project_id, company_id))
        
        activity = cursor.fetchone()
        if not activity:
            return jsonify({"success": False, "error": "Activity not found"}), 404
        
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
            """, (activity_id,))
            
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
            """, (activity_id, employee_id, role))
            
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
                """, (activity_id, employee_id, role, hours, notes))
            
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
        cursor.execute("""
            SELECT 
                pa.id,
                pa.title,
                pa.estimated_hours,
                pa.worked_hours,
                COALESCE(pa.worked_hours, 0) as total_worked,
                CASE 
                    WHEN pa.estimated_hours > 0 THEN 
                        ROUND((COALESCE(pa.worked_hours, 0) / pa.estimated_hours) * 100, 2)
                    ELSE 0
                END as progress_percent
            FROM project_activities pa
            WHERE pa.id = %s AND pa.project_id = %s AND pa.is_deleted = FALSE
        """, (activity_id, project_id))
        
        activity = cursor.fetchone()
        if not activity:
            return jsonify({"success": False, "error": "Activity not found"}), 404
        
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
        """, (activity_id,))
        
        collaborators = [dict(row) for row in cursor.fetchall()]
        
        summary = dict(activity)
        summary['collaborators'] = collaborators
        summary['collaborator_count'] = len(collaborators)
        
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
