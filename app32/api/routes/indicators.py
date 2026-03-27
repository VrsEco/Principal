from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify, abort
from utils.indicator_ranges import normalize_performance_ranges
from utils.permissions import permission_required
from models import db, Company, Indicator, IndicatorTree, IndicatorGoal, IndicatorData, Employee, Team, Routine
import json


def _indicator_exists_for_tree(company_id: int, tree_id: int) -> bool:
    return (
        db.session.query(Indicator.id)
        .filter(Indicator.company_id == company_id, Indicator.tree_id == tree_id)
        .first()
        is not None
    )

def _get_form_context(company_id):
    """Carrega e serializa todos os dados necessários para o formulário de indicadores."""
    from models import Project, Process, OKRGlobal, OKRArea, Routine

    # Todos os nós da empresa
    all_tree_nodes = IndicatorTree.query.filter_by(company_id=company_id).order_by(IndicatorTree.code).all()

    # Identificar IDs que são "pais" (têm subníveis) — não podem receber indicadores
    parent_ids = set(
        row[0] for row in
        db.session.query(IndicatorTree.parent_id)
        .filter(IndicatorTree.parent_id.isnot(None), IndicatorTree.company_id == company_id)
        .distinct().all()
    )

    # Apenas nós folha: sem filhos na árvore
    leaf_nodes = [n for n in all_tree_nodes if n.id not in parent_ids]

    employees = Employee.query.filter_by(company_id=company_id, status='active').order_by(Employee.name).all()
    teams = Team.query.filter_by(company_id=company_id, is_active=True).order_by(Team.name).all()

    try:
        projects = Project.query.filter_by(company_id=company_id).filter(
            Project.status.notin_(['completed', 'cancelled', 'archived'])
        ).order_by(Project.name).all()
        projects_json = json.dumps([{'id': p.id, 'name': p.name, 'code': getattr(p, 'code', '')} for p in projects])
    except Exception:
        projects_json = '[]'

    try:
        processes = Process.query.filter_by(company_id=company_id, is_active=True).order_by(Process.name).all()
        processes_json = json.dumps([{'id': p.id, 'name': p.name, 'code': getattr(p, 'code', '')} for p in processes])
    except Exception:
        processes_json = '[]'

    try:
        okrs_global = OKRGlobal.query.filter_by(company_id=company_id).all()
        okrs_area = OKRArea.query.filter_by(company_id=company_id).all()
        okrs_combined = [{'id': o.id, 'name': f'[Global] {o.objective}'} for o in okrs_global] + \
                        [{'id': o.id, 'name': f'[Área] {o.objective}'} for o in okrs_area]
        okrs_json = json.dumps(okrs_combined)
    except Exception:
        okrs_json = '[]'

    try:
        routines = Routine.query.filter_by(company_id=company_id, is_active=True).order_by(Routine.name).all()
        routines_json = json.dumps([{'id': r.id, 'name': r.name, 'code': getattr(r, 'code', '')} for r in routines])
    except Exception:
        routines_json = '[]'

    # Montar mapa de código pai para cada folha (para label contextual no select)
    id_to_node = {n.id: n for n in all_tree_nodes}

    return {
        'tree_nodes_json': json.dumps([
            {
                'id': n.id,
                'name': n.name,
                'code': n.code,
                'label': f"{n.code} — {n.name}"
            }
            for n in leaf_nodes
        ]),
        'employees_json': json.dumps([{'id': e.id, 'name': e.name} for e in employees]),
        'teams_json': json.dumps([{'id': t.id, 'name': t.name} for t in teams]),
        'projects_json': projects_json,
        'processes_json': processes_json,
        'okrs_json': okrs_json,
        'routines_json': routines_json,
    }

indicators_bp = Blueprint('indicators', __name__)


def _get_company_tree_node(company_id: int, node_id: int | None):
    if not node_id:
        return None
    return IndicatorTree.query.filter_by(id=node_id, company_id=company_id).first()

