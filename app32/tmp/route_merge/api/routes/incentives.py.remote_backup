from datetime import datetime, date
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from services.incentive_service import IncentiveService
from models import Company, IncentiveRuleSet, Employee, IncentiveCalculation, Indicator, IncentiveParticipant, db

incentives_bp = Blueprint('incentives', __name__, template_folder='templates')

# ── INDICADORES ──────────────────────────────────────────────────────────────

@incentives_bp.route('/incentives/indicators')
@login_required
def indicator_list():
    return redirect(url_for('indicators.indicators_list'))


@incentives_bp.route('/incentives/indicators/new', methods=['POST'])
@login_required
def indicator_create():
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    company_id = int(company_id)

    ind = Indicator(
        company_id=company_id,
        code=request.form.get('code', '').strip().upper(),
        name=request.form.get('name', '').strip(),
        description=request.form.get('description', '').strip() or None,
        indicator_type=request.form.get('indicator_type', 'individual'),
        source_module=request.form.get('source_module', 'manual'),
        source_id=request.form.get('source_id') or None,
        collection_mode=request.form.get('collection_mode', 'auto_interno'),
        aggregation_function=request.form.get('aggregation_function', 'score_ratio'),
        unit=request.form.get('unit', 'pts'),
        is_active=True,
    )
    db.session.add(ind)
    db.session.commit()
    flash(f'Indicador "{ind.name}" criado com sucesso!', 'success')
    return redirect(url_for('incentives.indicator_list'))


@incentives_bp.route('/incentives/indicators/<int:indicator_id>/edit', methods=['GET', 'POST'])
@login_required
def indicator_edit(indicator_id):
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    company_id = int(company_id)

    ind = Indicator.query.get_or_404(indicator_id)
    if ind.company_id != company_id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('incentives.indicator_list'))

    if request.method == 'POST':
        ind.code = request.form.get('code', ind.code).strip().upper()
        ind.name = request.form.get('name', ind.name).strip()
        ind.description = request.form.get('description', '').strip() or None
        ind.indicator_type = request.form.get('indicator_type', ind.indicator_type)
        ind.source_module = request.form.get('source_module', ind.source_module)
        ind.source_id = request.form.get('source_id') or None
        ind.collection_mode = request.form.get('collection_mode', ind.collection_mode)
        ind.aggregation_function = request.form.get('aggregation_function', ind.aggregation_function)
        ind.unit = request.form.get('unit', ind.unit)
        db.session.commit()
        flash(f'Indicador "{ind.name}" atualizado.', 'success')
        return redirect(url_for('incentives.indicator_list'))

    return render_template('modules/incentives/indicator_edit.html', ind=ind)

@incentives_bp.route('/incentives')
@login_required
def dashboard():
    company_id = session.get('active_company_id')
    if not company_id:
        return redirect(url_for('auth.portal'))
    
    company = Company.query.get(company_id)
    rule_sets = IncentiveRuleSet.query.filter_by(company_id=company_id).all()
    
    # Dynamic Stats
    from models import Indicator, IncentiveCalculation, db
    from sqlalchemy import func
    
    indicators_count = Indicator.query.filter_by(company_id=company_id, is_active=True).count()
    
    # Get last calculation totals
    last_calc = IncentiveCalculation.query.filter_by(company_id=company_id).order_by(IncentiveCalculation.created_at.desc()).first()
    
    # Historical Summary (Last 6 calculations)
    history = IncentiveCalculation.query.filter_by(company_id=company_id).order_by(IncentiveCalculation.created_at.desc()).limit(6).all()
    
    return render_template(
        'modules/incentives/dashboard.html',
        company=company,
        rule_sets=rule_sets,
        stats={
            "indicators": indicators_count,
            "total_payout": last_calc.total_distributed if last_calc else 0,
            "participants": last_calc.participants_count if last_calc else 0,
            "last_closing": last_calc.period_end if last_calc else None
        },
        history=history
    )

@incentives_bp.route('/incentives/spider-web')
@login_required
def spider_web():
    company_id = session.get('active_company_id')
    if not company_id:
        return redirect(url_for('auth.portal'))
        
    return render_template('modules/incentives/spider_web.html')

