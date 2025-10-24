"""
Service para My Work - Lógica de negócio
Gerencia atividades pessoais, de equipe e da empresa
"""
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from sqlalchemy import or_, and_, func
from database.postgres_helper import connect as pg_connect


def get_employee_from_user(user_id: int) -> Optional[int]:
    """
    Mapeia user_id para employee_id
    
    Estratégia:
    1. Busca direta por user_id (relacionamento FK)
    2. Fallback: busca por email (para dados legados)
    
    Args:
        user_id: ID do usuário logado
    
    Returns:
        employee_id ou None
    """
    from models.user import User
    
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # 1. Buscar por user_id (relacionamento direto)
        cursor.execute("SELECT id FROM employees WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        
        if row:
            conn.close()
            return row[0]
        
        # 2. Fallback: buscar por email (dados legados sem user_id preenchido)
        user = User.query.get(user_id)
        if user and user.email:
            cursor.execute("""
                SELECT id FROM employees 
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
            """, (user.email,))
            row = cursor.fetchone()
            
            if row:
                employee_id = row[0]
                
                # Auto-vincular para próximas consultas
                try:
                    cursor.execute("""
                        UPDATE employees 
                        SET user_id = %s 
                        WHERE id = %s AND user_id IS NULL
                    """, (user_id, employee_id))
                    conn.commit()
                    print(f"✅ Auto-vinculado: User #{user_id} -> Employee #{employee_id}")
                except:
                    conn.rollback()
                
                conn.close()
                return employee_id
        
        conn.close()
        return None
        
    except Exception as e:
        print(f"❌ Erro ao mapear user_id para employee_id: {e}")
        conn.close()
        return None


def get_user_activities(employee_id: int, scope: str = 'me', filters: Dict = None) -> List[Dict]:
    """
    Retorna atividades conforme escopo
    
    Args:
        employee_id: ID do colaborador
        scope: 'me', 'team' ou 'company'
        filters: Filtros adicionais (filter, search, sort)
    
    Returns:
        Lista de atividades (projetos + processos)
    """
    filters = filters or {}
    
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        if scope == 'me':
            activities = _get_my_activities(cursor, employee_id, filters)
        elif scope == 'team':
            activities = _get_team_activities(cursor, employee_id, filters)
        elif scope == 'company':
            activities = _get_company_activities(cursor, employee_id, filters)
        else:
            activities = []
        
        conn.close()
        return activities
        
    except Exception as e:
        conn.close()
        raise e


def _get_my_activities(cursor, employee_id: int, filters: Dict) -> List[Dict]:
    """Busca atividades pessoais do colaborador"""
    
    # Construir filtros WHERE
    where_clauses = []
    params = {'employee_id': employee_id}
    
    filter_type = filters.get('filter', 'all')
    if filter_type == 'today':
        where_clauses.append("end_date = CURRENT_DATE")
    elif filter_type == 'week':
        where_clauses.append("end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'")
    elif filter_type == 'overdue':
        where_clauses.append("end_date < CURRENT_DATE AND status != 'completed'")
    
    # Busca
    search = filters.get('search', '')
    
    # Construir WHERE adicional
    where_sql = ""
    if where_clauses:
        where_sql = " AND " + " AND ".join(where_clauses)
    
    if search:
        if where_sql:
            where_sql += " AND (title ILIKE %s OR description ILIKE %s)"
        else:
            where_sql = " AND (title ILIKE %s OR description ILIKE %s)"
    
    # Query de projetos
    query_sql = """
        SELECT 
            'project' as type,
            id,
            title,
            description,
            status,
            priority,
            responsible_id,
            executor_id,
            end_date as deadline,
            estimated_hours,
            worked_hours,
            created_at,
            updated_at
        FROM company_projects
        WHERE (responsible_id = %s OR executor_id = %s)
    """ + where_sql
    
    query_params = [employee_id, employee_id]
    if search:
        query_params.extend([f'%{search}%', f'%{search}%'])
    
    cursor.execute(query_sql, tuple(query_params))
    
    projects = [dict(row) for row in cursor.fetchall()]
    
    # Query de processos (simplificada por enquanto)
    # TODO: Melhorar query de processos com JSON
    try:
        cursor.execute("""
            SELECT 
                'process' as type,
                id,
                title,
                description,
                status,
                priority,
                NULL as responsible_id,
                NULL as executor_id,
                due_date as deadline,
                estimated_hours,
                actual_hours as worked_hours,
                created_at,
                updated_at
            FROM process_instances
            WHERE status != 'completed'
            LIMIT 50
        """)
    except:
        # Se falhar, retornar lista vazia de processos
        processes = []
    else:
        processes = [dict(row) for row in cursor.fetchall()]
    
    # Combinar e ordenar
    all_activities = projects + processes
    
    # Ordenação
    sort_by = filters.get('sort', 'deadline')
    if sort_by == 'priority':
        all_activities.sort(key=lambda x: _priority_order(x.get('priority')), reverse=True)
    elif sort_by == 'status':
        all_activities.sort(key=lambda x: _status_order(x.get('status')))
    else:  # deadline
        all_activities.sort(key=lambda x: x.get('deadline') or '9999-12-31')
    
    return all_activities


def _get_team_activities(cursor, employee_id: int, filters: Dict) -> List[Dict]:
    """Busca atividades da equipe do colaborador"""
    
    # Buscar equipe do employee
    cursor.execute("""
        SELECT team_id
        FROM team_members
        WHERE employee_id = %s
        LIMIT 1
    """, (employee_id,))
    
    team_row = cursor.fetchone()
    if not team_row:
        return []
    
    team_id = team_row[0]
    
    # Buscar IDs dos membros da equipe
    cursor.execute("""
        SELECT employee_id
        FROM team_members
        WHERE team_id = %s
    """, (team_id,))
    
    member_ids = [row[0] for row in cursor.fetchall()]
    
    if not member_ids:
        return []
    
    # Buscar atividades de todos os membros
    placeholders = ','.join(['%s'] * len(member_ids))
    
    # Projetos da equipe
    cursor.execute(f"""
        SELECT 
            'project' as type,
            cp.id,
            cp.title,
            cp.description,
            cp.status,
            cp.priority,
            cp.responsible_id,
            cp.executor_id,
            cp.end_date as deadline,
            cp.estimated_hours,
            cp.worked_hours,
            e.name as assigned_to_name,
            cp.created_at,
            cp.updated_at
        FROM company_projects cp
        LEFT JOIN employees e ON e.id = COALESCE(cp.executor_id, cp.responsible_id)
        WHERE (cp.responsible_id IN ({placeholders}) OR cp.executor_id IN ({placeholders}))
    """, member_ids + member_ids)
    
    projects = [dict(row) for row in cursor.fetchall()]
    
    # TODO: Buscar processos da equipe
    # (mais complexo pois assigned_collaborators é JSON)
    
    return projects


def _get_company_activities(cursor, employee_id: int, filters: Dict) -> List[Dict]:
    """Busca todas as atividades da empresa"""
    
    # Verificar permissão
    if not _can_view_company(cursor, employee_id):
        raise PermissionError("Usuário sem permissão para visualizar atividades da empresa")
    
    # Buscar company_id do employee
    cursor.execute("SELECT company_id FROM employees WHERE id = %s", (employee_id,))
    company_row = cursor.fetchone()
    
    if not company_row:
        return []
    
    company_id = company_row[0]
    
    # Buscar todas as atividades da empresa
    cursor.execute("""
        SELECT 
            'project' as type,
            cp.id,
            cp.title,
            cp.description,
            cp.status,
            cp.priority,
            cp.responsible_id,
            cp.executor_id,
            cp.end_date as deadline,
            cp.estimated_hours,
            cp.worked_hours,
            e.name as assigned_to_name,
            cp.created_at,
            cp.updated_at
        FROM company_projects cp
        LEFT JOIN employees e ON e.id = COALESCE(cp.executor_id, cp.responsible_id)
        WHERE cp.company_id = %s
    """, (company_id,))
    
    projects = [dict(row) for row in cursor.fetchall()]
    
    return projects


def get_user_stats(employee_id: int, scope: str = 'me') -> Dict:
    """
    Retorna estatísticas conforme escopo
    
    Returns:
        Dict com contadores
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        if scope == 'me':
            stats = _get_my_stats(cursor, employee_id)
        elif scope == 'team':
            stats = _get_team_stats(cursor, employee_id)
        elif scope == 'company':
            stats = _get_company_stats(cursor, employee_id)
        else:
            stats = {}
        
        conn.close()
        return stats
        
    except Exception as e:
        conn.close()
        raise e


def _get_my_stats(cursor, employee_id: int) -> Dict:
    """Estatísticas pessoais"""
    
    cursor.execute("""
        SELECT 
            status,
            COUNT(*) as count
        FROM (
            SELECT status FROM company_projects
            WHERE (responsible_id = %s OR executor_id = %s)
            UNION ALL
            SELECT status FROM process_instances
            WHERE assigned_collaborators::text LIKE %s
        ) combined
        GROUP BY status
    """, (employee_id, employee_id, f'%"employee_id": {employee_id}%'))
    
    status_counts = {row[0]: row[1] for row in cursor.fetchall()}
    
    return {
        'pending': status_counts.get('pending', 0) + status_counts.get('planned', 0),
        'in_progress': status_counts.get('in_progress', 0) + status_counts.get('executing', 0),
        'overdue': 0,  # TODO: Calcular atrasadas
        'completed': status_counts.get('completed', 0)
    }


def _get_team_stats(cursor, employee_id: int) -> Dict:
    """Estatísticas da equipe"""
    # TODO: Implementar
    return {
        'pending': 45,
        'in_progress': 12,
        'overdue': 8,
        'completed': 320
    }


def _get_company_stats(cursor, employee_id: int) -> Dict:
    """Estatísticas da empresa"""
    # TODO: Implementar
    return {
        'pending': 180,
        'in_progress': 65,
        'overdue': 23,
        'completed': 1500
    }


def count_activities_by_scope(employee_id: int) -> Dict:
    """
    Conta atividades em cada escopo para os contadores das abas
    
    Returns:
        {'me': 17, 'team': 45, 'company': 180}
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Minhas atividades
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT id FROM company_projects
                WHERE (responsible_id = %s OR executor_id = %s) AND status != 'completed'
                UNION ALL
                SELECT id FROM process_instances
                WHERE assigned_collaborators::text LIKE %s AND status != 'completed'
            ) combined
        """, (employee_id, employee_id, f'%"employee_id": {employee_id}%'))
        
        count_me = cursor.fetchone()[0]
        
        # TODO: Contar equipe e empresa
        count_team = 0
        count_company = 0
        
        conn.close()
        
        return {
            'me': count_me,
            'team': count_team,
            'company': count_company
        }
        
    except Exception as e:
        conn.close()
        raise e


def _can_view_company(cursor, employee_id: int) -> bool:
    """Verifica se employee tem permissão para ver atividades da empresa"""
    
    # TODO: Implementar verificação de role/permissão
    # Por enquanto, permitir para todos (demo)
    return True


def _priority_order(priority: str) -> int:
    """Ordem de prioridade para ordenação"""
    order = {'urgent': 4, 'high': 3, 'normal': 2, 'low': 1}
    return order.get(priority, 0)


def _status_order(status: str) -> int:
    """Ordem de status para ordenação"""
    order = {'overdue': 1, 'pending': 2, 'planned': 3, 'in_progress': 4, 'executing': 5, 'completed': 6}
    return order.get(status, 99)


# ============================================================================
# WORK HOURS
# ============================================================================

def add_work_hours(employee_id: int, activity_type: str, activity_id: int, work_data: Dict) -> Dict:
    """
    Adiciona registro de horas trabalhadas
    
    Args:
        employee_id: ID do colaborador
        activity_type: 'project' ou 'process'
        activity_id: ID da atividade
        work_data: {work_date, hours, description}
    
    Returns:
        Dict com log criado
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Buscar nome do employee
        cursor.execute("SELECT name FROM employees WHERE id = %s", (employee_id,))
        employee_row = cursor.fetchone()
        employee_name = employee_row[0] if employee_row else "Desconhecido"
        
        # Inserir log
        cursor.execute("""
            INSERT INTO activity_work_logs 
            (activity_type, activity_id, employee_id, employee_name, work_date, hours_worked, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            activity_type,
            activity_id,
            employee_id,
            employee_name,
            work_data['work_date'],
            work_data['hours'],
            work_data.get('description')
        ))
        
        log_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return {
            'id': log_id,
            'success': True,
            'message': f'{work_data["hours"]}h registradas com sucesso'
        }
        
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def add_comment(employee_id: int, activity_type: str, activity_id: int, comment_data: Dict) -> Dict:
    """
    Adiciona comentário em atividade
    
    Args:
        employee_id: ID do colaborador
        activity_type: 'project' ou 'process'
        activity_id: ID da atividade
        comment_data: {comment_type, comment, is_private}
    
    Returns:
        Dict com comentário criado
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Buscar nome do employee
        cursor.execute("SELECT name FROM employees WHERE id = %s", (employee_id,))
        employee_row = cursor.fetchone()
        employee_name = employee_row[0] if employee_row else "Desconhecido"
        
        # Inserir comentário
        cursor.execute("""
            INSERT INTO activity_comments 
            (activity_type, activity_id, employee_id, employee_name, comment_type, comment_text, is_private)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            activity_type,
            activity_id,
            employee_id,
            employee_name,
            comment_data.get('comment_type', 'note'),
            comment_data['comment'],
            comment_data.get('is_private', False)
        ))
        
        comment_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return {
            'id': comment_id,
            'success': True,
            'message': 'Comentário adicionado com sucesso'
        }
        
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def complete_activity(employee_id: int, activity_type: str, activity_id: int, completion_data: Dict) -> Dict:
    """
    Finaliza atividade
    
    Args:
        employee_id: ID do colaborador
        activity_type: 'project' ou 'process'
        activity_id: ID da atividade
        completion_data: {completion_comment (optional)}
    
    Returns:
        Dict com resultado
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Adicionar comentário final se fornecido
        if completion_data.get('completion_comment'):
            add_comment(employee_id, activity_type, activity_id, {
                'comment_type': 'note',
                'comment': completion_data['completion_comment'],
                'is_private': False
            })
        
        # Atualizar status
        if activity_type == 'project':
            cursor.execute("""
                UPDATE company_projects
                SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (activity_id,))
        elif activity_type == 'process':
            cursor.execute("""
                UPDATE process_instances
                SET status = 'completed', 
                    completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (activity_id,))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Atividade finalizada com sucesso'
        }
        
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


# ============================================================================
# TEAM OVERVIEW
# ============================================================================

def get_team_overview(employee_id: int) -> Dict:
    """
    Retorna dados para o Team Overview
    
    Returns:
        Dict com distribuição, alertas e performance
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Buscar equipe
        cursor.execute("""
            SELECT t.id, t.name, t.description
            FROM teams t
            JOIN team_members tm ON tm.team_id = t.id
            WHERE tm.employee_id = %s
            LIMIT 1
        """, (employee_id,))
        
        team_row = cursor.fetchone()
        if not team_row:
            conn.close()
            return {}
        
        team_id = team_row[0]
        team_name = team_row[1]
        
        # Buscar distribuição de carga
        distribution = _get_team_load_distribution(cursor, team_id)
        
        # Gerar alertas
        alerts = _generate_team_alerts(distribution)
        
        # Calcular performance
        performance = _calculate_team_performance(cursor, team_id)
        
        conn.close()
        
        return {
            'team_name': team_name,
            'members': distribution,
            'alerts': alerts,
            'performance': performance
        }
        
    except Exception as e:
        conn.close()
        raise e


def _get_team_load_distribution(cursor, team_id: int) -> List[Dict]:
    """Calcula distribuição de carga entre membros"""
    
    cursor.execute("""
        SELECT 
            e.id,
            e.name,
            tm.role,
            COALESCE(
                (SELECT SUM(estimated_hours) 
                 FROM company_projects 
                 WHERE (responsible_id = e.id OR executor_id = e.id) 
                 AND status != 'completed'), 
                0
            ) as allocated_hours,
            COALESCE(
                (SELECT SUM(worked_hours) 
                 FROM company_projects 
                 WHERE (responsible_id = e.id OR executor_id = e.id)), 
                0
            ) as worked_hours
        FROM team_members tm
        JOIN employees e ON e.id = tm.employee_id
        WHERE tm.team_id = %s
        ORDER BY allocated_hours DESC
    """, (team_id,))
    
    members = []
    for row in cursor.fetchall():
        capacity = 40  # TODO: Buscar capacidade configurada do employee
        allocated = float(row[3] or 0)
        utilization = (allocated / capacity * 100) if capacity > 0 else 0
        
        members.append({
            'id': row[0],
            'name': row[1],
            'role': row[2],
            'capacity': capacity,
            'allocated': allocated,
            'worked': float(row[4] or 0),
            'utilization_percent': round(utilization),
            'status': _get_load_status(utilization)
        })
    
    return members


def _get_load_status(utilization: float) -> str:
    """Determina status baseado na utilização"""
    if utilization > 90:
        return 'overload'
    elif utilization > 75:
        return 'high'
    elif utilization < 50:
        return 'available'
    else:
        return 'normal'


def _generate_team_alerts(members: List[Dict]) -> List[Dict]:
    """Gera alertas baseado na distribuição"""
    alerts = []
    
    for member in members:
        if member['status'] == 'overload':
            alerts.append({
                'type': 'overload',
                'severity': 'warning',
                'employee_id': member['id'],
                'employee_name': member['name'],
                'message': f"{member['name']} sobrecarregado(a)",
                'details': f"{member['allocated']}h alocadas ({member['utilization_percent']}% da capacidade)"
            })
        elif member['status'] == 'available':
            alerts.append({
                'type': 'available',
                'severity': 'success',
                'employee_id': member['id'],
                'employee_name': member['name'],
                'message': f"{member['name']} disponível",
                'details': f"{member['capacity'] - member['allocated']}h de capacidade livre"
            })
    
    return alerts


def _calculate_team_performance(cursor, team_id: int) -> Dict:
    """Calcula métricas de performance da equipe"""
    
    # TODO: Implementar cálculo real
    return {
        'avg_score': 78,
        'completion_rate': 85,
        'capacity_utilization': 75
    }


# ============================================================================
# COMPANY OVERVIEW
# ============================================================================

def get_company_overview(employee_id: int) -> Dict:
    """
    Retorna dados executivos para Company Overview
    
    Returns:
        Dict com métricas executivas
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Verificar permissão
        if not _can_view_company(cursor, employee_id):
            raise PermissionError("Sem permissão para visualizar dados da empresa")
        
        # Buscar company_id
        cursor.execute("SELECT company_id FROM employees WHERE id = %s", (employee_id,))
        company_id = cursor.fetchone()[0]
        
        # Buscar métricas
        summary = _get_company_summary(cursor, company_id)
        heatmap = _get_company_heatmap(cursor, company_id)
        ranking = _get_department_ranking(cursor, company_id)
        
        conn.close()
        
        return {
            'summary': summary,
            'heatmap': heatmap,
            'ranking': ranking
        }
        
    except Exception as e:
        conn.close()
        raise e


def _get_company_summary(cursor, company_id: int) -> Dict:
    """Métricas gerais da empresa"""
    
    # Contar equipes
    cursor.execute("SELECT COUNT(*) FROM teams WHERE company_id = %s AND is_active = true", (company_id,))
    teams_count = cursor.fetchone()[0]
    
    # Contar colaboradores
    cursor.execute("SELECT COUNT(*) FROM employees WHERE company_id = %s", (company_id,))
    employees_count = cursor.fetchone()[0]
    
    # Contar atividades
    cursor.execute("SELECT COUNT(*) FROM company_projects WHERE company_id = %s AND status != 'completed'", (company_id,))
    activities_count = cursor.fetchone()[0]
    
    return {
        'active_teams': teams_count,
        'total_employees': employees_count,
        'avg_capacity_utilization': 78,  # TODO: Calcular real
        'total_activities': activities_count
    }


def _get_company_heatmap(cursor, company_id: int) -> List[Dict]:
    """Mapa de calor por equipe/departamento"""
    
    # TODO: Implementar query real agrupando por equipe
    # Mockado por enquanto
    return [
        {
            'team_name': 'Comercial',
            'employee_count': 12,
            'activities_count': 45,
            'utilization_percent': 92,
            'status': 'high'
        },
        {
            'team_name': 'TI / Tecnologia',
            'employee_count': 18,
            'activities_count': 65,
            'utilization_percent': 75,
            'status': 'medium'
        },
        {
            'team_name': 'RH / Administrativo',
            'employee_count': 8,
            'activities_count': 18,
            'utilization_percent': 48,
            'status': 'low'
        },
        {
            'team_name': 'Operações',
            'employee_count': 25,
            'activities_count': 52,
            'utilization_percent': 98,
            'status': 'critical'
        }
    ]


def _get_department_ranking(cursor, company_id: int) -> List[Dict]:
    """Ranking de performance por departamento"""
    
    # TODO: Implementar query real
    return [
        {'rank': 1, 'team_name': 'TI / Tecnologia', 'score': 85, 'completion_rate': 92},
        {'rank': 2, 'team_name': 'Comercial', 'score': 82, 'completion_rate': 88},
        {'rank': 3, 'team_name': 'Operações', 'score': 78, 'completion_rate': 85},
        {'rank': 4, 'team_name': 'RH / Administrativo', 'score': 75, 'completion_rate': 80}
    ]