@indicators_bp.route('/indicators')
@permission_required('indicators', 'view')
def indicators_list():
    """Unified Indicators list page"""
    from flask import session, redirect, url_for
    from models import Indicator
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    
    from sqlalchemy import func
    from models import Indicator, IndicatorGoal, IndicatorData

    # Subqueries for counts
    goals_count_sq = db.session.query(
        IndicatorGoal.indicator_id, 
        func.count(IndicatorGoal.id).label('count')
    ).filter_by(company_id=int(company_id)).group_by(IndicatorGoal.indicator_id).subquery()

    data_count_sq = db.session.query(
        IndicatorData.indicator_id, 
        func.count(IndicatorData.id).label('count')
    ).filter_by(company_id=int(company_id)).group_by(IndicatorData.indicator_id).subquery()


    # Query indicators with counts
    indicators = db.session.query(
        Indicator,
        func.coalesce(goals_count_sq.c.count, 0).label('goals_count'),
        func.coalesce(data_count_sq.c.count, 0).label('data_count')
    ).outerjoin(goals_count_sq, Indicator.id == goals_count_sq.c.indicator_id)\
     .outerjoin(data_count_sq, Indicator.id == data_count_sq.c.indicator_id)\
     .filter(Indicator.company_id == int(company_id))\
     .order_by(Indicator.is_active.desc(), Indicator.source_module, Indicator.name)\
     .all()

    # Attach counts to objects for easy access in Jinja
    final_indicators = []
    for ind, gc, dc in indicators:
        ind.goals_count = gc
        ind.data_count = dc
        final_indicators.append(ind)

    
    employees = Employee.query.filter_by(company_id=int(company_id), status='active').order_by(Employee.name).all()
    tree_nodes = IndicatorTree.query.filter_by(company_id=int(company_id)).order_by(IndicatorTree.code).all()
    teams = Team.query.filter_by(company_id=int(company_id), is_active=True).order_by(Team.name).all()
    
    routines = Routine.query.filter_by(company_id=int(company_id), is_active=True).all()
    import json
    routines_json = json.dumps([{"id": r.id, "name": r.name} for r in routines])
    
    # Using the more complete incentive template as the unified view
    return render_template('modules/incentives/indicator_list.html', 
                         indicators=final_indicators, 
                         employees=employees,
                         tree_nodes=tree_nodes,
                         teams=teams,
                         routines_json=routines_json)



@indicators_bp.route('/indicators/<int:indicator_id>')
@permission_required('indicators', 'view')
def indicator_details(indicator_id):
    """Indicator details page (dashboard/history)"""
    return render_template('modules/indicators/indicator_details_v2.html', indicator_id=indicator_id)

@indicators_bp.route('/indicators/new')
@permission_required('indicators', 'create')
def indicator_new():
    """New indicator form"""
    company_id = session.get('active_company_id')
    if not company_id:
        return redirect(url_for('auth.portal'))
    ctx = _get_form_context(int(company_id))
    return render_template('modules/indicators/indicator_form_v2.html', **ctx)

@indicators_bp.route('/indicators/<int:indicator_id>/edit')
@permission_required('indicators', 'edit')
def indicator_edit(indicator_id):
    """Edit indicator form — usa o mesmo template unificado indicator_form_v2"""
    company_id = session.get('active_company_id')
    if not company_id:
        return redirect(url_for('auth.portal'))
    # Validação de ownership
    ind = Indicator.query.filter_by(id=indicator_id, company_id=int(company_id)).first_or_404()
    ctx = _get_form_context(int(company_id))
    return render_template('modules/indicators/indicator_form_v2.html', indicator_id=indicator_id, **ctx)

# --- Tree (Groups/Hierarchy) ---

@indicators_bp.route('/indicators/tree')
@permission_required('indicators', 'view')
def indicator_tree():
    """Hierarchical tree of indicator groups"""
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    
    # We'll use IndicatorTree model for the hierarchy
    nodes = IndicatorTree.query.filter_by(company_id=int(company_id)).order_by(IndicatorTree.code).all()
    
    # Calcular quais nós têm indicadores para bloquear visualmente
    from sqlalchemy import func
    locked_node_ids = set(
        row[0] for row in
        db.session.query(Indicator.tree_id)
        .filter(Indicator.company_id == int(company_id), Indicator.tree_id.isnot(None))
        .distinct().all()
    )

    return render_template('modules/indicators/indicator_tree.html', nodes=nodes, locked_node_ids=locked_node_ids)