@incentives_bp.route('/incentives/rules/new', methods=['GET', 'POST'])
@login_required
def create_rule_set():
    company_id_raw = session.get('active_company_id')
    if not company_id_raw:
        return redirect(url_for('auth.portal'))
    company_id = int(company_id_raw)

    if request.method == 'POST':
        name        = request.form.get('name', 'Novo Plano').strip() or 'Novo Plano'
        description = request.form.get('description', '').strip()
        periodicity = request.form.get('periodicity', 'monthly')
        valid_from  = request.form.get('valid_from') or None
        valid_to    = request.form.get('valid_to') or None

        new_rs = IncentiveRuleSet(
            company_id=company_id,
            name=name,
            description=description,
            periodicity=periodicity,
            valid_from=valid_from,
            valid_to=valid_to
        )
        db.session.add(new_rs)
        db.session.commit()

        flash(f'Plano "{name}" criado com sucesso! Configure os indicadores.', 'success')
        return redirect(url_for('incentives.manage_rules', rule_set_id=new_rs.id))

    # GET — exibe formulário
    return render_template('modules/incentives/plan_new.html')

@incentives_bp.route('/incentives/rules/<int:rule_set_id>', methods=['PATCH'])
@login_required
def rule_set_update(rule_set_id):
    company_id = int(session.get('active_company_id', 0))
    rs = IncentiveRuleSet.query.get_or_404(rule_set_id)
    if rs.company_id != company_id:
        return jsonify({"error": "Acesso negado"}), 403

    data = request.get_json() or {}
    for field in ('name', 'description', 'periodicity'):
        if field in data: setattr(rs, field, data[field])
    
    for field in ('max_red_total',):
        if field in data: setattr(rs, field, float(data[field]) if data[field] else None)

    db.session.commit()
    return jsonify({"ok": True}), 200

@incentives_bp.route('/incentives/rules/<int:rule_set_id>', methods=['GET'])
@login_required
def manage_rules(rule_set_id):
    company_id_raw = session.get('active_company_id')
    if not company_id_raw:
        return redirect(url_for('auth.portal'))
    company_id = int(company_id_raw)
    rule_set = IncentiveRuleSet.query.get_or_404(rule_set_id)

    if rule_set.company_id != company_id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('incentives.dashboard'))

    from models import IncentiveRule, IncentiveParticipant

    # Participantes do plano
    participants = IncentiveParticipant.query.filter_by(
        rule_set_id=rule_set_id, company_id=company_id
    ).all()

    # Vetores de Premiação configurados
    vetores = IncentiveRule.query.filter_by(rule_set_id=rule_set_id).order_by(
        IncentiveRule.order_index
    ).all()

    # Catálogo de indicadores disponíveis (para adicionar vetores)
    indicators_available = Indicator.query.filter_by(
        company_id=company_id, is_active=True
    ).order_by(Indicator.source_module, Indicator.name).all()

    # Colaboradores elegíveis (para adicionar participantes)
    employees = Employee.query.filter_by(
        company_id=company_id, status='active'
    ).order_by(Employee.name).all()

    return render_template(
        'modules/incentives/plan_manage.html',
        rule_set=rule_set,
        participants=participants,
        vetores=vetores,
        indicators_available=indicators_available,
        employees=employees,
        tab=request.args.get('tab', 'overview'),
    )


# ── PARTICIPANTES ─────────────────────────────────────────────────────────────

