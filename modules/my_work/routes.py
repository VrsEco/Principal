import logging
from datetime import datetime
from typing import List, Optional

"""
Rotas do Módulo My Work
APIs e páginas para gestão de atividades
"""

from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from . import my_work_bp
from services.my_work_service import (
    add_comment,
    add_work_hours,
    count_activities_by_scope,
    get_company_overview,
    get_employee_from_user,
    get_filter_options,
    get_occurrences_summary,
    get_team_overview,
    get_user_activities,
    get_user_employees,
    get_user_stats,
    complete_activity,
    DELIVERY_TAGS,
)
from middleware.auto_log_decorator import auto_log_crud

logger = logging.getLogger(__name__)

SELECTION_MODE_NONE = "none"


# ============================================================================
# PÃGINAS
# ============================================================================


@my_work_bp.route("/")
@login_required
def dashboard():
    """
    PÃ¡gina principal - My Work Dashboard
    """
    return render_template("my_work.html", active_nav="my_work")


# ============================================================================
# APIs - LISTAGEM
# ============================================================================


@my_work_bp.route("/api/companies/debug", methods=["GET"])
@login_required
def debug_user_companies():
    """Endpoint de debug para diagnosticar problema de empresas"""
    from models.user import User
    from models.employee import Employee
    from models.company import Company
    from models import db
    from database.postgres_helper import connect as pg_connect
    from sqlalchemy import func
    
    debug_info = {
        "user_id": current_user.id,
        "user_email": current_user.email,
        "employees_by_user_id": [],
        "employees_by_email_sqlalchemy": [],
        "employees_by_email_sql": [],
        "companies_found": []
    }
    
    # Buscar por user_id
    employees_by_user_id = Employee.query.filter_by(user_id=current_user.id).all()
    debug_info["employees_by_user_id"] = [
        {"id": e.id, "name": e.name, "email": e.email, "company_id": e.company_id, "user_id": e.user_id}
        for e in employees_by_user_id
    ]
    
    # Buscar por email com SQLAlchemy
    if current_user.email:
        employees_by_email = Employee.query.filter(
            func.lower(Employee.email) == current_user.email.lower()
        ).all()
        debug_info["employees_by_email_sqlalchemy"] = [
            {"id": e.id, "name": e.name, "email": e.email, "company_id": e.company_id, "user_id": e.user_id}
            for e in employees_by_email
        ]
        
        # Buscar por email com SQL direto
        conn = pg_connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, company_id, user_id 
            FROM employees 
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
        """, (current_user.email,))
        rows = cursor.fetchall()
        debug_info["employees_by_email_sql"] = [
            {"id": row[0], "name": row[1], "email": row[2], "company_id": row[3], "user_id": row[4]}
            for row in rows
        ]
        conn.close()
    
    # Buscar empresas
    all_employee_ids = set()
    for emp in employees_by_user_id:
        all_employee_ids.add(emp.id)
    for emp in employees_by_email if current_user.email else []:
        all_employee_ids.add(emp.id)
    
    for emp_id in all_employee_ids:
        emp = Employee.query.get(emp_id)
        if emp and emp.company_id:
            company = Company.query.get(emp.company_id)
            if company:
                debug_info["companies_found"].append({
                    "employee_id": emp.id,
                    "company_id": company.id,
                    "company_name": company.name
                })
    
    return jsonify(debug_info)


@my_work_bp.route("/api/companies", methods=["GET"])
@login_required
def get_user_companies():
    """
    API: Lista empresas vinculadas ao usuário
    """
    try:
        logger.info(f"🔍 API /api/companies chamada para user_id: {current_user.id}, email: {current_user.email}")
        companies = get_user_employees(current_user.id)
        
        logger.info(f"📊 Retornando {len(companies)} empresas para o frontend")
        for comp in companies:
            logger.info(f"   - {comp.get('company_name')} (ID: {comp.get('company_id')})")
        
        # Sempre retornar sucesso, mesmo se lista vazia
        # O frontend vai tratar lista vazia adequadamente
        response_data = {"success": True, "data": companies or []}
        logger.info(f"✅ Resposta da API: success={response_data['success']}, data_count={len(response_data['data'])}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ Erro ao buscar empresas do usuário {current_user.id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Retornar lista vazia em caso de erro, não erro 500
        # Isso permite que o seletor apareça mesmo com erro
        return jsonify({
            "success": True, 
            "data": [],
            "error": str(e)  # Incluir erro para debug, mas não falhar
        })


@my_work_bp.route("/api/filter-options", methods=["GET"])
@login_required
def api_filter_options():
    """Return directories used by the filter dashboard."""
    try:
        data = get_filter_options(current_user.id)
        return jsonify({"success": True, "data": data})
    except Exception as exc:
        logger.error("Erro ao gerar opções de filtro: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@my_work_bp.route("/api/activities")
@login_required
def get_activities():
    """
    API: Lista de atividades conforme escopo

    Query Params:
        - scope: 'me', 'team' ou 'company'
        - filter: 'all', 'today', 'week', 'overdue'
        - search: texto de busca
        - sort: 'deadline', 'priority', 'status'
        - company_id: ID da empresa para filtrar (opcional)
    """
    try:
        # Mapear user para employee
        employee_id = get_employee_from_user(current_user.id)

        if employee_id is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Usuário não vinculado a um colaborador. Solicite ao administrador para concluir o cadastro.",
                    }
                ),
                404,
            )

        # Coleção de todos os employee_ids vinculados ao usuário
        def _collect_employee_ids() -> List[int]:
            employee_ids_set = set()
            if employee_id:
                employee_ids_set.add(employee_id)

            try:
                companies = get_user_employees(current_user.id) or []
            except Exception as exc:  # pragma: no cover - defensivo
                logger.warning(
                    "Falha ao buscar colaboradores vinculados ao usuário %s: %s",
                    current_user.id,
                    exc,
                )
                companies = []

            for company in companies:
                extra_id = company.get("employee_id")
                if extra_id:
                    employee_ids_set.add(extra_id)

            return list(employee_ids_set)

        employee_ids = _collect_employee_ids()

        # Parâmetros
        scope = request.args.get("scope", "me")
        company_id = request.args.get("company_id", type=int)  # Legado

        def _parse_int_csv(raw_value: Optional[str]) -> List[int]:
            if not raw_value:
                return []
            values = []
            for chunk in raw_value.split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                try:
                    values.append(int(chunk))
                except ValueError:
                    continue
            return values

        company_ids = _parse_int_csv(request.args.get("company_ids"))

        # Se company_id (legado) vier e company_ids não, adiciona
        if company_id and not company_ids:
            company_ids = [company_id]

        filters = {
            "filter": request.args.get("filter", "all"),
            "search": request.args.get("search", ""),
            "sort": request.args.get("sort", "deadline"),
        }

        types_raw = request.args.get("types")
        if types_raw:
            filters["types"] = [
                t.strip()
                for t in types_raw.split(",")
                if t.strip() in ("project", "process")
            ]

        roles_raw = request.args.get("roles")
        if roles_raw:
            filters["roles"] = [
                r.strip()
                for r in roles_raw.split(",")
                if r.strip() in ("responsible", "executor")
            ]

        responsible_ids = _parse_int_csv(request.args.get("responsible_ids"))
        if responsible_ids:
            filters["responsible_ids"] = responsible_ids

        executor_ids = _parse_int_csv(request.args.get("executor_ids"))
        if executor_ids:
            filters["executor_ids"] = executor_ids

        project_selection = (request.args.get("project_selection") or "").lower()
        project_ids = _parse_int_csv(request.args.get("project_ids"))
        if project_ids:
            filters["project_ids"] = project_ids
        elif project_selection == SELECTION_MODE_NONE:
            filters["project_selection"] = SELECTION_MODE_NONE

        process_selection = (request.args.get("process_selection") or "").lower()
        process_ids = _parse_int_csv(request.args.get("process_ids"))
        if process_ids:
            filters["process_ids"] = process_ids
        elif process_selection == SELECTION_MODE_NONE:
            filters["process_selection"] = SELECTION_MODE_NONE

        delivery_raw = request.args.get("delivery_tags")
        if delivery_raw is not None:
            filters["delivery_tags"] = [
                tag.strip()
                for tag in delivery_raw.split(",")
                if tag.strip() in DELIVERY_TAGS
            ]

        def _parse_date(value: str):
            if not value:
                return None
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None

        due_date_start = _parse_date(request.args.get("due_date_start"))
        due_date_end = _parse_date(request.args.get("due_date_end"))
        if due_date_start:
            filters["due_date_start"] = due_date_start
        if due_date_end:
            filters["due_date_end"] = due_date_end

        # Buscar atividades
        activities = get_user_activities(
            employee_id,
            scope,
            filters,
            company_ids=company_ids,
            employee_ids=employee_ids,
        )

        # Buscar estatísticas
        stats = get_user_stats(
            employee_id,
            scope,
            company_id,
            company_ids=company_ids,
            filters=filters,
            employee_ids=employee_ids,
        )

        # Contadores das abas
        counts = count_activities_by_scope(
            employee_id,
            company_id,
            company_ids=company_ids,
            filters=filters,
            employee_ids=employee_ids,
        )

        return jsonify(
            {"success": True, "data": activities, "stats": stats, "counts": counts}
        )

    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        logger.error(f"Erro ao buscar atividades: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@my_work_bp.route("/api/team-overview")
@login_required
def api_team_overview():
    """
    API: Dados do Team Overview
    
    Query Params:
        - company_id: ID da empresa para filtrar (opcional)
    """
    try:
        employee_id = get_employee_from_user(current_user.id)
        company_id = request.args.get("company_id", type=int)

        data = get_team_overview(employee_id, company_id)

        return jsonify({"success": True, "data": data})

    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@my_work_bp.route("/api/company-overview")
@login_required
def api_company_overview():
    """
    API: Dados executivos para Company Overview
    
    Query Params:
        - company_id: ID da empresa para filtrar (opcional)
    """
    try:
        employee_id = get_employee_from_user(current_user.id)
        company_id = request.args.get("company_id", type=int)

        data = get_company_overview(employee_id, company_id)

        return jsonify({"success": True, "data": data})

    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@my_work_bp.route("/api/occurrences/summary")
@login_required
def api_occurrences_summary():
    """Resumo de ocorrências para o card do My Work."""

    try:
        employee_id = get_employee_from_user(current_user.id)
        if employee_id is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Usuário não vinculado a um colaborador. Solicite ao administrador.",
                    }
                ),
                404,
            )

        def _parse_ints(raw_value: Optional[str]) -> List[int]:
            if not raw_value:
                return []
            values = []
            for chunk in raw_value.split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                try:
                    values.append(int(chunk))
                except ValueError:
                    continue
            return values

        company_ids = _parse_ints(request.args.get("company_ids"))

        def _collect_employee_ids(primary_id: Optional[int]) -> List[int]:
            collected: List[int] = []
            if primary_id:
                collected.append(primary_id)

            try:
                companies = get_user_employees(current_user.id) or []
            except Exception as exc:  # pragma: no cover - defensivo
                logger.warning(
                    "Falha ao buscar colaboradores do usuário %s: %s",
                    current_user.id,
                    exc,
                )
                companies = []

            for company in companies:
                extra_id = company.get("employee_id")
                if extra_id and extra_id not in collected:
                    collected.append(extra_id)
            return collected

        employee_ids = _collect_employee_ids(employee_id)

        summary = get_occurrences_summary(
            employee_id,
            company_ids=company_ids,
            employee_ids=employee_ids,
        )
        return jsonify({"success": True, "data": summary})
    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except Exception as e:
        logger.error("Erro ao obter resumo de ocorrências: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# APIs - AÇÕES
# ============================================================================


@login_required
@my_work_bp.route("/api/work-hours", methods=["POST"])
@login_required
@auto_log_crud("activity_work_log")
def api_add_work_hours():
    """
    API: Adicionar horas trabalhadas

    Payload:
        {
            "activity_type": "project" | "process",
            "activity_id": 123,
            "work_date": "2025-10-21",
            "hours": 2.5,
            "description": "..."
        }
    """
    try:
        employee_id = get_employee_from_user(current_user.id)

        data = request.get_json()

        # ValidaÃ§Ãµes
        if not data:
            return jsonify({"success": False, "error": "Dados nÃ£o fornecidos"}), 400

        if "activity_type" not in data or "activity_id" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "activity_type e activity_id obrigatÃ³rios",
                    }
                ),
                400,
            )

        if "hours" not in data or data["hours"] <= 0:
            return (
                jsonify({"success": False, "error": "Horas devem ser maior que zero"}),
                400,
            )

        # Adicionar horas
        result = add_work_hours(
            employee_id,
            data["activity_type"],
            data["activity_id"],
            {
                "work_date": data.get("work_date", datetime.now().date().isoformat()),
                "hours": data["hours"],
                "description": data.get("description"),
            },
        )

        return jsonify({"success": True, "data": result, "message": result["message"]})

    except Exception as e:
        logger.info(f"Erro ao adicionar horas: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@my_work_bp.route("/api/comments", methods=["POST"])
@login_required
@auto_log_crud("activity_comment")
def api_add_comment():
    """
    API: Adicionar comentÃ¡rio em atividade

    Payload:
        {
            "activity_type": "project" | "process",
            "activity_id": 123,
            "comment_type": "note",
            "comment": "...",
            "is_private": false
        }
    """
    try:
        employee_id = get_employee_from_user(current_user.id)

        data = request.get_json()

        # ValidaÃ§Ãµes
        if not data:
            return jsonify({"success": False, "error": "Dados nÃ£o fornecidos"}), 400

        if "activity_type" not in data or "activity_id" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "activity_type e activity_id obrigatÃ³rios",
                    }
                ),
                400,
            )

        if "comment" not in data or not data["comment"].strip():
            return (
                jsonify({"success": False, "error": "ComentÃ¡rio nÃ£o pode ser vazio"}),
                400,
            )

        # Adicionar comentÃ¡rio
        result = add_comment(
            employee_id,
            data["activity_type"],
            data["activity_id"],
            {
                "comment_type": data.get("comment_type", "note"),
                "comment": data["comment"],
                "is_private": data.get("is_private", False),
            },
        )

        return jsonify({"success": True, "data": result, "message": result["message"]})

    except Exception as e:
        logger.info(f"Erro ao adicionar comentÃ¡rio: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@my_work_bp.route("/api/complete", methods=["POST"])
@login_required
@auto_log_crud("activity")
def api_complete_activity():
    """
    API: Finalizar atividade

    Payload:
        {
            "activity_type": "project" | "process",
            "activity_id": 123,
            "completion_comment": "..." (opcional)
        }
    """
    try:
        employee_id = get_employee_from_user(current_user.id)

        data = request.get_json()

        # ValidaÃ§Ãµes
        if not data:
            return jsonify({"success": False, "error": "Dados nÃ£o fornecidos"}), 400

        if "activity_type" not in data or "activity_id" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "activity_type e activity_id obrigatÃ³rios",
                    }
                ),
                400,
            )

        # Finalizar
        result = complete_activity(
            employee_id,
            data["activity_type"],
            data["activity_id"],
            {"completion_comment": data.get("completion_comment")},
        )

        return jsonify({"success": True, "data": result, "message": result["message"]})

    except Exception as e:
        logger.info(f"Erro ao finalizar atividade: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# APIs - DETALHAMENTO
# ============================================================================


@my_work_bp.route("/activity/<int:activity_id>")
@login_required
def view_project_activity(activity_id):
    """
    PÃ¡gina de detalhes da atividade de projeto
    """
    # TODO: Implementar pÃ¡gina de detalhamento
    return f"<h1>Detalhes da Atividade de Projeto #{activity_id}</h1><p>Em desenvolvimento...</p>"


@my_work_bp.route("/process-instance/<int:instance_id>")
@login_required
def view_process_instance(instance_id):
    """
    PÃ¡gina de detalhes da instÃ¢ncia de processo
    """
    # TODO: Implementar pÃ¡gina de detalhamento
    return f"<h1>Detalhes da InstÃ¢ncia de Processo #{instance_id}</h1><p>Em desenvolvimento...</p>"