@indicators_bp.route('/indicators/tree/new', methods=['GET', 'POST'])
@indicators_bp.route('/indicators/tree/<int:node_id>/edit', methods=['GET', 'POST'])
@permission_required('indicators', 'create')
def indicator_tree_form(node_id=None):
    """Create or edit tree nodes"""
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    company_id = int(company_id)
    company = Company.query.get(company_id)
    
    node = None
    if node_id:
        node = IndicatorTree.query.get_or_404(node_id)
        if node.company_id != company_id: abort(403)

    # ── TRAVA 1: Bloqueio em GET ──
    # Se o link de "Adicionar Subgrupo" foi clicado para um nó que já possui indicadores, bloqueia.
    pre_selected_parent_id_get = request.args.get('parent_id', type=int)
    if request.method == 'GET' and pre_selected_parent_id_get and not node_id:
        parent_node_check = _get_company_tree_node(company_id, pre_selected_parent_id_get)
        if not parent_node_check:
            flash('Grupo pai inválido para a empresa ativa.', 'danger')
            return redirect(url_for('indicators.indicator_tree'))

        has_indicators_in_parent = _indicator_exists_for_tree(company_id, pre_selected_parent_id_get)
        if has_indicators_in_parent:
            flash(f'O nível "{parent_node_check.name}" já possui indicadores associados. Não é possível criar subníveis abaixo dele.', 'danger')
            return redirect(url_for('indicators.indicator_tree'))

    if request.method == 'POST':
        name = request.form.get('name')
        parent_id_val = request.form.get('parent_id')
        description = request.form.get('description')
        
        parent_id = int(parent_id_val) if parent_id_val and parent_id_val != 'None' else None

        is_new = False
        if not node:
            node = IndicatorTree(company_id=company_id)
            is_new = True

            # ── TRAVA 2: Bloqueio em POST de novo nó ──
            # Proibe criar subnível num nó que já tem indicadores
            if parent_id:
                parent_node_check = _get_company_tree_node(company_id, parent_id)
                if not parent_node_check:
                    flash('Grupo pai inválido para a empresa ativa.', 'danger')
                    return redirect(url_for('indicators.indicator_tree'))

                has_indicators_in_parent = _indicator_exists_for_tree(company_id, parent_id)
                if has_indicators_in_parent:
                    flash(f'O nível "{parent_node_check.name}" já possui indicadores associados. Não é possível criar subníveis abaixo dele.', 'danger')
                    return redirect(url_for('indicators.indicator_tree'))
            
            # --- Automatic Code Generation ---
            company_prefix = company.client_code or "VS"
            if parent_id is None:
                # Root nodes: AA.I.X
                roots = IndicatorTree.query.filter_by(company_id=company_id, parent_id=None).all()
                indices = []
                for r in roots:
                    parts = r.code.split('.')
                    if len(parts) >= 3 and parts[1] == 'I' and parts[2].isdigit():
                        indices.append(int(parts[2]))
                next_idx = max(indices) + 1 if indices else 1
                node.code = f"{company_prefix}.I.{next_idx}"
            else:
                # Child nodes: ParentCode.X
                parent_node = parent_node_check
                children = IndicatorTree.query.filter_by(company_id=company_id, parent_id=parent_id).all()
                indices = []
                for c in children:
                    last_part = c.code.split('.')[-1]
                    if last_part.isdigit():
                        indices.append(int(last_part))
                next_idx = max(indices) + 1 if indices else 1
                node.code = f"{parent_node.code}.{next_idx}"
        # Bloqueios de Segurança:
        if node and not is_new:
            # Precisamos checar se houve tentativa de alteração de hierarquia (mudança de pai)
            if node.parent_id != parent_id:
                # Se está mudando o parent e tem indicadores próprios ou filhos, bloqueia.
                has_indicators = _indicator_exists_for_tree(company_id, node.id)
                if has_indicators:
                    flash('Este nível já possui indicadores associados. Não é possível alterar sua hierarquia (Pai).', 'danger')
                    return redirect(url_for('indicators.indicator_tree_form', node_id=node.id))
            
        node.name = name
        node.description = description
        node.parent_id = parent_id
        
        if is_new:
            db.session.add(node)
        
        try:
            db.session.commit()
            flash('Grupo de indicadores salvo com sucesso!', 'success')
            return redirect(url_for('indicators.indicator_tree'))
        except Exception as e:
            db.session.rollback()
            flash('Erro interno do servidor. Tente novamente ou contate o suporte.', 'danger')

    # List for parent selection (excluding self if editing AND excluding locked nodes)
    # Locked = nós que já possuem indicadores associados
    locked_ids = set(
        row[0] for row in
        db.session.query(Indicator.tree_id)
        .filter(Indicator.company_id == company_id, Indicator.tree_id.isnot(None))
        .distinct().all()
    )
    parents_query = IndicatorTree.query.filter_by(company_id=company_id)
    if node_id:
        parents_query = parents_query.filter(IndicatorTree.id != node_id)
    # Excluir nós travados da lista de opções de pai
    if locked_ids:
        parents_query = parents_query.filter(~IndicatorTree.id.in_(locked_ids))
    parents = parents_query.order_by(IndicatorTree.code).all()
    
    # Pre-select parent from query string if provided (for adding sub-nodes)
    pre_selected_parent_id = request.args.get('parent_id', type=int)

    return render_template('modules/indicators/indicator_tree_form.html', 
                         node=node, parents=parents,
                         locked_ids=locked_ids,
                         pre_selected_parent_id=pre_selected_parent_id,
                         company_prefix=company.client_code or "VS")