@incentives_bp.route('/incentives/rules/<int:rule_set_id>/participants', methods=['POST'])
@login_required
def participant_add(rule_set_id):
    company_id = int(session.get('active_company_id', 0))
    rule_set = IncentiveRuleSet.query.get_or_404(rule_set_id)
    if rule_set.company_id != company_id:
        return jsonify({"error": "Acesso negado"}), 403

    from models import IncentiveParticipant
    data = request.get_json() or request.form

    employee_id = int(data.get('employee_id', 0))
    valor_base  = float(data.get('valor_base', 0))
    data_entrada = data.get('data_entrada') or None

    # Evitar duplicata
    existing = IncentiveParticipant.query.filter_by(
        rule_set_id=rule_set_id, employee_id=employee_id
    ).first()
    if existing:
        return jsonify({"error": "Colaborador já está no plano"}), 400

    p = IncentiveParticipant(
        company_id=company_id,
        rule_set_id=rule_set_id,
        employee_id=employee_id,
        valor_base=valor_base,
        elegivel=True,
        data_entrada=data_entrada,
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({"ok": True, "participant": p.to_dict()}), 201


@incentives_bp.route('/incentives/participants/<int:participant_id>', methods=['PATCH', 'DELETE'])
@login_required
def participant_update(participant_id):
    company_id = int(session.get('active_company_id', 0))
    from models import IncentiveParticipant
    p = IncentiveParticipant.query.get_or_404(participant_id)
    if p.company_id != company_id:
        return jsonify({"error": "Acesso negado"}), 403

    if request.method == 'DELETE':
        db.session.delete(p)
        db.session.commit()
        return jsonify({"ok": True}), 200

    data = request.get_json() or {}
    if 'valor_base' in data:
        p.valor_base = float(data['valor_base'])
    if 'elegivel' in data:
        p.elegivel = bool(data['elegivel'])
    if 'notas' in data:
        p.notas = data['notas']
    if 'data_entrada' in data:
        p.data_entrada = data['data_entrada'] or None
    db.session.commit()
    return jsonify({"ok": True, "participant": p.to_dict()}), 200


# ── VETORES DE PREMIAÇÃO ──────────────────────────────────────────────────────

@incentives_bp.route('/incentives/rules/<int:rule_set_id>/vetores', methods=['POST'])
@login_required
def vetor_add(rule_set_id):
    company_id = int(session.get('active_company_id', 0))
    rule_set = IncentiveRuleSet.query.get_or_404(rule_set_id)
    if rule_set.company_id != company_id:
        return jsonify({"error": "Acesso negado"}), 403

    from models import IncentiveRule
    data = request.get_json() or request.form

    v = IncentiveRule(
        company_id=company_id,
        rule_set_id=rule_set_id,
        indicator_id=int(data.get('indicator_id', 0)),
        vetor_type=data.get('vetor_type', 'bonus'),
        impact_value=float(data.get('impact_value', 1.0)),
        weight=float(data.get('impact_value', 1.0)), # legacy
        target_value=data.get('target_value') or None,
        min_threshold=data.get('min_threshold') or None,
        max_cap=data.get('max_cap') or None,
        max_reduction=data.get('max_reduction') or None,
        incidencia=data.get('incidencia', 'individual'),
        order_index=IncentiveRule.query.filter_by(rule_set_id=rule_set_id).count(),
    )
    db.session.add(v)
    db.session.commit()
    return jsonify({"ok": True, "vetor": v.to_dict()}), 201


@incentives_bp.route('/incentives/vetores/<int:vetor_id>', methods=['PATCH', 'DELETE'])
@login_required
def vetor_update(vetor_id):
    company_id = int(session.get('active_company_id', 0))
    from models import IncentiveRule
    v = IncentiveRule.query.get_or_404(vetor_id)
    rs = IncentiveRuleSet.query.get(v.rule_set_id)
    if not rs or rs.company_id != company_id:
        return jsonify({"error": "Acesso negado"}), 403

    if request.method == 'DELETE':
        db.session.delete(v)
        db.session.commit()
        return jsonify({"ok": True}), 200

    data = request.get_json() or {}
    for field in ('vetor_type', 'incidencia'):
        if field in data: setattr(v, field, data[field])
    for field in ('weight', 'impact_value', 'target_value', 'min_threshold', 'max_cap', 'max_reduction'):
        if field in data: setattr(v, field, float(data[field]) if data[field] else None)
    # Sync impact_value and weight if one is provided
    if 'impact_value' in data: v.weight = v.impact_value
    elif 'weight' in data: v.impact_value = v.weight
    db.session.commit()
    return jsonify({"ok": True, "vetor": v.to_dict()}), 200

@incentives_bp.route('/incentives/reports')
@login_required
def reports_selector():
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    
    # Se vier ID por query param, redireciona para o fechamento (suporte a GET simples)
    calc_id = request.args.get('calc_id')
    if calc_id:
        return redirect(url_for('incentives.closing_report', calc_id=calc_id))
    
    rule_sets = IncentiveRuleSet.query.filter_by(company_id=company_id).all()
    calculations = IncentiveCalculation.query.filter_by(company_id=company_id).order_by(IncentiveCalculation.period_start.desc()).all()
    
    return render_template(
        'modules/incentives/reports_selector.html',
        rule_sets=rule_sets,
        calculations=calculations
    )

@incentives_bp.route('/incentives/statement')
@incentives_bp.route('/incentives/statement/<int:calc_id>/<int:employee_id>')
@login_required
def statement(calc_id=None, employee_id=None):
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    company_id = int(company_id)
    
    # Target employee
    if employee_id:
        # TODO: Permission check for manager
        employee = Employee.query.get_or_404(employee_id)
    else:
        employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
        
    if not employee or employee.company_id != company_id:
        flash("Vínculo de colaborador não encontrado.", "warning")
        return redirect(url_for('incentives.dashboard'))
    
    # Target calculation
    if calc_id:
        calc = IncentiveCalculation.query.get_or_404(calc_id)
    else:
        # Search for any recent calculation to at least show the structure
        calc = IncentiveCalculation.query.filter_by(
            company_id=company_id
        ).order_by(IncentiveCalculation.created_at.desc()).first()
    
    statement_data = None
    if calc and calc.results_payload:
        # Normalize: calculate participants list safely
        participants = calc.results_payload.get('participants', [])
        # Ensure ID comparison is correct (int vs possible string/None)
        statement_data = next((p for p in participants if int(p.get('employee_id', 0)) == employee.id), None)
        
    return render_template(
        'modules/incentives/statement.html',
        employee=employee,
        calculation=calc,
        statement=statement_data,
        is_manager_view=(employee_id is not None)
    )

@incentives_bp.route('/incentives/closing/<int:calc_id>')
@login_required
def closing_report(calc_id):
    try:
        company_id = session.get('active_company_id')
        if not company_id: 
            flash("Sessão expirada ou empresa não selecionada.", "warning")
            return redirect(url_for('auth.portal'))
        
        company_id = int(company_id)
        calc = IncentiveCalculation.query.get_or_404(calc_id)
        
        # LOG
        with open('debug_inc_redirect.txt', 'a') as f:
            f.write(f"ACCESS: Calc {calc_id}, Co {calc.company_id}, Sess {company_id}\n")

        if calc.company_id != company_id:
            flash(f"Acesso negado. Esta apuração (ID {calc_id}) pertence à empresa ID {calc.company_id}, mas você está na empresa ID {company_id}.", "error")
            return redirect(url_for('incentives.dashboard'))
            
        participants = calc.results_payload.get('participants', []) if calc.results_payload else []
        
        return render_template(
            'modules/incentives/closing.html',
            calculation=calc,
            participants=participants
        )
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        with open('debug_inc_redirect.txt', 'a') as f:
            f.write(f"ERROR: {str(e)}\n{err}\n")
        flash(f"Erro ao carregar relatório: {str(e)}", "danger")
        return redirect(url_for('incentives.reports_selector'))
@incentives_bp.route('/incentives/validation')
@login_required
def validation_panel():
    company_id = int(session.get('active_company_id', 0))
    from services.incentive_service import IncentiveService
    from models import IncentiveFact, Indicator
    
    today = date.today()
    p_start = date(today.year, today.month, 1)
    p_end = today
    
    facts = IncentiveFact.query.filter(
        IncentiveFact.company_id == company_id,
        IncentiveFact.period_start == p_start,
        IncentiveFact.period_end == p_end
    ).all()
    
    # Agrupa por indicador
    grouped = {}
    for f in facts:
        grouped.setdefault(f.indicator_id, {"indicator": f.indicator, "facts": [], "all_ok": True})
        grouped[f.indicator_id]["facts"].append(f)
        if f.status != 'verified':
            grouped[f.indicator_id]["all_ok"] = False
            
    manual_pending = IncentiveService.harvest_manual_pending(company_id, p_start, p_end)
            
    return render_template(
        'modules/incentives/validation_panel.html',
        grouped_facts=grouped,
        total_facts_count=len(facts),
        manual_pending=manual_pending,
        period_start=p_start,
        period_end=p_end
    )

@incentives_bp.route('/api/v1/incentives/facts/<int:fact_id>', methods=['PATCH'])
@login_required
def fact_update(fact_id):
    company_id = int(session.get('active_company_id', 0))
    fact = IncentiveFact.query.get_or_404(fact_id)
    if fact.company_id != company_id: return jsonify({"error": "Acesso negado"}), 403
    
    data = request.get_json()
    if 'value' in data:
        fact.value = float(data['value'])
        fact.status = 'verified' # Edição manual marca como verificado
    db.session.commit()
    return jsonify({"ok": True})

@incentives_bp.route('/api/v1/incentives/facts/<int:fact_id>/verify', methods=['POST'])
@login_required
def fact_verify(fact_id):
    company_id = int(session.get('active_company_id', 0))
    fact = IncentiveFact.query.get_or_404(fact_id)
    if fact.company_id != company_id: return jsonify({"error": "Acesso negado"}), 403
    
    fact.status = 'verified'
    db.session.commit()
    return jsonify({"ok": True})

@incentives_bp.route('/incentives/calculate/run')
@login_required
def calculate_run():
    # Simplificado: pega o plano ativo e roda para o mês atual
    company_id = int(session.get('active_company_id', 0))
    rs = IncentiveRuleSet.query.filter_by(company_id=company_id, is_active=True).first()
    if not rs:
        flash("Nenhum plano ativo encontrado para processar.", "warning")
        return redirect(url_for('incentives.dashboard'))
        
    today = date.today()
    p_start = date(today.year, today.month, 1)
    p_end = today
    
    from services.incentive_service import IncentiveService
    res = IncentiveService.calculate_incentive(company_id, rs.id, p_start, p_end)
    
    if 'error' in res:
        flash(res['error'], "danger")
        return redirect(url_for('incentives.validation_panel'))
        
    flash(f"Apuração gerada com sucesso para {len(res['participants'])} participantes!", "success")
    return redirect(url_for('incentives.closing_report', calc_id=res['calculation_id']))


# ── INTEGRAÇÃO E COLETA ───────────────────────────────────────────────────────

@incentives_bp.route('/api/v1/incentives/facts/webhook', methods=['POST'])
@login_required # Ou Token/API Key em produção real
def webhook_facts():
    """
    Endpoint para recepção de fatos de sistemas externos (API_EXTERNA).
    Esperado: {
        "indicator_code": "KPI-001",
        "employee_id": 123,
        "period_start": "2024-01-01",
        "period_end": "2024-01-31",
        "value": 0.85,
        "evidence": {...}
    }
    """
    company_id = int(session.get('active_company_id', 0))
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Payload vazio"}), 400
        
    indicator = Indicator.query.filter_by(
        company_id=company_id, code=data.get('indicator_code')
    ).first()
    
    if not indicator:
        return jsonify({"error": "Indicador não encontrado"}), 404

    from services.incentive_service import IncentiveService
    fact = IncentiveService._upsert_fact(
        company_id=company_id,
        indicator_id=indicator.id,
        employee_id=data.get('employee_id'),
        period_start=datetime.strptime(data.get('period_start'), "%Y-%m-%d").date(),
        period_end=datetime.strptime(data.get('period_end'), "%Y-%m-%d").date(),
        value=float(data.get('value')),
        evidence=data.get('evidence', {})
    )
    db.session.commit()
    
    return jsonify({"ok": True, "fact_id": fact.id}), 201


@incentives_bp.route('/incentives/harvest/run', methods=['POST'])
@login_required
def trigger_harvest():
    """Gatilho manual para rodar os harvesters nativos."""
    company_id = int(session.get('active_company_id', 0))
    from services.incentive_service import IncentiveService
    from datetime import date
    
    # Datas do mês atual por padrão se não informado
    today = date.today()
    p_start = date(today.year, today.month, 1)
    p_end = today
    
    results = IncentiveService.harvest_all_modules(company_id, p_start, p_end)
    db.session.commit()
    
    summary = results.get('summary', {})
    flash(f"Coleta concluída! Processos: {summary.get('processo',0)} | Projetos: {summary.get('projeto',0)} | Ocorrências: {summary.get('ocorrencia',0)}", "success")
    
    return redirect(url_for('incentives.dashboard'))
