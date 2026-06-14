import os
import logging
import math
from pathlib import Path

PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."

from flask import Blueprint, render_template, request, jsonify, send_from_directory, current_app, session, redirect, url_for, abort, flash
from flask_login import current_user
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from datetime import datetime

from database import get_db
from models import db, Company, MacroProcess, Process, ProcessInstance, Employee, Indicator, ProcessRoutine, Routine, ProcessActivityExecutionContract, ProcessBpmnDiagram
from schemas.routine_journey import RoutineJourneyBindingUpsertSchema
from services.process_bpmn_service import get_latest_diagram, serialize_flow_snapshot
from services.process_portal_service import (
    ProcessPortalAccessError,
    build_process_portal_process_detail,
    build_process_portal_summary,
)
from services.strategic_management_panel_service import build_strategic_management_panel
from utils.indicator_filters import PROCESS_SOURCE_MODULES, indicator_supports_source_context
from utils.permissions import get_default_company_id, permission_required, has_permission, has_company_full_access, is_collaborator_in_company, can_model_process

processes_bp = Blueprint('processes', __name__)
logger = logging.getLogger(__name__)


def _process_bpmn_modeler_asset_version() -> str:
    root = Path(current_app.root_path)
    candidates = [
        root / 'static' / 'css' / 'process_bpmn_modeler.css',
        root / 'static' / 'js' / 'process_bpmn_modeler.js',
        root / 'templates' / 'modules' / 'processes' / 'bpmn_modeler.html',
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return '1'
    latest_mtime = max(int(path.stat().st_mtime) for path in existing)
    return str(latest_mtime)


def _build_process_map_compact_context(company_id: int, *, area_id: int | None = None, macro_id: int | None = None):
    """
    Contexto único do MP-2 para evitar drift entre:
    - /process-map/compact
    - /companies/<company_id>/process-portal
    """
    if not company_id:
        raise ValueError("Nenhuma empresa ativa selecionada.")

    db_helper = get_db()
    company = Company.query.get(company_id)
    if not company:
        raise LookupError(f"Empresa com ID {company_id} não encontrada.")

    map_data = db_helper.get_process_map(company_id)

    process_ids = []
    for area in map_data.get('areas', []):
        for macro in area.get('macros', []):
            for p in macro.get('processes', []):
                if p.get('id'):
                    process_ids.append(int(p['id']))

    routine_counts = {}
    indicator_counts = {}
    spec_counts = {}
    published_flow_ids = set()

    if process_ids:
        for process_id, total in (
            db.session.query(ProcessRoutine.process_id, db.func.count(ProcessRoutine.id))
            .filter(ProcessRoutine.company_id == company_id)
            .filter(ProcessRoutine.process_id.in_(process_ids))
            .group_by(ProcessRoutine.process_id)
            .all()
        ):
            if process_id is not None:
                routine_counts[int(process_id)] = int(total or 0)

        for process_id, total in (
            db.session.query(Routine.process_id, db.func.count(Routine.id))
            .filter(Routine.company_id == company_id)
            .filter(Routine.process_id.in_(process_ids))
            .group_by(Routine.process_id)
            .all()
        ):
            if process_id is not None:
                routine_counts[int(process_id)] = routine_counts.get(int(process_id), 0) + int(total or 0)

        if indicator_supports_source_context():
            for process_id, total in (
                db.session.query(Indicator.source_id, db.func.count(Indicator.id))
                .filter(Indicator.company_id == company_id)
                .filter(Indicator.is_active.is_(True))
                .filter(Indicator.source_module.in_(PROCESS_SOURCE_MODULES))
                .filter(Indicator.source_id.in_(process_ids))
                .group_by(Indicator.source_id)
                .all()
            ):
                if process_id is not None:
                    indicator_counts[int(process_id)] = int(total or 0)

        for process_id, total in (
            db.session.query(Indicator.process_id, db.func.count(Indicator.id))
            .filter(Indicator.company_id == company_id)
            .filter(Indicator.is_active.is_(True))
            .filter(Indicator.process_id.in_(process_ids))
            .group_by(Indicator.process_id)
            .all()
        ):
            if process_id is not None:
                indicator_counts[int(process_id)] = indicator_counts.get(int(process_id), 0) + int(total or 0)

        for process_id, total in (
            db.session.query(ProcessActivityExecutionContract.process_id, db.func.count(ProcessActivityExecutionContract.id))
            .filter(ProcessActivityExecutionContract.company_id == company_id)
            .filter(ProcessActivityExecutionContract.is_active.is_(True))
            .filter(ProcessActivityExecutionContract.process_id.in_(process_ids))
            .group_by(ProcessActivityExecutionContract.process_id)
            .all()
        ):
            if process_id is not None:
                spec_counts[int(process_id)] = int(total or 0)

        published_flow_ids = {
            int(process_id)
            for (process_id,) in (
                db.session.query(ProcessBpmnDiagram.process_id)
                .filter(ProcessBpmnDiagram.company_id == company_id)
                .filter(ProcessBpmnDiagram.status == 'published')
                .filter(ProcessBpmnDiagram.process_id.in_(process_ids))
                .distinct()
                .all()
            )
            if process_id is not None
        }

    if area_id:
        map_data['areas'] = [a for a in map_data.get('areas', []) if a['id'] == area_id]
    if macro_id:
        for area in map_data.get('areas', []):
            area['macros'] = [m for m in area.get('macros', []) if m['id'] == macro_id]

    def get_stage_color(stage):
        colors = {
            'inbox': '#cbd5e1', 'designing': '#93c5fd', 'deploying': '#3b82f6',
            'stabilizing': '#a855f7', 'stable': '#6366f1'
        }
        return colors.get(stage, '#cbd5e1')

    def get_perf_color(perf):
        colors = {
            'critical': '#ef4444', 'below': '#f59e0b', 'satisfactory': '#10b981'
        }
        return colors.get(perf, '#f1f5f9')

    for area in map_data.get('areas', []):
        area['display_name'] = f"{area.get('code', '')} - {area.get('name', '')}" if area.get('code') else area.get('name', '')

        for macro in area.get('macros', []):
            macro['display_name'] = f"{macro.get('code', '')} - {macro.get('name', '')}" if macro.get('code') else macro.get('name', '')

            for p in macro.get('processes', []):
                p['display_name'] = f"{p.get('code', '')} - {p.get('name', '')}" if p.get('code') else p.get('name', '')
                p['stage_color'] = get_stage_color(p.get('kanban_stage'))
                p['perf_color'] = get_perf_color(p.get('performance_level'))
                process_id = int(p.get('id') or 0)
                p['portal_stats'] = {
                    'flow_count': 1 if process_id in published_flow_ids else 0,
                    'routine_count': int(routine_counts.get(process_id, 0)),
                    'indicator_count': int(indicator_counts.get(process_id, 0)),
                    'spec_count': int(spec_counts.get(process_id, 0)),
                }
                p['has_portal_assets'] = any([
                    p['portal_stats']['flow_count'] > 0,
                    p['portal_stats']['routine_count'] > 0,
                    p['portal_stats']['indicator_count'] > 0,
                    p['portal_stats']['spec_count'] > 0,
                ])

    return {
        'company': company,
        'company_name': company.name,
        'areas': map_data.get('areas', []),
        'now': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'is_collaborator': is_collaborator_in_company(company_id),
    }


def _coerce_optional_int(value, default=0):
    if value in (None, ''):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_optional_float(value, default=1.0):
    if value in (None, ''):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_optional_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_hours_used(value):
    """Converte dedicação para horas decimais aceitando decimal e HH:MM.

    A tela de executores usa máscara visual HH:MM (ex.: 04:00), mas o backend
    persiste horas decimais. A validação precisa ser tolerante ao formato real
    enviado pelo navegador para não transformar uma dedicação válida em zero.
    """
    if value in (None, ""):
        return None

    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None

    text = str(value).strip()
    if not text:
        return None

    if ":" in text:
        parts = text.split(":")
        if len(parts) != 2:
            return None
        hours_raw, minutes_raw = (part.strip() for part in parts)
        if not (hours_raw.isdigit() and minutes_raw.isdigit()):
            return None
        minutes = int(minutes_raw)
        if minutes < 0 or minutes > 59:
            return None
        return int(hours_raw) + (minutes / 60)

    normalized = text.replace(" ", "").replace("\u00a0", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    try:
        numeric = float(normalized)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _get_current_company_employee(company_id: int):
    if not current_user.is_authenticated or not company_id:
        return None
    return Employee.query.filter_by(user_id=current_user.id, company_id=company_id, status='active').first()


def _build_published_bpmn_flow_payload(process: Process) -> dict | None:
    diagram = get_latest_diagram(
        process_id=process.id,
        company_id=process.company_id,
        status="published",
    )
    return serialize_flow_snapshot(diagram)


def _fetch_routine_scope(cursor, routine_id: int):
    cursor.execute(
        """
        SELECT
            r.id,
            r.company_id,
            r.process_id,
            r.name,
            r.schedule_type,
            r.schedule_value,
            r.start_time
        FROM routines r
        WHERE r.id = %s
          AND (r.is_active = TRUE OR r.is_active IS NULL)
        """,
        (routine_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _validate_routine_collaborator_payload(data: dict):
    if not isinstance(data, dict):
        return None, "Payload inválido."

    allowed_fields = {"employee_id", "hours_used", "notes"}
    unknown_fields = sorted(set(data.keys()) - allowed_fields)
    if unknown_fields:
        return None, f"Campos não permitidos: {', '.join(unknown_fields)}"

    try:
        employee_id = int(data.get("employee_id"))
    except (TypeError, ValueError):
        return None, "Selecione um colaborador válido."

    hours_used = _parse_hours_used(data.get("hours_used"))
    if hours_used is None:
        return None, "Informe uma dedicação válida."

    if hours_used <= 0:
        return None, "A dedicação deve ser maior que zero."

    notes = _coerce_optional_text(data.get("notes")) or ""
    return {
        "employee_id": employee_id,
        "hours_used": hours_used,
        "notes": notes,
    }, None


def _get_process_with_access(process_id: int, action: str = 'view') -> Process:
    process = Process.query.get_or_404(process_id)

    if not current_user.is_authenticated:
        abort(403, description="Usuário não autenticado.")

    if not has_permission(process.company_id, 'processes', action):
        abort(403, description=f"Permission denied: {action} on processes")

    session['active_company_id'] = process.company_id
    return process


def _get_macro_process_with_access(macro_id: int, action: str = 'view') -> MacroProcess:
    macro = MacroProcess.query.get_or_404(macro_id)

    if not current_user.is_authenticated:
        abort(403, description="Usuário não autenticado.")

    if not has_permission(macro.company_id, 'processes', action):
        abort(403, description=f"Permission denied: {action} on processes")

    session['active_company_id'] = macro.company_id
    return macro


def _build_process_details_payload(process: Process) -> dict:
    """Payload mínimo e resiliente para hidratação inicial da tela de detalhes."""
    macro = getattr(process, 'macro', None)
    area = getattr(macro, 'area', None) if macro else None

    # Link to the unified core Indicator instead of IncentiveIndicator
    ind = None
    try:
        ind = Indicator.query.filter_by(
            source_module='processo',
            source_id=process.id,
            is_active=True
        ).first()
    except Exception:
        ind = None

    return {
        'id': process.id,
        'company_id': process.company_id,
        'macro_id': getattr(process, 'macro_id', None),
        'code': getattr(process, 'code', None),
        'name': process.name,
        'description': getattr(process, 'description', None),
        'responsible': getattr(process, 'responsible', None),
        'responsible_id': getattr(process, 'responsible_id', None),
        'owner_employee_id': getattr(process, 'owner_employee_id', None),
        'kanban_stage': getattr(process, 'kanban_stage', None),
        'structuring_level': getattr(process, 'structuring_level', None),
        'performance_level': getattr(process, 'performance_level', None),
        'order_index': getattr(process, 'order_index', None),
        'flow_document': getattr(process, 'flow_document', None),
        'flow_mermaid': getattr(process, 'flow_mermaid', None),
        'bpmn_flow': _build_published_bpmn_flow_payload(process),
        'notes': getattr(process, 'notes', None),
        'is_active': getattr(process, 'is_active', None),
        'incentive_indicator': ind.to_dict() if ind else None,
        'macro': {
            'id': macro.id,
            'company_id': macro.company_id,
            'area_id': macro.area_id,
            'code': macro.code,
            'name': macro.name,
            'owner': macro.owner,
            'description': macro.description,
            'order_index': macro.order_index,
            'area': {
                'id': area.id,
                'company_id': area.company_id,
                'code': area.code,
                'name': area.name,
                'description': area.description,
                'order_index': area.order_index,
                'color': area.color,
            } if area else None,
        } if macro else None,
    }

@processes_bp.route('/api/processes/upload-flow', methods=['POST'])
def upload_process_flow():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], 'process_flows', filename))
        return jsonify({"success": True, "filename": filename}), 200

@processes_bp.route('/processes')
@permission_required('processes', 'view')
def processes_list():
    """Processes list page"""
    company_id = request.args.get('company_id', type=int) or session.get('active_company_id')
    if not company_id and current_user.is_authenticated:
        company_id = get_default_company_id()
    if company_id:
        session['active_company_id'] = company_id
    return render_template('modules/processes/processes_v2.html', company_id=company_id)

@processes_bp.route('/process-map')
@permission_required('processes', 'view')
def process_map():
    """Process map (Big Picture)"""
    from flask_login import current_user

    arg_company_id = request.args.get('company_id', type=int)
    company_id = arg_company_id or session.get('active_company_id')

    # Fallback: pega a primeira empresa permitida para o usuário
    if not company_id and current_user.is_authenticated:
        company_id = get_default_company_id()
    
    is_collaborator = is_collaborator_in_company(company_id)

    return render_template('modules/processes/process_map_v2.html', 
                           company_id=company_id, 
                           is_collaborator=is_collaborator)


@processes_bp.route('/process-portal')
@permission_required('processes', 'view')
def process_portal_redirect():
    company_id = session.get('active_company_id')
    if not company_id and current_user.is_authenticated:
        company_id = get_default_company_id()
        if company_id:
            session['active_company_id'] = company_id
    if company_id:
        return redirect(url_for('processes.process_portal_page', company_id=company_id))
    return redirect(url_for('my_work.my_work'))


@processes_bp.route('/process-portal/strategic-management')
@permission_required('processes', 'view')
def strategic_management_panel_redirect():
    company_id = session.get('active_company_id')
    if not company_id and current_user.is_authenticated:
        company_id = get_default_company_id()
        if company_id:
            session['active_company_id'] = company_id
    if company_id:
        return redirect(url_for('processes.strategic_management_panel_page', company_id=company_id))
    return redirect(url_for('my_work.my_work'))


@processes_bp.route('/companies/<int:company_id>/process-portal')
@permission_required('processes', 'view')
def process_portal_page(company_id):
    session['active_company_id'] = company_id
    try:
        context = _build_process_map_compact_context(company_id)
    except ValueError as exc:
        return str(exc), 400
    except LookupError as exc:
        return str(exc), 404

    return render_template(
        'modules/processes/process_portal_compact.html',
        **context,
    )


@processes_bp.route('/companies/<int:company_id>/process-portal/processes/<int:process_id>')
@permission_required('processes', 'view')
def process_portal_process_page(company_id, process_id):
    session['active_company_id'] = company_id
    company = Company.query.get_or_404(company_id)
    return render_template(
        'modules/processes/process_portal_process_detail.html',
        company=company,
        company_id=company_id,
        process_id=process_id,
    )


@processes_bp.route('/companies/<int:company_id>/process-portal/strategic-management')
@permission_required('processes', 'view')
def strategic_management_panel_page(company_id):
    session['active_company_id'] = company_id
    company = Company.query.get_or_404(company_id)
    period = request.args.get('period') or 'month'
    try:
        panel = build_strategic_management_panel(company_id, period=period)
    except ValueError as exc:
        return str(exc), 400
    return render_template(
        'modules/processes/strategic_management_panel.html',
        company=company,
        company_id=company_id,
        panel=panel,
    )


@processes_bp.route('/api/companies/<int:company_id>/process-portal', methods=['GET'])
@permission_required('processes', 'view')
def api_process_portal_summary(company_id):
    session['active_company_id'] = company_id
    current_employee = _get_current_company_employee(company_id)
    payload = build_process_portal_summary(
        company_id,
        current_employee_id=current_employee.id if current_employee else None,
        can_manage_all=bool(has_company_full_access(company_id)),
    )
    return jsonify({"ok": True, "data": payload})


@processes_bp.route('/api/companies/<int:company_id>/process-portal/strategic-management', methods=['GET'])
@permission_required('processes', 'view')
def api_strategic_management_panel(company_id):
    session['active_company_id'] = company_id
    period = request.args.get('period') or 'month'
    try:
        payload = build_strategic_management_panel(company_id, period=period)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        current_app.logger.exception(
            "Erro ao montar Painel de Gestão Estratégica company_id=%s",
            company_id,
        )
        return jsonify({"ok": False, "error": PUBLIC_ERROR_MESSAGE}), 500
    return jsonify({"ok": True, "data": payload})


@processes_bp.route('/api/companies/<int:company_id>/process-portal/processes/<int:process_id>', methods=['GET'])
@permission_required('processes', 'view')
def api_process_portal_process_detail(company_id, process_id):
    session['active_company_id'] = company_id
    current_employee = _get_current_company_employee(company_id)
    try:
        payload = build_process_portal_process_detail(
            company_id,
            process_id,
            current_employee_id=current_employee.id if current_employee else None,
            can_manage_all=bool(has_company_full_access(company_id)),
            request_root=request.url_root,
        )
    except ProcessPortalAccessError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception:
        current_app.logger.exception(
            "Erro ao montar detalhe do portal de processos company_id=%s process_id=%s",
            company_id,
            process_id,
        )
        return jsonify({"ok": False, "error": PUBLIC_ERROR_MESSAGE}), 500
    return jsonify({"ok": True, "data": payload})

@processes_bp.route('/process-map/compact')
@permission_required('processes', 'view')
def process_map_compact():
    """Print-friendly Compact Process Map (MP-2)"""
    # Use company_id from query params or session
    arg_id = request.args.get('company_id')
    company_id = request.args.get('company_id', type=int) or session.get('active_company_id')
    
    logger.debug(
        "[DEBUG] MP-2 View Request - arg_id: %s, session_id: %s, final_id: %s",
        arg_id,
        session.get('active_company_id'),
        company_id,
    )
    
    if not company_id:
        return "Nenhuma empresa ativa selecionada.", 400
        
    area_id = request.args.get('area_id', type=int)
    macro_id = request.args.get('macro_id', type=int)
        
    try:
        context = _build_process_map_compact_context(company_id, area_id=area_id, macro_id=macro_id)
    except ValueError as exc:
        return str(exc), 400
    except LookupError as exc:
        return str(exc), 404

    return render_template(
        'modules/processes/process_map_compact_view.html',
        **context,
        page_title='Mapa de Processos',
        toolbar_title='Mapa de Processos',
        heading_title='Mapa de Processos',
        subtitle_company_name=context['company_name'],
        show_close_button=True,
        show_back_button=False,
    )

@processes_bp.route('/processes/<int:process_id>')
@permission_required('processes', 'view')
def process_details(process_id):
    """Process details page (modeling/pops)"""
    process = _get_process_with_access(process_id, action='view')
    if not can_model_process(process.company_id):
        abort(403, description="Acesso negado: Usuário sem permissão para modelar este processo.")

    company = Company.query.get_or_404(process.company_id)
    return render_template('modules/processes/process_details_v2.html', 
                            process_id=process_id, 
                            process=process,
                            company=company,
                            company_id=process.company_id,
                            process_payload=_build_process_details_payload(process))


@processes_bp.route('/processes/<int:process_id>/bpmn-modeler')
@permission_required('processes', 'view')
def process_bpmn_modeler(process_id):
    """APP32 BPMN Modeler page."""
    process = _get_process_with_access(process_id, action='view')
    if not can_model_process(process.company_id):
        abort(403, description="Acesso negado: Usuário sem permissão para modelar este processo.")

    company = Company.query.get_or_404(process.company_id)
    return render_template(
        'modules/processes/bpmn_modeler.html',
        process=process,
        process_id=process.id,
        company=company,
        company_id=process.company_id,
        asset_version=_process_bpmn_modeler_asset_version(),
    )


@processes_bp.route('/processes/<int:process_id>/book')
@permission_required('processes', 'view')
def process_book(process_id):
    """Renderiza o Book do Processo em layout print-friendly do app32."""
    from services.process_book_service import build_process_book_context

    process = _get_process_with_access(process_id, action='view')
    if is_collaborator_in_company(process.company_id):
        abort(403, description="Acesso negado: Colaboradores não podem acessar o book do processo.")

    try:
        context = build_process_book_context(
            process_id=process.id,
            company_id=process.company_id,
            request_root=request.url_root,
        )
    except ValueError as exc:
        current_app.logger.warning('Book do processo indisponível para process_id=%s: %s', process_id, exc)
        abort(404, description=str(exc))

    return render_template('reports/process_book_v2.html', **context)


@processes_bp.route('/macro-processes/<int:macro_id>/book')
@permission_required('processes', 'view')
def macro_process_book(macro_id):
    """Renderiza o Book do Macroprocesso em layout print-friendly client-safe."""
    from services.macro_process_book_service import build_macro_process_book_context, ensure_process_map_context

    macro = _get_macro_process_with_access(macro_id, action='view')
    if is_collaborator_in_company(macro.company_id):
        abort(403, description="Acesso negado: Colaboradores não podem acessar o book do macroprocesso.")

    try:
        context = build_macro_process_book_context(
            macro_id=macro.id,
            company_id=macro.company_id,
            request_root=request.url_root,
        )
        context = ensure_process_map_context(
            context,
            current_macro_id=macro.id,
            company_id=macro.company_id,
        )
    except ValueError as exc:
        current_app.logger.warning('Book do macroprocesso indisponível para macro_id=%s: %s', macro_id, exc)
        abort(404, description=str(exc))

    return render_template('reports/macro_process_book_v1.html', **context)


# --- Process Routines Page and APIs ---

@processes_bp.route('/process-routines')
@permission_required('processes', 'view')
def process_routines_redirect():
    """Redirect to the routine page of the active company."""
    company_id = session.get('active_company_id')
    if not company_id:
        company_id = get_default_company_id()
        if company_id:
            session['active_company_id'] = company_id
    
    if company_id:
        return redirect(url_for('processes.process_routines_page', company_id=company_id))
    
    return redirect(url_for('my_work.my_work'))

@processes_bp.route('/bpms-analysis')
@permission_required('processes', 'view')
def bpms_analysis_redirect():
    company_id = session.get('active_company_id')
    if not company_id:
        company_id = get_default_company_id()
        if company_id:
            session['active_company_id'] = company_id

    if company_id:
        return redirect(url_for('processes.bpms_analysis_page', company_id=company_id))

    return redirect(url_for('my_work.my_work'))

@processes_bp.route('/companies/<int:company_id>/bpms-analysis')
@permission_required('processes', 'view')
def bpms_analysis_page(company_id):
    from services.process_bpms_analysis_service import build_bpms_analysis_page_context

    selected_analysis_id = request.args.get('analysis_id', type=int)
    selected_process_id = request.args.get('process_id', type=int)
    context = build_bpms_analysis_page_context(
        company_id=company_id,
        selected_analysis_id=selected_analysis_id,
        selected_process_id=selected_process_id,
    )
    context['is_collaborator'] = is_collaborator_in_company(company_id)
    return render_template('modules/processes/bpms_analysis.html', **context)

@processes_bp.route('/companies/<int:company_id>/bpms-analysis/save', methods=['POST'])
@permission_required('processes', 'edit')
def bpms_analysis_save(company_id):
    from services.process_bpms_analysis_service import save_bpms_analysis

    if is_collaborator_in_company(company_id):
        abort(403, description="Acesso negado: Colaboradores não podem editar análises BPMS.")

    try:
        analysis = save_bpms_analysis(
            company_id=company_id,
            form_data=request.form.to_dict(flat=True),
            actor_user_id=current_user.id if current_user.is_authenticated else None,
        )
        flash('Análise BPMS salva com sucesso.', 'success')
        return redirect(url_for(
            'processes.bpms_analysis_page',
            company_id=company_id,
            analysis_id=analysis.id,
            process_id=analysis.process_id,
        ))
    except ValueError as exc:
        flash(str(exc), 'warning')
    except Exception:
        current_app.logger.exception('Falha ao salvar análise BPMS para company_id=%s', company_id)
        flash('Não foi possível salvar a análise BPMS agora. Tente novamente em instantes.', 'error')

    process_id = request.form.get('process_id', type=int)
    analysis_id = request.form.get('analysis_id', type=int)
    return redirect(url_for(
        'processes.bpms_analysis_page',
        company_id=company_id,
        process_id=process_id,
        analysis_id=analysis_id,
    ))

@processes_bp.route('/companies/<int:company_id>/processes/<int:process_id>/bpms-analysis')
@permission_required('processes', 'view')
def bpms_analysis_for_process(company_id, process_id):
    process = Process.query.filter_by(company_id=company_id, id=process_id).first_or_404()
    return redirect(url_for('processes.bpms_analysis_page', company_id=company_id, process_id=process.id))

@processes_bp.route('/process-instances')
@permission_required('processes', 'view')
def process_instances_redirect():
    """Redirect to the instances page of the active company."""
    company_id = session.get('active_company_id')
    if not company_id:
        company_id = get_default_company_id()
        if company_id:
            session['active_company_id'] = company_id
    
    if company_id:
        return redirect(url_for('processes.process_instances_page', company_id=company_id))
    
    return redirect(url_for('my_work.my_work'))

@processes_bp.route('/companies/<int:company_id>/process-instances')
@permission_required('processes', 'view')
def process_instances_page(company_id):
    """Render the process instances management page."""
    instance_id = request.args.get('instance_id', type=int)
    if instance_id:
        instance = ProcessInstance.query.filter_by(company_id=company_id, id=instance_id).first()
        if instance:
            session['active_company_id'] = company_id
            return redirect(url_for('my_work.process_instance_view', instance_id=instance.id, company_id=company_id, from_='work-journey'))
    company = Company.query.get_or_404(company_id)
    is_collaborator = is_collaborator_in_company(company_id)
    return render_template('modules/processes/process_instances_list.html', company=company, is_collaborator=is_collaborator)

@processes_bp.route('/process-occurrences')
@permission_required('processes', 'view')
def process_occurrences_redirect():
    """Redirect to the occurrences page of the active company."""
    company_id = session.get('active_company_id')
    if not company_id:
        company_id = get_default_company_id()
        if company_id:
            session['active_company_id'] = company_id
    
    if company_id:
        return redirect(url_for('processes.process_occurrences_page', company_id=company_id))
    
    return redirect(url_for('my_work.my_work'))

@processes_bp.route('/companies/<int:company_id>/process-occurrences')
@permission_required('processes', 'view')
def process_occurrences_page(company_id):
    """Render the process occurrences management page."""
    company = Company.query.get_or_404(company_id)
    is_collaborator = is_collaborator_in_company(company_id)
    current_employee = _get_current_company_employee(company_id)
    return render_template(
        'modules/processes/process_occurrences_list.html',
        company=company,
        is_collaborator=is_collaborator,
        current_employee_id=current_employee.id if current_employee else None,
    )

@processes_bp.route('/companies/<int:company_id>/process-routines')
@permission_required('processes', 'view')
def process_routines_page(company_id):
    """Render the process routines management page."""
    company = Company.query.get_or_404(company_id)
    is_collaborator = is_collaborator_in_company(company_id)
    return render_template('process_routines.html', company=company, is_collaborator=is_collaborator)

@processes_bp.route('/companies/<int:company_id>/process-routines/analysis')
@permission_required('processes', 'view')
def process_routines_analysis_page(company_id):
    """Render analytical page for routine capacity and commitments."""
    from services.routine_analysis_service import get_routine_analysis

    company = Company.query.get_or_404(company_id)
    department = request.args.get('department')
    employee_id = request.args.get('employee_id', type=int)

    current_employee = _get_current_company_employee(company_id)
    if is_collaborator_in_company(company_id):
        if not current_employee:
            abort(403, description='Acesso negado: colaborador sem vínculo ativo na empresa.')
        employee_id = current_employee.id
        department = None

    try:
        analysis = get_routine_analysis(company_id, department=department, employee_id=employee_id)
        return render_template(
            'modules/processes/routine_analysis.html',
            company=company,
            analysis=analysis,
        )
    except Exception:
        current_app.logger.exception(
            'Falha ao carregar análise de rotinas para company_id=%s (department=%s, employee_id=%s)',
            company_id,
            department,
            employee_id,
        )
        flash('Não foi possível aplicar os filtros selecionados. Exibindo a visão geral da análise.', 'warning')
        try:
            analysis = get_routine_analysis(company_id)
            return render_template(
                'modules/processes/routine_analysis.html',
                company=company,
                analysis=analysis,
            )
        except Exception:
            current_app.logger.exception('Falha ao carregar visão geral da análise de rotinas para company_id=%s', company_id)
            flash('Não foi possível carregar a análise de rotinas agora. Tente novamente em instantes.', 'error')
            return redirect(url_for('processes.process_routines_page', company_id=company_id))


@processes_bp.route('/api/companies/<int:company_id>/process-routines/analysis', methods=['GET'])
@permission_required('processes', 'view')
def api_get_process_routines_analysis(company_id):
    """Return analytical payload for routine capacity and commitments."""
    from services.routine_analysis_service import get_routine_analysis

    department = request.args.get('department')
    employee_id = request.args.get('employee_id', type=int)

    current_employee = _get_current_company_employee(company_id)
    if is_collaborator_in_company(company_id):
        if not current_employee:
            return jsonify({"success": False, "message": "Acesso negado: colaborador sem vínculo ativo na empresa."}), 403
        employee_id = current_employee.id
        department = None

    try:
        payload = get_routine_analysis(company_id, department=department, employee_id=employee_id)
        return jsonify({"success": True, "data": payload})
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

@processes_bp.route('/api/companies/<int:company_id>/process-routines', methods=['GET'])
@permission_required('processes', 'view')
def api_get_process_routines(company_id):
    """Get all process routines for a company with collaborator summary"""
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                r.id,
                r.name,
                r.description,
                r.process_id,
                r.schedule_type,
                r.schedule_value,
                r.start_time,
                r.deadline_days,
                r.deadline_hours,
                r.deadline_date,
                p.code AS process_code,
                p.name AS process_name,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'employee_id', rc.employee_id,
                            'employee_name', e.name,
                            'hours_used', rc.hours_used,
                            'notes', rc.notes
                        )
                        ORDER BY e.name
                    )
                    FILTER (WHERE rc.employee_id IS NOT NULL),
                    '[]'::json
                ) AS collaborators
            FROM routines r
            LEFT JOIN processes p ON r.process_id = p.id
            LEFT JOIN routine_collaborators rc ON rc.routine_id = r.id
            LEFT JOIN employees e ON e.id = rc.employee_id
            WHERE r.company_id = %s AND (r.is_active = TRUE OR r.is_active IS NULL)
            GROUP BY
                r.id,
                r.name,
                r.description,
                r.process_id,
                r.schedule_type,
                r.schedule_value,
                r.start_time,
                r.deadline_days,
                r.deadline_hours,
                r.deadline_date,
                p.code,
                p.name
            ORDER BY r.created_at DESC
        """,
            (company_id,),
        )
        
        rows = cursor.fetchall()
        routines = [dict(row) for row in rows]
        conn.close()
        return jsonify({"success": True, "routines": routines})

    except Exception as e:
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500

@processes_bp.route('/api/companies/<int:company_id>/process-routines', methods=['POST'])
@permission_required('processes', 'create')
def api_create_process_routine(company_id):
    """Create a new process routine"""
    if not has_company_full_access(company_id):
        return jsonify({"success": False, "message": "Acesso negado: Colaboradores não podem criar rotinas."}), 403
    try:
        data = request.get_json(silent=True) or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"success": False, "message": "Nome é obrigatório"}), 400

        process_id = _coerce_optional_int(data.get("process_id"), default=None)
        schedule_type = _coerce_optional_text(data.get("schedule_type")) or "weekly"
        schedule_value = _coerce_optional_text(data.get("schedule_value"))
        start_time = _coerce_optional_text(data.get("start_time")) or "00:01"
        deadline_days = _coerce_optional_int(data.get("deadline_days"), default=0)
        deadline_hours = _coerce_optional_int(data.get("deadline_hours"), default=0)
        deadline_date = _coerce_optional_text(data.get("deadline_date"))
        score_weight = _coerce_optional_float(data.get("score_weight"), default=1.0)
        
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO routines (
                company_id, name, description, process_id,
                schedule_type, schedule_value, start_time, deadline_days, deadline_hours, deadline_date,
                score_weight, is_active, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        """,
            (
                company_id,
                name,
                data.get("description", ""),
                process_id,
                schedule_type,
                schedule_value,
                start_time,
                deadline_days,
                deadline_hours,
                deadline_date,
                score_weight
            ),
        )

        routine_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return jsonify({
            "success": True, 
            "routine_id": routine_id,
            "message": "Rotina cadastrada com sucesso"
        }), 201

    except Exception as e:
        return jsonify({"success": False, "message": PUBLIC_ERROR_MESSAGE}), 500