@indicators_bp.route('/indicators/tree/<int:node_id>/delete', methods=['POST'])
@permission_required('indicators', 'delete')
def indicator_tree_delete(node_id):
    company_id = session.get('active_company_id')
    if not company_id: return jsonify({'error': 'Unauthorized'}), 401
    company_id = int(company_id)
    
    node = IndicatorTree.query.get_or_404(node_id)
    if node.company_id != company_id: return jsonify({'error': 'Forbidden'}), 403
    
    # Travas solicitadas:
    # 1. Tem indicadores associados?
    has_indicators = _indicator_exists_for_tree(company_id, node.id)
    if has_indicators:
        return jsonify({'error': 'Este nível já possui indicadores associados. Não é possível excluí-lo.'}), 400
        
    # 2. Tem subníveis na árvore?
    has_children = (
        IndicatorTree.query
        .filter_by(company_id=company_id, parent_id=node.id)
        .first()
        is not None
    )
    if has_children:
        return jsonify({'error': 'Este nível possui subníveis. Não é possível excluí-lo antes de excluir os subníveis vazios.'}), 400
        
    try:
        db.session.delete(node)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Nível excluído com sucesso.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno ao excluir nível. Tente novamente ou contate o suporte.'}), 500

# --- Goals (Metas) ---

@indicators_bp.route('/indicators/goals')
@permission_required('indicators', 'view')
def indicator_goals():
    """List of indicator goals"""
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    
    indicators = (
        Indicator.query
        .filter_by(company_id=int(company_id))
        .filter(Indicator.is_active.isnot(False))
        .order_by(Indicator.name)
        .all()
    )
    goals = IndicatorGoal.query.filter_by(company_id=int(company_id)).order_by(IndicatorGoal.goal_date.desc()).all()
    
    ctx = _get_form_context(int(company_id))
    
    # Criar mapeamento de IDs de rotina para nomes para exibição rápida na lista
    from models import Routine
    all_routines = Routine.query.filter_by(company_id=int(company_id)).all()
    routines_map = {r.id: f"{r.code or 'OP'} - {r.name}" for r in all_routines}

    return render_template('modules/indicators/indicator_goals.html', 
                         goals=goals, 
                         indicators=indicators,
                         routines_map=routines_map,
                         **ctx)

@indicators_bp.route('/indicators/measurement-routines')
@permission_required('indicators', 'view')
def measurement_routines():
    """Operaional view of routines selection"""
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    
    from models import Routine, IndicatorGoal, ProcessInstance
    active_goals = IndicatorGoal.query.filter_by(company_id=int(company_id), status='active').filter(IndicatorGoal.routine_id.isnot(None)).all()
    routine_ids = set(g.routine_id for g in active_goals)
    routines = Routine.query.filter(Routine.id.in_(routine_ids)).all()
    
    # Para cada rotina, buscar instância de processo ativa
    routines_data = []
    for r in routines:
        count = sum(1 for g in active_goals if g.routine_id == r.id)
        
        # Instância ativa: pending ou in_progress vinculada a esta routine
        active_instance = ProcessInstance.query.filter(
            ProcessInstance.company_id == int(company_id),
            ProcessInstance.routine_id == r.id,
            ProcessInstance.status.in_(['pending', 'in_progress'])
        ).order_by(ProcessInstance.created_at.desc()).first()
        
        routines_data.append({
            "id": r.id,
            "name": r.name,
            "code": r.code,
            "count": count,
            "instance_id": active_instance.id if active_instance else None,
            "instance_status": active_instance.status if active_instance else None,
            "instance_due": active_instance.due_date.isoformat() if active_instance and active_instance.due_date else None,
        })

    return render_template('modules/indicators/measurement_routines.html', routines_data=routines_data)

@indicators_bp.route('/indicators/routine-execution/<int:routine_id>')
@permission_required('indicators', 'edit')
def routine_execution(routine_id):
    """Spreadsheet-style view for batch indicator data entry"""
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    
    from models import Routine, IndicatorGoal, Indicator, ProcessInstance
    from flask import request as flask_request
    routine = Routine.query.filter_by(id=routine_id, company_id=int(company_id)).first_or_404()
    
    # Captura instância de processo vinculada (se veio de uma execução)
    instance_id = flask_request.args.get('instance_id', type=int)
    active_instance = None
    if instance_id:
        active_instance = ProcessInstance.query.filter_by(
            id=instance_id,
            company_id=int(company_id)
        ).first()
        # Marca como in_progress ao abrir
        if active_instance and active_instance.status == 'pending':
            active_instance.status = 'in_progress'
            from models import db
            db.session.commit()
    
    # Buscar metas ativas vinculadas a esta rotina
    goals = IndicatorGoal.query.filter_by(
        company_id=int(company_id), 
        routine_id=routine_id, 
        status='active'
    ).all()
    
    indicators_meta = []
    for g in goals:
        ind = Indicator.query.filter_by(id=g.indicator_id, company_id=int(company_id)).first()
        if ind:
            indicators_meta.append({
                "indicator": ind,
                "goal": g
            })
    import datetime
    now_date = datetime.datetime.now().strftime('%Y-%m-%d')
            
    return render_template('modules/indicators/indicator_batch_entry.html', 
                         routine=routine, 
                         indicators_meta=indicators_meta,
                         now_date=now_date,
                         active_instance=active_instance,
                         instance_id=instance_id)

# --- Data (Registros) ---

@indicators_bp.route('/indicators/data')
@permission_required('indicators', 'edit')
def indicator_data_list():
    """List of measured data points"""
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    
    goals = IndicatorGoal.query.filter_by(
        company_id=int(company_id),
        status='active'
    ).order_by(
        IndicatorGoal.goal_date.desc(),
        IndicatorGoal.created_at.desc()
    ).all()
    data_records = IndicatorData.query.filter_by(company_id=int(company_id)).order_by(IndicatorData.measured_date.desc()).all()
    
    return render_template('modules/indicators/indicator_data_list.html', 
                         data_records=data_records,
                         goals=goals)

# --- Analysis (Dashboard) ---