@processes_bp.route('/api/companies/<int:company_id>/process-routines/<int:routine_id>', methods=['PUT'])
@permission_required('processes', 'edit')
def api_update_process_routine(company_id, routine_id):
    """Update an existing process routine"""
    if not has_company_full_access(company_id):
        return jsonify({"success": False, "message": "Acesso negado: Colaboradores não podem editar rotinas."}), 403
    try:
        data = request.get_json(silent=True) or {}
        process_id = _coerce_optional_int(data.get("process_id"), default=None)
        schedule_type = _coerce_optional_text(data.get("schedule_type"))
        schedule_value = _coerce_optional_text(data.get("schedule_value"))
        start_time = _coerce_optional_text(data.get("start_time")) or "00:01"
        deadline_days = _coerce_optional_int(data.get("deadline_days"), default=0)
        deadline_hours = _coerce_optional_int(data.get("deadline_hours"), default=0)
        score_weight = _coerce_optional_float(data.get("score_weight"), default=1.0)
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE routines SET
                name = %s,
                description = %s,
                process_id = %s,
                schedule_type = %s,
                schedule_value = %s,
                start_time = %s,
                deadline_days = %s,
                deadline_hours = %s,
                score_weight = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND company_id = %s
        """,
            (
                data.get("name"),
                data.get("description", ""),
                process_id,
                schedule_type,
                schedule_value,
                start_time,
                deadline_days,
                deadline_hours,
                score_weight,
                routine_id,
                company_id,
            ),
        )

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Rotina atualizada com sucesso"})

    except Exception as e:
        return jsonify({"success": False, "message": PUBLIC_ERROR_MESSAGE}), 500

@processes_bp.route('/api/companies/<int:company_id>/process-routines/<int:routine_id>', methods=['DELETE'])
@permission_required('processes', 'delete')
def api_delete_process_routine(company_id, routine_id):
    """Soft delete a process routine"""
    if not has_company_full_access(company_id):
        return jsonify({"success": False, "message": "Acesso negado: Colaboradores não podem excluir rotinas."}), 403
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE routines SET is_active = FALSE WHERE id = %s AND company_id = %s",
            (routine_id, company_id),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Rotina excluída com sucesso"})

    except Exception as e:
        return jsonify({"success": False, "message": PUBLIC_ERROR_MESSAGE}), 500

@processes_bp.route('/api/routines/<int:routine_id>/collaborators', methods=['GET'])
@permission_required('processes', 'view')
def api_get_routine_collaborators(routine_id):
    """Get all collaborators for a routine"""
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        routine = _fetch_routine_scope(cursor, routine_id)
        if not routine:
            conn.close()
            return jsonify({"success": False, "message": "Rotina não encontrada."}), 404
        if not has_permission(routine["company_id"], 'processes', 'view'):
            conn.close()
            return jsonify({"success": False, "message": "Acesso negado."}), 403
        session['active_company_id'] = routine["company_id"]

        cursor.execute(
            """
            SELECT rc.*, e.name as employee_name, e.email as employee_email
            FROM routine_collaborators rc
            JOIN employees e ON rc.employee_id = e.id
            JOIN routines r ON r.id = rc.routine_id
            WHERE rc.routine_id = %s
              AND r.company_id = %s
              AND e.company_id = r.company_id
            ORDER BY e.name
        """,
            (routine_id, routine["company_id"]),
        )

        collaborators = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "collaborators": collaborators})

    except HTTPException:
        raise
    except Exception as e:
        return jsonify({"success": False, "message": PUBLIC_ERROR_MESSAGE}), 500

@processes_bp.route('/api/routines/<int:routine_id>/collaborators', methods=['POST'])
@permission_required('processes', 'edit')
def api_add_routine_collaborator(routine_id):
    """Add a collaborator to a routine"""
    try:
        data = request.get_json(silent=True) or {}
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        routine = _fetch_routine_scope(cursor, routine_id)
        if not routine:
            conn.close()
            return jsonify({"success": False, "message": "Rotina não encontrada."}), 404
        if not has_permission(routine["company_id"], 'processes', 'edit'):
            conn.close()
            return jsonify({"success": False, "message": "Acesso negado."}), 403

        payload, error = _validate_routine_collaborator_payload(data)
        if error:
            conn.close()
            return jsonify({"success": False, "message": error}), 400

        cursor.execute(
            """
            SELECT 1
            FROM employees
            WHERE id = %s
              AND company_id = %s
              AND status = 'active'
            """,
            (payload["employee_id"], routine["company_id"]),
        )
        if not cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Colaborador inválido para esta empresa."}), 400

        cursor.execute(
            """
            SELECT 1
            FROM routine_collaborators
            WHERE routine_id = %s
              AND employee_id = %s
            """,
            (routine_id, payload["employee_id"]),
        )
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Este colaborador já está vinculado à rotina."}), 409

        session['active_company_id'] = routine["company_id"]

        cursor.execute(
            """
            INSERT INTO routine_collaborators (routine_id, employee_id, hours_used, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """,
            (
                routine_id,
                payload["employee_id"],
                payload["hours_used"],
                payload["notes"],
            ),
        )

        collaborator_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": collaborator_id, "message": "Colaborador adicionado com sucesso"}), 201

    except HTTPException:
        raise
    except Exception as e:
        return jsonify({"success": False, "message": PUBLIC_ERROR_MESSAGE}), 500

@processes_bp.route('/api/routines/<int:routine_id>/collaborators/<int:collaborator_id>', methods=['PUT'])
@permission_required('processes', 'edit')
def api_update_routine_collaborator(routine_id, collaborator_id):
    """Update a routine collaborator"""
    try:
        data = request.get_json(silent=True) or {}
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        routine = _fetch_routine_scope(cursor, routine_id)
        if not routine:
            conn.close()
            return jsonify({"success": False, "message": "Rotina não encontrada."}), 404
        if not has_permission(routine["company_id"], 'processes', 'edit'):
            conn.close()
            return jsonify({"success": False, "message": "Acesso negado."}), 403

        payload, error = _validate_routine_collaborator_payload(data)
        if error:
            conn.close()
            return jsonify({"success": False, "message": error}), 400

        cursor.execute(
            """
            SELECT 1
            FROM employees
            WHERE id = %s
              AND company_id = %s
              AND status = 'active'
            """,
            (payload["employee_id"], routine["company_id"]),
        )
        if not cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Colaborador inválido para esta empresa."}), 400

        cursor.execute(
            """
            SELECT 1
            FROM routine_collaborators rc
            JOIN routines r ON r.id = rc.routine_id
            WHERE rc.id = %s
              AND rc.routine_id = %s
              AND r.company_id = %s
            """,
            (collaborator_id, routine_id, routine["company_id"]),
        )
        if not cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Executor não encontrado."}), 404

        cursor.execute(
            """
            SELECT 1
            FROM routine_collaborators
            WHERE routine_id = %s
              AND employee_id = %s
              AND id <> %s
            """,
            (routine_id, payload["employee_id"], collaborator_id),
        )
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Este colaborador já está vinculado à rotina."}), 409

        session['active_company_id'] = routine["company_id"]

        cursor.execute(
            """
            UPDATE routine_collaborators
            SET employee_id = %s,
                hours_used = %s,
                notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND routine_id = %s
        """,
            (
                payload["employee_id"],
                payload["hours_used"],
                payload["notes"],
                collaborator_id,
                routine_id,
            ),
        )

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Colaborador atualizado com sucesso"})

    except HTTPException:
        raise
    except Exception as e:
        return jsonify({"success": False, "message": PUBLIC_ERROR_MESSAGE}), 500

@processes_bp.route('/api/routines/<int:routine_id>/collaborators/<int:collaborator_id>', methods=['DELETE'])
@permission_required('processes', 'edit')
def api_delete_routine_collaborator(routine_id, collaborator_id):
    """Delete a routine collaborator"""
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        routine = _fetch_routine_scope(cursor, routine_id)
        if not routine:
            conn.close()
            return jsonify({"success": False, "message": "Rotina não encontrada."}), 404
        if not has_permission(routine["company_id"], 'processes', 'edit'):
            conn.close()
            return jsonify({"success": False, "message": "Acesso negado."}), 403
        session['active_company_id'] = routine["company_id"]

        cursor.execute(
            """
            DELETE FROM routine_collaborators rc
            USING routines r
            WHERE rc.id = %s
              AND rc.routine_id = %s
              AND r.id = rc.routine_id
              AND r.company_id = %s
            """,
            (collaborator_id, routine_id, routine["company_id"]),
        )
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"success": False, "message": "Executor não encontrado."}), 404

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Colaborador removido com sucesso"})

    except HTTPException:
        raise
    except Exception as e:
        return jsonify({"success": False, "message": PUBLIC_ERROR_MESSAGE}), 500


@processes_bp.route('/api/routines/<int:routine_id>/journey-bindings', methods=['GET'])
@permission_required('processes', 'view')
def api_get_routine_journey_bindings(routine_id):
    try:
        from services.routine_journey_binding_service import list_routine_bindings_context

        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()
        routine = _fetch_routine_scope(cursor, routine_id)
        conn.close()
        if not routine:
            return jsonify({"success": False, "message": "Rotina não encontrada."}), 404
        if not has_permission(routine["company_id"], 'processes', 'view'):
            return jsonify({"success": False, "message": "Acesso negado."}), 403
        session['active_company_id'] = routine["company_id"]
        payload = list_routine_bindings_context(routine["company_id"], routine_id)
        return jsonify({"success": True, "data": payload})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception:
        return jsonify({"success": False, "message": PUBLIC_ERROR_MESSAGE}), 500


@processes_bp.route('/api/routines/<int:routine_id>/journey-bindings', methods=['POST'])
@permission_required('processes', 'edit')
def api_save_routine_journey_binding(routine_id):
    try:
        from services.routine_journey_binding_service import save_routine_binding

        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()
        routine = _fetch_routine_scope(cursor, routine_id)
        conn.close()
        if not routine:
            return jsonify({"success": False, "message": "Rotina não encontrada."}), 404
        if not has_permission(routine["company_id"], 'processes', 'edit'):
            return jsonify({"success": False, "message": "Acesso negado."}), 403
        session['active_company_id'] = routine["company_id"]

        payload = RoutineJourneyBindingUpsertSchema.model_validate(request.get_json(silent=True) or {}).model_dump()
        binding = save_routine_binding(
            routine["company_id"],
            routine_id,
            payload["employee_id"],
            payload.get("block_id"),
            payload.get("notes"),
        )
        return jsonify({"success": True, "binding": binding})
    except ValidationError as exc:
        return jsonify({"success": False, "message": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception:
        return jsonify({"success": False, "message": PUBLIC_ERROR_MESSAGE}), 500



@processes_bp.route('/api/companies/<int:company_id>/employees')
@permission_required('companies', 'view')
def api_get_company_employees(company_id):
    """Get all employees for a company"""
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, email FROM employees WHERE company_id = %s AND status = 'active' ORDER BY name",
            (company_id,),
        )

        employees = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "employees": employees})

    except Exception as e:
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500

@processes_bp.route('/companies/<int:company_id>/routines/<routine_id>')
@permission_required('processes', 'view')
def routine_details_page(company_id, routine_id):
    """Routine details/creation page"""
    from flask import abort
    company = Company.query.get_or_404(company_id)
    
    pg = get_db()
    conn = pg._get_connection()
    cursor = conn.cursor()

    # Buscar todos os processos para o select
    cursor.execute(
        "SELECT id, code, name FROM processes WHERE company_id = %s AND (is_active = True OR is_active IS NULL) ORDER BY code",
        (company_id,),
    )
    processes = [dict(row) for row in cursor.fetchall()]

    is_new = routine_id == "new"
    if is_new:
        routine = {
            "id": None, "name": "", "description": "", "process_id": None,
            "schedule_type": "weekly", "schedule_value": "", "start_time": "00:01",
            "deadline_days": 0, "deadline_hours": 0, "score_weight": 1.0
        }
    else:
        cursor.execute(
            """
            SELECT r.*, p.code as process_code, p.name as process_name
            FROM routines r
            LEFT JOIN processes p ON r.process_id = p.id
            WHERE r.id = %s AND r.company_id = %s
        """,
            (int(routine_id), company_id),
        )
        row = cursor.fetchone()
        if row:
            routine = dict(row)
        else:
            conn.close()
            abort(404)

    conn.close()

    return render_template(
        "routine_details.html",
        company=company,
        routine=routine,
        processes=processes,
        is_new=is_new
    )