@indicators_bp.route('/indicators/dashboard')
@permission_required('indicators', 'view')
def indicator_dashboard():
    """Indicator analysis dashboard — dados reais com status de desempenho"""
    from sqlalchemy import func, text
    import datetime

    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    cid = int(company_id)

    indicators = Indicator.query.filter_by(company_id=cid, is_active=True).order_by(
        Indicator.indicator_type, Indicator.name
    ).all()

    hoje = datetime.date.today()

    # Mapas auxiliares para evitar N+1
    # Metas ativas: pega a primeira meta ativa por indicador
    active_goals_raw = IndicatorGoal.query.filter_by(
        company_id=cid, status='active'
    ).order_by(IndicatorGoal.indicator_id, IndicatorGoal.created_at.desc()).all()

    active_goal_map = {}
    for g in active_goals_raw:
        if g.indicator_id not in active_goal_map:
            active_goal_map[g.indicator_id] = g

    # Último registro de dados por indicador (mês atual)
    last_data_map = {}
    all_data = IndicatorData.query.filter_by(company_id=cid).order_by(
        IndicatorData.indicator_id, IndicatorData.measured_date.desc()
    ).all()
    for d in all_data:
        if d.indicator_id not in last_data_map:
            last_data_map[d.indicator_id] = d

    # Calcular status para cada indicador
    kpi_data = []
    count_on_target = 0
    count_below = 0
    count_no_data = 0

    for ind in indicators:
        goal = active_goal_map.get(ind.id)
        last = last_data_map.get(ind.id)
        
        # Performance calculation
        performance = None
        status_class = 'no_data'
        performance_pct = None

        if goal and last:
            goal_val = float(goal.goal_value) if goal.goal_value else None
            realized = float(last.measured_value)
            
            if goal_val and goal_val != 0:
                performance_pct = round((realized / goal_val) * 100, 1)
                
                # Ranges de performance (com defaults)
                ranges = normalize_performance_ranges(goal.performance_ranges)
                red_max = ranges.get('red', 80)
                yellow_max = ranges.get('yellow', 90)
                green_max = ranges.get('green', 110)
                
                if ind.polarity == 'negative':
                    # Para indicadores negativos (ex: custo), menor é melhor
                    if realized <= goal_val * (red_max / 100):
                        status_class = 'on_target'
                        count_on_target += 1
                    elif realized <= goal_val * (yellow_max / 100):
                        status_class = 'alert'
                        count_below += 1
                    else:
                        status_class = 'below'
                        count_below += 1
                else:
                    if performance_pct >= green_max:
                        status_class = 'exceeded'
                        count_on_target += 1
                    elif performance_pct >= yellow_max:
                        status_class = 'on_target'
                        count_on_target += 1
                    elif performance_pct >= red_max:
                        status_class = 'alert'
                        count_below += 1
                    else:
                        status_class = 'below'
                        count_below += 1
        elif not last:
            status_class = 'no_data'
            count_no_data += 1
        else:
            # tem dado mas sem meta
            status_class = 'no_goal'

        kpi_data.append({
            'indicator': ind,
            'goal': goal,
            'last_data': last,
            'performance_pct': performance_pct,
            'status_class': status_class,
        })

    # Contagens por tipo
    type_counts = {
        'effort': sum(1 for k in kpi_data if k['indicator'].indicator_type == 'effort'),
        'result': sum(1 for k in kpi_data if k['indicator'].indicator_type == 'result'),
        'impact': sum(1 for k in kpi_data if k['indicator'].indicator_type == 'impact'),
    }

    # Pegar grupos (IndicatorTree) da empresa para filtro
    tree_nodes = IndicatorTree.query.filter_by(company_id=cid).order_by(IndicatorTree.code).all()

    return render_template(
        'modules/indicators/indicator_dashboard.html',
        kpi_data=kpi_data,
        indicators=indicators,
        tree_nodes=tree_nodes,
        type_counts=type_counts,
        count_on_target=count_on_target,
        count_below=count_below,
        count_no_data=count_no_data,
        hoje=hoje,
    )

@indicators_bp.route('/indicators/analysis')
@permission_required('indicators', 'view')
def indicator_analysis():
    """Análise comparativa de indicadores, metas e medições históricas."""
    company_id = session.get('active_company_id')
    if not company_id:
        return redirect(url_for('auth.portal'))

    cid = int(company_id)

    indicators = Indicator.query.filter_by(
        company_id=cid,
        is_active=True
    ).order_by(Indicator.code.asc(), Indicator.name.asc()).all()

    indicator_ids = [indicator.id for indicator in indicators]
    goals = []
    data_records = []

    if indicator_ids:
        goals = IndicatorGoal.query.filter(
            IndicatorGoal.company_id == cid,
            IndicatorGoal.indicator_id.in_(indicator_ids)
        ).order_by(
            IndicatorGoal.indicator_id.asc(),
            IndicatorGoal.period_start.desc(),
            IndicatorGoal.goal_date.desc(),
            IndicatorGoal.created_at.desc()
        ).all()

        goal_ids = [goal.id for goal in goals]
        if goal_ids:
            data_records = IndicatorData.query.filter(
                IndicatorData.company_id == cid,
                IndicatorData.goal_id.in_(goal_ids)
            ).order_by(
                IndicatorData.goal_id.asc(),
                IndicatorData.measured_date.asc(),
                IndicatorData.created_at.asc()
            ).all()

    indicators_payload = [
        {
            'id': indicator.id,
            'code': indicator.code,
            'name': indicator.name,
            'unit': indicator.unit,
            'polarity': indicator.polarity,
        }
        for indicator in indicators
    ]

    goals_payload = [
        {
            'id': goal.id,
            'indicator_id': goal.indicator_id,
            'code': goal.code,
            'goal_value': float(goal.goal_value) if goal.goal_value is not None else None,
            'goal_date': goal.goal_date.isoformat() if goal.goal_date else None,
            'period_start': goal.period_start.isoformat() if goal.period_start else None,
            'period_end': goal.period_end.isoformat() if goal.period_end else None,
            'status': goal.status,
            'goal_type': goal.goal_type,
        }
        for goal in goals
    ]

    data_payload = [
        {
            'id': record.id,
            'indicator_id': record.indicator_id,
            'goal_id': record.goal_id,
            'measured_value': float(record.measured_value) if record.measured_value is not None else None,
            'measured_date': record.measured_date.isoformat() if record.measured_date else None,
            'status': record.status,
        }
        for record in data_records
    ]

    return render_template(
        'modules/indicators/comparative_analysis.html',
        indicators_payload=indicators_payload,
        goals_payload=goals_payload,
        data_payload=data_payload,
    )

# --- API Actions ---

@indicators_bp.route('/api/indicators/<int:indicator_id>/toggle-active', methods=['POST'])
@permission_required('indicators', 'edit')
def toggle_indicator_active(indicator_id):
    company_id = session.get('active_company_id')
    if not company_id: return jsonify({"error": "Sessão expirada"}), 401
    
    ind = Indicator.query.filter_by(id=indicator_id, company_id=int(company_id)).first_or_404()
    ind.is_active = not ind.is_active
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "is_active": ind.is_active,
        "message": f"Indicador {'ativado' if ind.is_active else 'inativado'} com sucesso."
    })

@indicators_bp.route('/api/indicators/<int:indicator_id>', methods=['DELETE'])
@permission_required('indicators', 'delete')
def delete_indicator(indicator_id):
    company_id = session.get('active_company_id')
    if not company_id: return jsonify({"error": "Sessão expirada"}), 401
    
    ind = Indicator.query.filter_by(id=indicator_id, company_id=int(company_id)).first_or_404()

    try:
        goals_count = IndicatorGoal.query.filter_by(company_id=int(company_id), indicator_id=ind.id).count()
        data_count = IndicatorData.query.filter_by(company_id=int(company_id), indicator_id=ind.id).count()
        if goals_count > 0 or data_count > 0:
            return jsonify({
                "error": (
                    "Não é possível excluir o indicador porque existem "
                    f"{goals_count} meta(s) e {data_count} registro(s) vinculados."
                )
            }), 409

        ind.is_active = False
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "Indicador excluído com soft delete (inativado) com sucesso.",
            "id": ind.id,
            "is_active": ind.is_active,
        })
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Erro interno ao inativar indicador. Tente novamente ou contate o suporte."}), 500
