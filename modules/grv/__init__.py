from flask import Blueprint, render_template, abort, url_for, make_response, request, jsonify, redirect, current_app
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import subprocess
import sys
import threading
from typing import Any, Optional
from config_database import get_db
from middleware.auto_log_decorator import auto_log_crud

grv_bp = Blueprint('grv', __name__, url_prefix='/grv')

print(">>> MÓDULO GRV CARREGADO - VERSÃO COM API ROUTES <<<")

_playwright_install_lock = threading.Lock()
_playwright_chromium_ready = False


def _ensure_playwright_browser_installed(browser_name: str = 'chromium') -> None:
    """
    Garantir que o navegador necessário do Playwright esteja disponível.

    Executa `python -m playwright install <browser>` uma única vez por processo.
    Levanta RuntimeError se a instalação falhar.
    """
    global _playwright_chromium_ready
    if _playwright_chromium_ready:
        return

    with _playwright_install_lock:
        if _playwright_chromium_ready:
            return

        install_cmd = [sys.executable, '-m', 'playwright', 'install', browser_name]
        try:
            completed = subprocess.run(
                install_cmd,
                check=True,
                capture_output=True,
                text=True
            )
            stdout = completed.stdout.strip()
            if stdout:
                print(f"Playwright install output: {stdout}")
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or '').strip()
            stdout = (exc.stdout or '').strip()
            error_message = stderr or stdout or str(exc)
            raise RuntimeError(
                f"Falha ao instalar navegador Playwright '{browser_name}': {error_message}"
            ) from exc

        _playwright_chromium_ready = True


def _should_attempt_playwright_install(error: Exception) -> bool:
    """Detecta mensagens típicas de ausência do executável Playwright."""
    message = str(error) if error else ''
    triggers = (
        "Executable doesn't exist",
        "Please run the following command to download new browsers",
        'browserType.launch'
    )
    return any(trigger in message for trigger in triggers)

def normalize_indicator_code(code: Optional[str]) -> Optional[str]:
    if not code:
        return code
    return code.replace('.IND.', '.')


ALLOWED_GOAL_TYPES = {'single', 'daily', 'weekly', 'monthly', 'quarterly', 'biannual', 'annual'}
ALLOWED_GOAL_EVALUATIONS = {'value', 'sum', 'average', 'latest'}


def ensure_indicator_schema(conn):
    """Ensure indicator table has the latest helper columns."""
    cursor = conn.cursor()
    # PostgreSQL: usar information_schema para listar colunas
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'indicators' 
        AND table_schema = 'public'
    """)
    columns = {row[0] for row in cursor.fetchall()}

    added_reference = False
    if 'okr_reference' not in columns:
        cursor.execute("ALTER TABLE indicators ADD COLUMN okr_reference TEXT")
        added_reference = True
    if 'okr_reference_label' not in columns:
        cursor.execute("ALTER TABLE indicators ADD COLUMN okr_reference_label TEXT")
    if 'plan_id' not in columns:
        cursor.execute("ALTER TABLE indicators ADD COLUMN plan_id TEXT")
    if 'okr_id' not in columns:
        cursor.execute("ALTER TABLE indicators ADD COLUMN okr_id INTEGER")
    if 'okr_level' not in columns:
        cursor.execute("ALTER TABLE indicators ADD COLUMN okr_level TEXT")
    conn.commit()

    if added_reference:
        cursor.execute("""
            UPDATE indicators
            SET okr_reference = NULL
            WHERE okr_reference IS NULL
        """)
        conn.commit()


def ensure_indicator_goals_schema(conn):
    """Guarantee new goal tracking columns exist and populate defaults."""
    cursor = conn.cursor()
    # PostgreSQL: usar information_schema para listar colunas
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'indicator_goals' 
        AND table_schema = 'public'
    """)
    columns = {row[0] for row in cursor.fetchall()}

    added_goal_type = False
    added_evaluation = False
    if 'goal_type' not in columns:
        cursor.execute("ALTER TABLE indicator_goals ADD COLUMN goal_type TEXT DEFAULT 'single'")
        added_goal_type = True
    if 'period_start' not in columns:
        cursor.execute("ALTER TABLE indicator_goals ADD COLUMN period_start DATE")
    if 'period_end' not in columns:
        cursor.execute("ALTER TABLE indicator_goals ADD COLUMN period_end DATE")
    if 'evaluation_basis' not in columns:
        cursor.execute("ALTER TABLE indicator_goals ADD COLUMN evaluation_basis TEXT DEFAULT 'value'")
        added_evaluation = True
    if 'okr_reference' not in columns:
        cursor.execute("ALTER TABLE indicator_goals ADD COLUMN okr_reference TEXT")
    if 'okr_reference_label' not in columns:
        cursor.execute("ALTER TABLE indicator_goals ADD COLUMN okr_reference_label TEXT")

    conn.commit()

    if added_goal_type:
        cursor.execute("""
            UPDATE indicator_goals
            SET goal_type = 'single'
            WHERE goal_type IS NULL OR TRIM(goal_type) = ''
        """)
    if added_evaluation:
        cursor.execute("""
            UPDATE indicator_goals
            SET evaluation_basis = 'value'
            WHERE evaluation_basis IS NULL OR TRIM(evaluation_basis) = ''
        """)
    conn.commit()


def normalize_goal_row(goal: dict) -> dict:
    """Apply defaults and formatting helpers for goal payloads."""
    goal_type = goal.get('goal_type') or 'single'
    if goal_type not in ALLOWED_GOAL_TYPES:
        goal_type = 'single'
    goal['goal_type'] = goal_type

    for key in ('period_start', 'period_end'):
        if not goal.get(key):
            goal[key] = None

    evaluation = goal.get('evaluation_basis') or ('value' if goal_type == 'single' else 'sum')
    if evaluation not in ALLOWED_GOAL_EVALUATIONS:
        evaluation = 'value' if goal_type == 'single' else 'sum'
    goal['evaluation_basis'] = evaluation

    value = goal.get('goal_value')
    if value is not None:
        try:
            goal['goal_value'] = float(value)
        except (TypeError, ValueError):
            pass

    okr_reference = goal.get('okr_reference')
    goal['okr_reference'] = okr_reference if okr_reference else None
    okr_label = goal.get('okr_reference_label')
    goal['okr_reference_label'] = okr_label.strip() if isinstance(okr_label, str) and okr_label.strip() else None

    return goal

KANBAN_STAGE_DEFINITIONS = [
    {'slug': 'inbox', 'title': 'Caixa de Entrada', 'description': 'Processos recÃ©m cadastrados aguardando priorizaÃ§Ã£o.'},
    {'slug': 'out_of_scope', 'title': 'Fora de Escopo', 'description': 'Itens registrados que nÃ£o serÃ£o modelados neste ciclo.'},
    {'slug': 'designing', 'title': 'Modelando', 'description': 'Processos em anÃ¡lise e desenho do fluxo.'},
    {'slug': 'deploying', 'title': 'Implantando', 'description': 'Processos em implementaÃ§Ã£o junto Ã s equipes.'},
    {'slug': 'stabilizing', 'title': 'Estabilizando', 'description': 'Processos acompanhados atÃ© atingirem estabilidade.'},
    {'slug': 'stable', 'title': 'EstÃ¡vel', 'description': 'Processos consolidados e operando conforme desenho.'}
]

PROCESS_DETAIL_TABS = [
    {'slug': 'flow', 'label': 'Fluxo', 'description': 'Mapeamento do processo, etapas e respons-veis.'},
    {'slug': 'pop', 'label': 'POP', 'description': 'Procedimentos operacionais padr-o atualizados.'},
    {'slug': 'indicators', 'label': 'Indicadores', 'description': 'M-tricas, metas e respons-veis pelo monitoramento.'},
    {'slug': 'routine', 'label': 'Rotina', 'description': 'Reuni-es, cad-ncia de acompanhamento e entreg-veis.'},
    {'slug': 'notes', 'label': 'Obs/Outros', 'description': 'Observa--es gerais, riscos e anexos relevantes.'}
]


def grv_navigation():
    return [
        {
            'title': 'Dashboard',
            'items': [
                {'id': 'dashboard', 'name': 'Visão Geral'}
            ]
        },
        {
            'title': 'Identidade Organizacional',
            'items': [
                {'id': 'identity-mvv', 'name': 'Missão / Visão / Valores'},
                {'id': 'identity-roles', 'name': 'Cadastro de Funções'},
                {'id': 'identity-chart', 'name': 'Organograma'}
            ]
        },
        {
            'title': 'Gestão de Processos',
            'items': [
                {'id': 'process-map', 'name': 'Arquitetura'},
                {'id': 'process-modeling', 'name': 'Modelagem / Desenho'},
                {'id': 'process-instances', 'name': 'Instâncias de Processos'},
                {'id': 'process-analysis', 'name': 'Análises'},
                {'id': 'process-routines', 'name': 'Rotina dos Processos'}
            ]
        },
        {
            'title': 'Gestão de Projetos',
            'items': [
                {'id': 'project-portfolios', 'name': 'Portfólios'},
                {'id': 'project-projects', 'name': 'Projetos'},
                {'id': 'project-analysis', 'name': 'Análises'}
            ]
        },
        {
            'title': 'Gestão de Reuniões',
            'items': [
                {'id': 'meetings-manage', 'name': 'Gerir Reuniões'}
            ]
        },
        {
            'title': 'Gestão de Indicadores',
            'items': [
                {'id': 'indicators-tree', 'name': 'Árvore de Indicadores'},
                {'id': 'indicators-list', 'name': 'Indicadores'},
                {'id': 'indicators-goals', 'name': 'Metas'},
                {'id': 'indicators-data', 'name': 'Registros de Dados'},
                {'id': 'indicators-analysis', 'name': 'Análises'}
            ]
        },
        {
            'title': 'Gestão da Rotina',
            'items': [
                {'id': 'routine-work-distribution', 'name': 'Mapa de Distribuição do Trabalho'},
                {'id': 'routine-capacity', 'name': 'Gestão da Capacidade Operacional'},
                {'id': 'routine-activities', 'name': 'Gestão de Atividades / Calendário'},
                {'id': 'routine-incidents', 'name': 'Gestão de Ocorrências'},
                {'id': 'routine-efficiency', 'name': 'Gestão da Eficiência'}
            ]
        }
    ]


@grv_bp.route('/dashboard')
def grv_dashboard():
    # Dedicated GRV dashboard (was redirecting to core routine selector)
    db = get_db()
    companies = db.get_companies()

    companies_context = []
    total_processes = 0
    total_projects = 0
    
    for company in companies:
        plans = db.get_plans_by_company(company['id'])
        
        # Contar processos, areas e projetos
        process_count = 0
        areas_count = 0
        projects_count = 0
        
        try:
            from database.postgres_helper import connect as pg_connect
            conn = pg_connect()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM processes WHERE company_id = %s", (company['id'],))
            result = cursor.fetchone()
            if result:
                process_count = result[0]
            
            cursor.execute("SELECT COUNT(*) FROM process_areas WHERE company_id = %s", (company['id'],))
            result = cursor.fetchone()
            if result:
                areas_count = result[0]
            
            cursor.execute("SELECT COUNT(*) FROM company_projects WHERE company_id = %s", (company['id'],))
            result = cursor.fetchone()
            if result:
                projects_count = result[0]
            
            conn.close()
        except Exception as e:
            print(f"Erro ao contar processos/areas/projetos: {e}")
            process_count = 0
            areas_count = 0
            projects_count = 0
        
        total_processes += process_count
        total_projects += projects_count
        
        companies_context.append({
            'id': company['id'],
            'name': company.get('name') or company.get('legal_name') or 'Empresa',
            'client_code': (company.get('client_code') or '').strip() if isinstance(company.get('client_code'), str) else company.get('client_code'),
            'industry': company.get('industry') or '',
            'plans': [{'id': plan['id'], 'name': plan['name']} for plan in plans],
            'process_count': process_count,
            'areas_count': areas_count,
            'projects_count': projects_count
        })

    highlights = {
        'companies': len(companies_context),
        'total_projects': total_projects,
        'last_update': datetime.now().strftime('%d/%m/%Y')
    }

    return render_template(
        "grv_dashboard.html",
        companies=companies_context,
        highlights=highlights,
        total_processes=total_processes
    )

@grv_bp.route('/company/<int:company_id>')
def grv_company_dashboard(company_id: int):
    db = get_db()
    company = db.get_company(company_id)
    if not company:
        abort(404)

    plans = db.get_plans_by_company(company_id)
    # Determine which plan's MVV is in use for GRV
    default_plan_id = None
    enriched_plans = []
    for p in plans:
        pdata = dict(p)
        company_data_row = db.get_company_data(int(p['id'])) or {}
        in_use = bool(company_data_row.get('grv_mvv_in_use'))
        pdata['grv_mvv_in_use'] = in_use
        if in_use and default_plan_id is None:
            default_plan_id = p['id']
        enriched_plans.append(pdata)
    if default_plan_id is None and plans:
        default_plan_id = plans[0]['id']
    summary_cards = [
        {
            'label': 'Projetos ativos',
            'value': len(plans),
            'description': 'Projetos registrados para a empresa'
        },
        {
            'label': 'Capacidade estimada',
            'value': '72% ocupação',
            'description': 'Espaço disponível para novas atividades'
        },
        {
            'label': 'Processos mapeados',
            'value': 12,
            'description': 'Fluxos documentados e validados'
        },
        {
            'label': 'Última atualização',
            'value': datetime.now().strftime('%d/%m/%Y'),
            'description': 'Data do último ajuste registrado'
        }
    ]

    navigation = grv_navigation()

    upcoming_activities = [
        {'title': 'Revisar POP de atendimento', 'responsible': 'Equipe Operacional', 'deadline': 'Próx. segunda'},
        {'title': 'Reunião de status dos projetos', 'responsible': 'PMO', 'deadline': 'Quarta-feira'},
        {'title': 'Atualizar carga horária do time', 'responsible': 'RH', 'deadline': 'Sexta-feira'}
    ]

    quick_links = [
        {'label': 'Cadastrar atividade', 'href': '#routine-overview'},
        {'label': 'Novo processo', 'href': '#process-list'},
        {'label': 'Estruturar processos', 'href': url_for('grv.grv_process_map', company_id=company_id)}
    ]

    return render_template(
        "routine_dashboard.html",
        company=company,
        plans=enriched_plans,
        default_plan_id=default_plan_id,
        navigation=navigation,
        summary_cards=summary_cards,
        upcoming_activities=upcoming_activities,
        quick_links=quick_links,
        active_id='dashboard'
    )


@grv_bp.route('/company/<int:company_id>/identity/mvv')
def grv_identity_mvv(company_id: int):
    """Redirect to centralized company management - MVV tab"""
    db = get_db()
    company = db.get_company(company_id) or {}
    return render_template('grv_identity_mvv_redirect.html', company=company, navigation=grv_navigation(), active_id='identity-mvv')


@grv_bp.route('/company/<int:company_id>/identity/roles')
def grv_identity_roles(company_id: int):
    """Redirect to centralized company management - Roles tab"""
    company = get_db().get_company(company_id) or {}
    return render_template('grv_identity_roles_redirect.html', company=company, navigation=grv_navigation(), active_id='identity-roles')


@grv_bp.route('/company/<int:company_id>/identity/org-chart')
def grv_identity_org_chart(company_id: int):
    company = get_db().get_company(company_id) or {}
    return render_template('grv_identity_org_chart.html', company=company, navigation=grv_navigation(), active_id='identity-chart')


@grv_bp.route('/company/<int:company_id>/process/map')
def grv_process_map(company_id: int):
    db = get_db()
    company = db.get_company(company_id) or {}
    areas = db.list_process_areas(company_id)
    macros = db.list_macro_processes(company_id)

    for macro in macros:
        area = next((a for a in areas if a['id'] == macro.get('area_id')), None)
        macro['area_name'] = area['name'] if area else 'Sem area'
        macro['area_color'] = area.get('color', '#a78bfa') if area else '#a78bfa'

    return render_template(
        'grv_process_map.html',
        company=company,
        navigation=grv_navigation(),
        active_id='process-map',
        areas=areas,
        macros=macros
    )


@grv_bp.route('/company/<int:company_id>/process/map/print')
def grv_process_map_print(company_id: int):
    """Print-friendly version of the process map"""
    db = get_db()
    company = db.get_company(company_id)
    if not company:
        abort(404)

    map_data = db.get_process_map(company_id) or {}
    raw_areas = map_data.get('areas', [])

    structuring_levels = {
        '': {'label': 'Fora de Escopo', 'color': '#94a3b8'},
        'in_progress': {'label': 'Map | Impl | Estabn', 'color': '#f59e0b'},
        'stabilized': {'label': 'Estabilizado', 'color': '#10b981'},
        'initiated': {'label': 'Map | Impl | Estabn', 'color': '#f59e0b'},
        'structured': {'label': 'Estabilizado', 'color': '#10b981'}
    }
    performance_levels = {
        '': {'label': 'Fora de Escopo', 'color': '#94a3b8'},
        'critical': {'label': 'Crítico', 'color': '#ef4444'},
        'below': {'label': 'Abaixo', 'color': '#f59e0b'},
        'satisfactory': {'label': 'Satisfatório', 'color': '#10b981'},
        'initiated': {'label': 'Abaixo', 'color': '#f59e0b'},
        'structured': {'label': 'Satisfatório', 'color': '#10b981'}
    }

    def _normalize_hex(value: str, default: str = '#1d4ed8') -> str:
        if not value:
            return default
        value = value.strip()
        if not value.startswith('#'):
            value = f'#{value}'
        if len(value) == 4:
            value = f"#{''.join(ch * 2 for ch in value[1:])}"
        return value.lower() if len(value) == 7 else default

    def _mix_with_white(color_hex: str, factor: float = 0.75) -> str:
        base = _normalize_hex(color_hex)
        r = int(base[1:3], 16)
        g = int(base[3:5], 16)
        b = int(base[5:7], 16)
        def _blend(channel: int) -> int:
            return max(0, min(255, int(channel + (255 - channel) * factor)))
        return '#{0:02x}{1:02x}{2:02x}'.format(_blend(r), _blend(g), _blend(b))

    def _accent_text_color(color_hex: str) -> str:
        color = _normalize_hex(color_hex)
        if color in {'#f59e0b', '#fbbf24'}:
            return '#b45309'
        return color

    def _parse_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None
            if cleaned.endswith('Z'):
                cleaned = cleaned[:-1] + '+00:00'
            try:
                return datetime.fromisoformat(cleaned)
            except ValueError:
                pass
            for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    return datetime.strptime(cleaned, fmt)
                except ValueError:
                    continue
        return None

    def _format_datetime(value: Optional[datetime], with_time: bool = True) -> Optional[str]:
        if not value:
            return None
        fmt = '%d/%m/%Y %H:%M' if with_time else '%d/%m/%Y'
        return value.strftime(fmt)

    def _clean_text(value: Any, fallback: str = '') -> str:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
        return fallback

    def _format_display_name(code: Any, name: Any, fallback: str) -> str:
        safe_name = _clean_text(name, fallback)
        safe_code = _clean_text(code)
        name_part = safe_name.upper() if safe_name else fallback.upper()
        if safe_code:
            return f"{safe_code.upper()} - {name_part}"
        return name_part

    areas = []
    total_macros = 0
    total_processes = 0

    for area in raw_areas:
        macros = area.get('macros') or []
        area_color = _normalize_hex(area.get('color'))
        area_entry = {
            'display_name': _format_display_name(area.get('code'), area.get('name'), 'Área'),
            'color': area_color,
            'color_soft': _mix_with_white(area_color, 0.82),
            'color_accent': _mix_with_white(area_color, 0.68),
            'macros': [],
            'macro_count': len(macros),
            'process_count': 0
        }

        for macro in macros:
            processes = macro.get('processes') or []
            macro_entry = {
                'display_name': _format_display_name(macro.get('code'), macro.get('name'), 'Macroprocesso'),
                'owner': macro.get('owner'),
                'processes': []
            }

            for proc in processes:
                struct_info = structuring_levels.get(proc.get('structuring_level') or '', structuring_levels[''])
                perf_info = performance_levels.get(proc.get('performance_level') or '', performance_levels[''])
                struct_color = _normalize_hex(struct_info['color'])
                perf_color = _normalize_hex(perf_info['color'])
                macro_entry['processes'].append({
                    'display_name': _format_display_name(proc.get('code'), proc.get('name'), 'Processo'),
                    'responsible': proc.get('responsible'),
                    'description': proc.get('description'),
                    'structuring': {
                        'label': struct_info['label'],
                        'color': struct_color,
                        'text_color': _accent_text_color(struct_color),
                        'background': _mix_with_white(struct_color, 0.88)
                    },
                    'performance': {
                        'label': perf_info['label'],
                        'color': perf_color,
                        'text_color': _accent_text_color(perf_color),
                        'background': _mix_with_white(perf_color, 0.88)
                    }
                })

            macro_entry['process_total'] = len(macro_entry['processes'])
            area_entry['process_count'] += macro_entry['process_total']
            area_entry['macros'].append(macro_entry)

        total_macros += area_entry['macro_count']
        total_processes += area_entry['process_count']
        areas.append(area_entry)

    generated_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
    app_version = current_app.config.get('APP_VERSION') if current_app else None
    company_created_at = _parse_datetime(company.get('created_at'))
    header_meta = {
        'company_name': company.get('name'),
        'version': map_data.get('version') or '1.0',
        'created_at': _format_datetime(company_created_at, with_time=False),
        'updated_at': _format_datetime(generated_at, with_time=False),
        'printed_at': _format_datetime(generated_at, with_time=True)
    }

    return render_template(
        'pdf/grv_process_map_print.html',
        company=company,
        areas=areas,
        totals={
            'areas': len(areas),
            'macros': total_macros,
            'processes': total_processes
        },
        generated_at=generated_at,
        header_meta=header_meta
    )


@grv_bp.route('/company/<int:company_id>/process/map/pdf/debug')
def grv_process_map_pdf_debug(company_id: int):
    """Debug: View HTML before PDF conversion"""
    db = get_db()
    company = db.get_company(company_id)
    if not company:
        abort(404)

    map_data = db.get_process_map(company_id) or {}
    raw_areas = map_data.get('areas', [])

    structuring_levels = {
        '': {'label': 'Fora de Escopo', 'color': '#94a3b8'},
        'in_progress': {'label': 'Map | Impl | Estabn', 'color': '#f59e0b'},
        'stabilized': {'label': 'Estabilizado', 'color': '#10b981'},
        'initiated': {'label': 'Map | Impl | Estabn', 'color': '#f59e0b'},
        'structured': {'label': 'Estabilizado', 'color': '#10b981'}
    }
    performance_levels = {
        '': {'label': 'Fora de Escopo', 'color': '#94a3b8'},
        'critical': {'label': 'Crítico', 'color': '#ef4444'},
        'below': {'label': 'Abaixo', 'color': '#f59e0b'},
        'satisfactory': {'label': 'Satisfatório', 'color': '#10b981'},
        'initiated': {'label': 'Abaixo', 'color': '#f59e0b'},
        'structured': {'label': 'Satisfatório', 'color': '#10b981'}
    }

    def _normalize_hex(value: str, default: str = '#1d4ed8') -> str:
        if not value:
            return default
        value = value.strip()
        if not value.startswith('#'):
            value = f'#{value}'
        if len(value) == 4:
            value = f"#{''.join(ch * 2 for ch in value[1:])}"
        return value.lower() if len(value) == 7 else default

    def _mix_with_white(color_hex: str, factor: float = 0.75) -> str:
        base = _normalize_hex(color_hex)
        r = int(base[1:3], 16)
        g = int(base[3:5], 16)
        b = int(base[5:7], 16)
        def _blend(channel: int) -> int:
            return max(0, min(255, int(channel + (255 - channel) * factor)))
        return '#{0:02x}{1:02x}{2:02x}'.format(_blend(r), _blend(g), _blend(b))

    areas = []
    total_macros = 0
    total_processes = 0

    for area in raw_areas:
        macros = area.get('macros') or []
        area_color = _normalize_hex(area.get('color'))
        area_entry = {
            'display_name': f"{area.get('code')} - {area.get('name').upper()}" if area.get('code') else (area.get('name') or 'Área'),
            'color': area_color,
            'color_soft': _mix_with_white(area_color, 0.82),
            'macros': [],
            'macro_count': len(macros),
            'process_count': 0
        }

        for macro in macros:
            processes = macro.get('processes') or []
            macro_entry = {
                'display_name': _format_display_name(macro.get('code'), macro.get('name'), 'Macroprocesso'),
                'owner': macro.get('owner'),
                'processes': []
            }

            for proc in processes:
                struct_info = structuring_levels.get(proc.get('structuring_level') or '', structuring_levels[''])
                perf_info = performance_levels.get(proc.get('performance_level') or '', performance_levels[''])
                macro_entry['processes'].append({
                    'display_name': _format_display_name(proc.get('code'), proc.get('name'), 'Processo'),
                    'code': _clean_text(proc.get('code')),
                    'raw_name': _clean_text(proc.get('name'), 'Processo'),
                    'responsible': proc.get('responsible'),
                    'description': proc.get('description'),
                    'structuring': {
                        'label': struct_info['label'],
                        'color': struct_info['color'],
                        'background': _mix_with_white(struct_info['color'], 0.88)
                    },
                    'performance': {
                        'label': perf_info['label'],
                        'color': perf_info['color'],
                        'background': _mix_with_white(perf_info['color'], 0.88)
                    }
                })

            macro_entry['process_total'] = len(macro_entry['processes'])
            area_entry['process_count'] += macro_entry['process_total']
            area_entry['macros'].append(macro_entry)

        total_macros += area_entry['macro_count']
        total_processes += area_entry['process_count']
        areas.append(area_entry)

    generated_at = datetime.now()

    return render_template(
        'pdf/grv_process_map_embed.html',
        company=company,
        areas=areas,
        totals={
            'areas': len(areas),
            'macros': total_macros,
            'processes': total_processes
        },
        generated_at=generated_at,
        report_version=app_version
    )


@grv_bp.route('/company/<int:company_id>/process/map/pdf')
def grv_process_map_pdf(company_id: int):
    db = get_db()
    company = db.get_company(company_id)
    if not company:
        abort(404)

    map_data = db.get_process_map(company_id) or {}
    raw_areas = map_data.get('areas', [])

    structuring_levels = {
        '': {'label': 'Fora de Escopo', 'color': '#94a3b8'},
        'in_progress': {'label': 'Map | Impl | Estabn', 'color': '#f59e0b'},
        'stabilized': {'label': 'Estabilizado', 'color': '#10b981'},
        'initiated': {'label': 'Map | Impl | Estabn', 'color': '#f59e0b'},
        'structured': {'label': 'Estabilizado', 'color': '#10b981'}
    }
    performance_levels = {
        '': {'label': 'Fora de Escopo', 'color': '#94a3b8'},
        'critical': {'label': 'Crítico', 'color': '#ef4444'},
        'below': {'label': 'Abaixo', 'color': '#f59e0b'},
        'satisfactory': {'label': 'Satisfatório', 'color': '#10b981'},
        'initiated': {'label': 'Abaixo', 'color': '#f59e0b'},
        'structured': {'label': 'Satisfatório', 'color': '#10b981'}
    }

    def _normalize_hex(value: str, default: str = '#1d4ed8') -> str:
        if not value:
            return default
        value = value.strip()
        if not value.startswith('#'):
            value = f'#{value}'
        if len(value) == 4:
            value = f"#{''.join(ch * 2 for ch in value[1:])}"
        return value.lower() if len(value) == 7 else default

    def _mix_with_white(color_hex: str, factor: float = 0.75) -> str:
        base = _normalize_hex(color_hex)
        r = int(base[1:3], 16)
        g = int(base[3:5], 16)
        b = int(base[5:7], 16)
        def _blend(channel: int) -> int:
            return max(0, min(255, int(channel + (255 - channel) * factor)))
        return '#{0:02x}{1:02x}{2:02x}'.format(_blend(r), _blend(g), _blend(b))

    def _clean_text(value: Any, fallback: str = '') -> str:
        """Return stripped text or fallback."""
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
        return fallback

    def _format_display_name(code: Any, name: Any, fallback: str) -> str:
        """Format display name as 'CODE - NAME' guarding against missing values."""
        safe_name = _clean_text(name, fallback)
        safe_code = _clean_text(code)
        name_part = safe_name.upper() if safe_name else fallback.upper()
        if safe_code:
            return f"{safe_code.upper()} - {name_part}"
        return name_part

    areas = []
    total_macros = 0
    total_processes = 0

    for area in raw_areas:
        macros = area.get('macros') or []
        area_color = _normalize_hex(area.get('color'))
        area_entry = {
            'display_name': _format_display_name(area.get('code'), area.get('name'), 'Área'),
            'color': area_color,
            'color_soft': _mix_with_white(area_color, 0.82),
            'macros': [],
            'macro_count': len(macros),
            'process_count': 0
        }

        for macro in macros:
            processes = macro.get('processes') or []
            macro_entry = {
                'display_name': f"{macro.get('code')} - {macro.get('name').upper()}" if macro.get('code') else (macro.get('name') or 'Macroprocesso'),
                'owner': macro.get('owner'),
                'processes': []
            }

            for proc in processes:
                struct_info = structuring_levels.get(proc.get('structuring_level') or '', structuring_levels[''])
                perf_info = performance_levels.get(proc.get('performance_level') or '', performance_levels[''])
                macro_entry['processes'].append({
                    'display_name': f"{proc.get('code')} - {proc.get('name').upper()}" if proc.get('code') else (proc.get('name') or 'Processo'),
                    'responsible': proc.get('responsible'),
                    'description': proc.get('description'),
                    'structuring': {
                        'label': struct_info['label'],
                        'color': struct_info['color'],
                        'background': _mix_with_white(struct_info['color'], 0.88)
                    },
                    'performance': {
                        'label': perf_info['label'],
                        'color': perf_info['color'],
                        'background': _mix_with_white(perf_info['color'], 0.88)
                    }
                })

            macro_entry['process_total'] = len(macro_entry['processes'])
            area_entry['process_count'] += macro_entry['process_total']
            area_entry['macros'].append(macro_entry)

        total_macros += area_entry['macro_count']
        total_processes += area_entry['process_count']
        areas.append(area_entry)

    generated_at = datetime.now()

    html_content = render_template(
        'pdf/grv_process_map_embed.html',
        company=company,
        areas=areas,
        totals={
            'areas': len(areas),
            'macros': total_macros,
            'processes': total_processes
        },
        generated_at=generated_at
    )

    header_template = (
        "<style>"
        ".pdf-header{width:100%;height:8px;font-size:0;}"
        "</style>"
        "<div class='pdf-header'></div>"
    )

    footer_template = (
        "<style>"
        ".pdf-footer{width:100%;font-family:'Segoe UI','Inter',Arial,sans-serif;font-size:8.5pt;"
        "color:#475569;display:flex;justify-content:flex-end;align-items:center;"
        "padding:6px 12mm 0 12mm;border-top:1px solid rgba(15,23,42,0.12);background:#ffffff;}"
        "</style>"
        f"<div class='pdf-footer'>Gerado em {generated_at.strftime('%d/%m/%Y %H:%M')} â€¢ {company.get('name') or 'Empresa'}</div>"
    )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        abort(500, description="Dependência 'playwright' não encontrada. Execute: pip install playwright && playwright install chromium")

    def _build_pdf(html: str) -> bytes:
        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
                    try:
                        page = browser.new_page()
                        page.set_viewport_size({"width": 1240, "height": 1754})
                        page.set_content(html, wait_until="networkidle")
                        page.emulate_media(media="print")
                        pdf = page.pdf(
                            format="A4",
                            print_background=True,
                            display_header_footer=True,
                            header_template=header_template,
                            footer_template=footer_template,
                            prefer_css_page_size=True,
                            margin={"top": "15mm", "bottom": "20mm", "left": "12mm", "right": "12mm"}
                        )
                    finally:
                        browser.close()
                return pdf
            except Exception as exc:
                last_error = exc
                if attempt == 0 and _should_attempt_playwright_install(exc):
                    try:
                        _ensure_playwright_browser_installed('chromium')
                        continue
                    except Exception as install_error:
                        print(f"Erro ao instalar navegador Playwright: {install_error}")
                        last_error = install_error
                break

        if last_error:
            raise last_error
        raise RuntimeError("Falha desconhecida ao gerar PDF via Playwright")

    try:
        pdf_bytes = _build_pdf(html_content)
    except Exception as pdf_error:
        print(f"ERRO Playwright ao gerar PDF: {pdf_error}")
        abort(500, description=f"Erro ao gerar PDF: {pdf_error}")

    safe_name = re.sub(r'[^a-z0-9_-]+', '-', (company.get('name') or 'empresa').lower()).strip('-') or 'empresa'
    filename = f"mapa-processos-{safe_name}.pdf"

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@grv_bp.route('/company/<int:company_id>/process/map/pdf2/test')
def grv_process_map_pdf2_test(company_id: int):
    """Simple test endpoint"""
    from flask import jsonify
    return jsonify({"status": "OK", "message": "Test endpoint working", "company_id": company_id})


@grv_bp.route('/company/<int:company_id>/process/map/pdf2/debug')
def grv_process_map_pdf2_debug(company_id: int):
    """Debug: View HTML before PDF conversion"""
    from datetime import datetime
    from flask import render_template
    
    db = get_db()
    company = db.get_company(company_id)
    if not company:
        abort(404)
    
    map_data = db.get_process_map(company_id) or {}
    raw_areas = map_data.get('areas', [])
    
    structuring_levels = {
        '': {'label': 'Fora de Escopo', 'color': '#94a3b8'},
        'in_progress': {'label': 'Map | Impl | Estabn', 'color': '#f59e0b'},
        'stabilized': {'label': 'Estabilizado', 'color': '#10b981'},
        'initiated': {'label': 'Map | Impl | Estabn', 'color': '#f59e0b'},
        'structured': {'label': 'Estabilizado', 'color': '#10b981'}
    }
    performance_levels = {
        '': {'label': 'Fora de Escopo', 'color': '#94a3b8'},
        'critical': {'label': 'Crítico', 'color': '#ef4444'},
        'below': {'label': 'Abaixo do esperado', 'color': '#f97316'},
        'initiated': {'label': 'Ajustando', 'color': '#f59e0b'},
        'structured': {'label': 'Satisfatório', 'color': '#10b981'}
    }
    
    def _normalize_hex(color: str) -> str:
        if not color or not isinstance(color, str):
            return '#94a3b8'
        if color.startswith('#'):
            return color
        return f'#{color}'
    
    def _mix_with_white(color_hex: str, factor: float = 0.75) -> str:
        base = _normalize_hex(color_hex)
        r = int(base[1:3], 16)
        g = int(base[3:5], 16)
        b = int(base[5:7], 16)
        def _blend(channel: int) -> int:
            return max(0, min(255, int(channel + (255 - channel) * factor)))
        return '#{0:02x}{1:02x}{2:02x}'.format(_blend(r), _blend(g), _blend(b))
    
    areas = []
    total_macros = 0
    total_processes = 0
    
    for area in raw_areas:
        macros = area.get('macros') or []
        area_color = _normalize_hex(area.get('color'))
        area_entry = {
            'display_name': f"{area.get('code')} - {area.get('name').upper()}" if area.get('code') else (area.get('name') or 'Área'),
            'color': area_color,
            'color_soft': _mix_with_white(area_color, 0.82),
            'macros': [],
            'macro_count': len(macros),
            'process_count': 0
        }
        
        for macro in macros:
            processes = macro.get('processes') or []
            macro_entry = {
                'display_name': f"{macro.get('code')} - {macro.get('name').upper()}" if macro.get('code') else (macro.get('name') or 'Macroprocesso'),
                'owner': macro.get('owner'),
                'processes': []
            }
            
            for proc in processes:
                struct_info = structuring_levels.get(proc.get('structuring_level') or '', structuring_levels[''])
                perf_info = performance_levels.get(proc.get('performance_level') or '', performance_levels[''])
                macro_entry['processes'].append({
                    'display_name': f"{proc.get('code')} - {proc.get('name').upper()}" if proc.get('code') else (proc.get('name') or 'Processo'),
                    'responsible': proc.get('responsible'),
                    'description': proc.get('description'),
                    'structuring': {
                        'label': struct_info['label'],
                        'color': struct_info['color'],
                        'background': _mix_with_white(struct_info['color'], 0.88)
                    },
                    'performance': {
                        'label': perf_info['label'],
                        'color': perf_info['color'],
                        'background': _mix_with_white(perf_info['color'], 0.88)
                    }
                })
            
            macro_entry['process_total'] = len(macro_entry['processes'])
            area_entry['process_count'] += macro_entry['process_total']
            area_entry['macros'].append(macro_entry)
        
        total_macros += area_entry['macro_count']
        total_processes += area_entry['process_count']
        areas.append(area_entry)
    
    generated_at = datetime.now()
    
    return render_template(
        'pdf/grv_process_map_v2.html',
        company=company,
        areas=areas,
        totals={
            'areas': len(areas),
            'macros': total_macros,
            'processes': total_processes
        },
        generated_at=generated_at
    )


@grv_bp.route('/company/<int:company_id>/process/map/pdf2')
def grv_process_map_pdf2(company_id: int):
    """Generate Process Map PDF - Version 2 (Landscape, Table Format)"""
    print(f"DEBUG: Rota /pdf2 chamada para company_id={company_id}")
    db = get_db()
    company = db.get_company(company_id)
    if not company:
        print("DEBUG: Empresa não encontrada!")
        abort(404)
    print(f"DEBUG: Empresa encontrada: {company.get('name')}")

    map_data = db.get_process_map(company_id) or {}
    raw_areas = map_data.get('areas', [])

    structuring_levels = {
        '': {'label': 'Fora de Escopo', 'color': '#94a3b8'},
        'in_progress': {'label': 'Map | Impl | Estabn', 'color': '#f59e0b'},
        'stabilized': {'label': 'Estabilizado', 'color': '#10b981'},
        'initiated': {'label': 'Map | Impl | Estabn', 'color': '#f59e0b'},
        'structured': {'label': 'Estabilizado', 'color': '#10b981'}
    }
    performance_levels = {
        '': {'label': 'Fora de Escopo', 'color': '#94a3b8'},
        'critical': {'label': 'Crítico', 'color': '#ef4444'},
        'below': {'label': 'Abaixo', 'color': '#f59e0b'},
        'satisfactory': {'label': 'Satisfatório', 'color': '#10b981'},
        'initiated': {'label': 'Abaixo', 'color': '#f59e0b'},
        'structured': {'label': 'Satisfatório', 'color': '#10b981'}
    }

    def _normalize_hex(value: str, default: str = '#1d4ed8') -> str:
        if not value:
            return default
        value = value.strip()
        if not value.startswith('#'):
            value = f'#{value}'
        if len(value) == 4:
            value = f"#{''.join(ch * 2 for ch in value[1:])}"
        return value.lower() if len(value) == 7 else default

    def _mix_with_white(color_hex: str, factor: float = 0.75) -> str:
        base = _normalize_hex(color_hex)
        r = int(base[1:3], 16)
        g = int(base[3:5], 16)
        b = int(base[5:7], 16)
        def _blend(channel: int) -> int:
            return max(0, min(255, int(channel + (255 - channel) * factor)))
        return '#{0:02x}{1:02x}{2:02x}'.format(_blend(r), _blend(g), _blend(b))

    def _clean_text(value: Any, fallback: str = '') -> str:
        """Return stripped text or fallback."""
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
        return fallback

    def _format_display_name(code: Any, name: Any, fallback: str) -> str:
        """Format display name as 'CODE - NAME' guarding against missing values."""
        safe_name = _clean_text(name, fallback)
        safe_code = _clean_text(code)
        name_part = safe_name.upper() if safe_name else fallback.upper()
        if safe_code:
            return f"{safe_code.upper()} - {name_part}"
        return name_part

    areas = []
    total_macros = 0
    total_processes = 0

    for area in raw_areas:
        macros = area.get('macros') or []
        area_color = _normalize_hex(area.get('color'))
        area_entry = {
            'display_name': _format_display_name(area.get('code'), area.get('name'), 'Área'),
            'color': area_color,
            'color_soft': _mix_with_white(area_color, 0.82),
            'macros': [],
            'macro_count': len(macros),
            'process_count': 0
        }

        for macro in macros:
            processes = macro.get('processes') or []
            macro_entry = {
                'display_name': _format_display_name(macro.get('code'), macro.get('name'), 'Macroprocesso'),
                'owner': macro.get('owner'),
                'processes': []
            }

            for proc in processes:
                struct_info = structuring_levels.get(proc.get('structuring_level') or '', structuring_levels[''])
                perf_info = performance_levels.get(proc.get('performance_level') or '', performance_levels[''])
                macro_entry['processes'].append({
                    'display_name': _format_display_name(proc.get('code'), proc.get('name'), 'Processo'),
                    'responsible': proc.get('responsible'),
                    'description': proc.get('description'),
                    'structuring': {
                        'label': struct_info['label'],
                        'color': struct_info['color'],
                        'background': _mix_with_white(struct_info['color'], 0.88)
                    },
                    'performance': {
                        'label': perf_info['label'],
                        'color': perf_info['color'],
                        'background': _mix_with_white(perf_info['color'], 0.88)
                    }
                })

            macro_entry['process_total'] = len(macro_entry['processes'])
            area_entry['process_count'] += macro_entry['process_total']
            area_entry['macros'].append(macro_entry)

        total_macros += area_entry['macro_count']
        total_processes += area_entry['process_count']
        areas.append(area_entry)

    generated_at = datetime.now()

    html_content = render_template(
        'pdf/grv_process_map_v2.html',
        company=company,
        areas=areas,
        totals={
            'areas': len(areas),
            'macros': total_macros,
            'processes': total_processes
        },
        generated_at=generated_at
    )

    header_template = ""
    footer_template = ""

    print("DEBUG: Iniciando geração de PDF...")
    
    try:
        from playwright.sync_api import sync_playwright
        print("DEBUG: Playwright importado com sucesso")
    except ImportError as e:
        print(f"DEBUG: Erro ao importar Playwright: {str(e)}")
        abort(500, description="Dependência 'playwright' não encontrada. Execute: pip install playwright && playwright install chromium")

    def _build_pdf(html: str) -> bytes:
        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                print("DEBUG: Iniciando sync_playwright...")
                with sync_playwright() as p:
                    print("DEBUG: Lançando navegador...")
                    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
                    try:
                        print("DEBUG: Criando nova página...")
                        page = browser.new_page()
                        page.set_viewport_size({"width": 794, "height": 1123})
                        print("DEBUG: Definindo conteúdo HTML...")
                        page.set_content(html, wait_until="networkidle")
                        page.emulate_media(media="print")

                        print("DEBUG: Gerando PDF...")
                        pdf = page.pdf(
                            format="A4",
                            landscape=False,
                            print_background=True,
                            display_header_footer=False,
                            header_template=header_template,
                            footer_template=footer_template,
                            prefer_css_page_size=True,
                            margin={"top": "8mm", "bottom": "8mm", "left": "6mm", "right": "6mm"}
                        )
                        print("DEBUG: PDF gerado com sucesso!")
                    finally:
                        browser.close()
                    return pdf
            except Exception as exc:
                last_error = exc
                print(f"ERRO ao gerar PDF (tentativa {attempt + 1}): {exc}")
                if attempt == 0 and _should_attempt_playwright_install(exc):
                    try:
                        print("DEBUG: Tentando instalar navegador Playwright ausente...")
                        _ensure_playwright_browser_installed('chromium')
                        print("DEBUG: Instalação Playwright concluída, repetindo tentativa...")
                        continue
                    except Exception as install_error:
                        print(f"ERRO ao instalar navegador Playwright: {install_error}")
                        last_error = install_error
                break

        if last_error:
            raise last_error
        raise RuntimeError("Falha desconhecida ao gerar PDF via Playwright")

    try:
        pdf_bytes = _build_pdf(html_content)
    except Exception as critical_error:
        print(f"ERRO CRÍTICO ao gerar PDF: {critical_error}")
        import traceback
        traceback.print_exc()
        abort(500, description=f"Erro ao gerar PDF: {critical_error}")

    safe_name = re.sub(r'[^a-z0-9_-]+', '-', (company.get('name') or 'empresa').lower()).strip('-') or 'empresa'
    filename = f"mapa-processos-v2-{safe_name}.pdf"

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@grv_bp.route('/company/<int:company_id>/process/macro')
def grv_process_macro(company_id: int):
    """Redirect to process map - Modelagem is now integrated into Arquitetura"""
    from flask import redirect
    return redirect(url_for('grv.grv_process_map', company_id=company_id))


@grv_bp.route('/company/<int:company_id>/process/list')
def grv_process_list(company_id: int):
    """Redirect to process map - AnÃ¡lise is now integrated into Arquitetura"""
    from flask import redirect
    return redirect(url_for('grv.grv_process_map', company_id=company_id))


@grv_bp.route('/company/<int:company_id>/process/modeling')
def grv_process_modeling(company_id: int):
    db = get_db()
    company = db.get_company(company_id) or {}
    processes = db.list_processes(company_id)
    macro_processes = {m['id']: m for m in db.list_macro_processes(company_id) or []}
    artifact_presence = {}
    if hasattr(db, 'get_process_artifact_presence'):
        try:
            artifact_presence = db.get_process_artifact_presence(company_id) or {}
        except Exception as exc:
            print(f"[grv_process_modeling] Warning: failed to load artifact presence -> {exc}")
            artifact_presence = {}

    process_groups = {stage['slug']: [] for stage in KANBAN_STAGE_DEFINITIONS}
    default_stage = 'inbox'
    structuring_labels = {
        '': 'Fora de Escopo',
        'initiated': 'Em andamento',
        'in_progress': 'Em andamento',
        'structured': 'Estabilizado',
        'stabilized': 'Estabilizado'
    }
    performance_labels = {
        '': 'Fora de Escopo',
        'critical': 'CrÃ­tico',
        'below': 'Abaixo do esperado',
        'initiated': 'Ajustando',
        'structured': 'SatisfatÃ³rio',
        'satisfactory': 'SatisfatÃ³rio'
    }

    for process in processes or []:
        stage_slug = (process.get('kanban_stage') or default_stage).strip().lower().replace('-', '_')
        if stage_slug not in process_groups:
            stage_slug = default_stage
        macro = macro_processes.get(process.get('macro_id'))
        flags = artifact_presence.get(process.get('id'), {})
        process_groups[stage_slug].append({
            'id': process.get('id'),
            'name': process.get('name'),
            'code': process.get('code'),
            'responsible': process.get('responsible'),
            'structuring_level': process.get('structuring_level'),
            'performance_level': process.get('performance_level'),
            'structuring_label': structuring_labels.get(process.get('structuring_level') or '', 'Sem avaliaÃ§Ã£o'),
            'performance_label': performance_labels.get(process.get('performance_level') or '', 'Sem avaliaÃ§Ã£o'),
            'macro_id': process.get('macro_id'),
            'macro_code': macro.get('code') if macro else '',
            'macro_name': macro.get('name') if macro else '',
            'description': process.get('description'),
            'order_index': process.get('order_index'),
            'kanban_stage': stage_slug,
            'artifact_flags': {
                'has_flow': bool(process.get('flow_document')),
                'has_routine': bool(flags.get('has_routine')),
                'has_pop': bool(flags.get('has_pop')),
                'has_indicator': bool(flags.get('has_indicator'))
            }
        })

    return render_template(
        'grv_process_modeling.html',
        company=company,
        navigation=grv_navigation(),
        active_id='process-modeling',
        stages=KANBAN_STAGE_DEFINITIONS,
        process_groups=process_groups
    )


@grv_bp.route('/company/<int:company_id>/process/modeling/<int:process_id>')
def grv_process_detail(company_id: int, process_id: int):
    db = get_db()
    company = db.get_company(company_id) or {}
    process = db.get_process(process_id)
    if not process or process.get('company_id') != company_id:
        abort(404)

    macros = db.list_macro_processes(company_id) or []
    macro = next((item for item in macros if item.get('id') == process.get('macro_id')), None)

    structuring_labels = {
        '': 'Fora de Escopo',
        'initiated': 'Em andamento',
        'in_progress': 'Em andamento',
        'structured': 'Estabilizado',
        'stabilized': 'Estabilizado'
    }
    performance_labels = {
        '': 'Fora de Escopo',
        'critical': 'CrÃ­tico',
        'below': 'Abaixo do esperado',
        'initiated': 'Ajustando',
        'structured': 'SatisfatÃ³rio',
        'satisfactory': 'SatisfatÃ³rio'
    }
    process_detail = dict(process)
    process_detail['structuring_label'] = structuring_labels.get(process.get('structuring_level') or '', 'Sem avaliaÃ§Ã£o')
    process_detail['performance_label'] = performance_labels.get(process.get('performance_level') or '', 'Sem avaliaÃ§Ã£o')

    stage_lookup = {stage['slug']: stage for stage in KANBAN_STAGE_DEFINITIONS}
    stage_info = stage_lookup.get(process_detail.get('kanban_stage'), stage_lookup['inbox'])

    stage_palette = {
        'inbox': {'bg': '#eff6ff', 'fg': '#1d4ed8'},
        'out_of_scope': {'bg': '#f8fafc', 'fg': '#64748b'},
        'designing': {'bg': '#fef3c7', 'fg': '#b45309'},
        'deploying': {'bg': '#ede9fe', 'fg': '#5b21b6'},
        'stabilizing': {'bg': '#dcfce7', 'fg': '#047857'},
        'stable': {'bg': '#e0f2f1', 'fg': '#0f766e'}
    }
    stage_badge = stage_palette.get(process_detail.get('kanban_stage'), stage_palette['inbox'])

    # Buscar modelos de relatÃ³rio disponÃ­veis
    from modules.report_models import ReportModelsManager
    try:
        models_manager = ReportModelsManager()
        report_models = models_manager.get_all_models()
    except Exception as e:
        print(f"Erro ao buscar modelos de relatÃ³rio: {e}")
        report_models = []

    # Buscar padrÃµes de relatÃ³rio disponÃ­veis
    from modules.report_patterns import ReportPatternsManager
    try:
        patterns_manager = ReportPatternsManager()
        report_patterns = patterns_manager.get_patterns_by_type('process')
    except Exception as e:
        print(f"Erro ao buscar padrÃµes de relatÃ³rio: {e}")
        report_patterns = []

    return render_template(
        'grv_process_detail.html',
        company=company,
        navigation=grv_navigation(),
        active_id='process-modeling',
        process=process_detail,
        macro=macro,
        stage_info=stage_info,
        stage_badge=stage_badge,
        detail_tabs=PROCESS_DETAIL_TABS,
        report_models=report_models,
        report_patterns=report_patterns
    )


# API Routes for POP Activities Management
# Padrão de URL: /api/companies/<company_id>/processes/<process_id>/activities/...
@grv_bp.route('/api/companies/<int:company_id>/processes/<int:process_id>/activities', methods=['GET', 'POST'])
def api_process_activities(company_id: int, process_id: int):
    """List or create POP activities for a process"""
    from flask import jsonify, request
    db = get_db()
    
    # Verificar se o processo existe e pertence à empresa
    process = db.get_process(process_id)
    if not process or process.get('company_id') != company_id:
        return jsonify({'success': False, 'error': 'Process not found'}), 404
    
    if request.method == 'GET':
        # Buscar atividades do POP usando método do banco
        activities = db.list_process_activities(process_id) or []
        return jsonify({'success': True, 'data': activities})
    
    elif request.method == 'POST':
        # Criar nova atividade
        data = request.json or {}
        name = (data.get('name') or '').strip()
        suffix = (data.get('suffix') or '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Activity name is required'}), 400
        
        if not suffix:
            return jsonify({'success': False, 'error': 'Activity suffix is required'}), 400
        
        # Criar atividade no banco
        activity_data = {
            'name': name,
            'code_suffix': suffix,
            'suffix': suffix,
            'layout': 'single'
        }
        
        new_id = db.create_process_activity(process_id, activity_data)
        
        if new_id:
            # Buscar a atividade criada
            new_activity = db.get_process_activity(new_id)
            if new_activity:
                new_activity['entries'] = []
            return jsonify({'success': True, 'data': new_activity})
        else:
            return jsonify({'success': False, 'error': 'Failed to save activity'}), 500


@grv_bp.route('/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>', methods=['GET', 'PUT', 'DELETE'])
def api_process_activity_detail(company_id: int, process_id: int, activity_id: int):
    """Get, update or delete a POP activity"""
    from flask import jsonify, request
    db = get_db()
    
    # Verificar se o processo existe e pertence à empresa
    process = db.get_process(process_id)
    if not process or process.get('company_id') != company_id:
        return jsonify({'success': False, 'error': 'Process not found'}), 404
    
    # Buscar a atividade
    activity = db.get_process_activity(activity_id)
    if not activity:
        return jsonify({'success': False, 'error': 'Activity not found'}), 404
    
    if request.method == 'GET':
        return jsonify({'success': True, 'data': activity})
    
    elif request.method == 'DELETE':
        # Remover atividade
        success = db.delete_process_activity(activity_id)
        return jsonify({'success': success})
    
    elif request.method == 'PUT':
        # Atualizar atividade
        data = request.json or {}
        name = (data.get('name') or '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Activity name is required'}), 400
        
        update_data = {'name': name}
        success = db.update_process_activity(activity_id, update_data)
        
        return jsonify({'success': success})


@grv_bp.route('/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries', methods=['POST'])
def api_create_process_activity_entry(company_id: int, process_id: int, activity_id: int):
    """Create a new entry (step) for a POP activity"""
    from flask import jsonify, request
    from datetime import datetime as dt
    import os
    import uuid
    
    # Log em arquivo para debug
    with open('debug_api.log', 'a', encoding='utf-8') as f:
        f.write(f"\n=== {dt.now()} - FUNÇÃO CHAMADA! company_id={company_id}, process_id={process_id}, activity_id={activity_id} ===\n")
    print(f"=== FUNÇÃO CHAMADA! company_id={company_id}, process_id={process_id}, activity_id={activity_id} ===")
    
    db = get_db()
    
    print(f"DEBUG: Recebendo requisição para criar etapa - company_id={company_id}, process_id={process_id}, activity_id={activity_id}")
    
    # Verificar se o processo existe e pertence à empresa
    process = db.get_process(process_id)
    if not process or process.get('company_id') != company_id:
        print(f"DEBUG: Processo não encontrado ou não pertence à empresa")
        return jsonify({'success': False, 'error': 'Process not found'}), 404
    
    print(f"DEBUG: Processo encontrado: {process.get('name')}")
    
    # Verificar se a atividade existe
    activity = db.get_process_activity(activity_id)
    if not activity:
        print(f"DEBUG: Atividade {activity_id} não encontrada!")
        return jsonify({'success': False, 'error': 'Activity not found'}), 404
    
    print(f"DEBUG: Atividade encontrada: {activity.get('name')}")
    
    # Processar dados do formulário
    form_data = request.form
    file = request.files.get('image')
    
    layout = form_data.get('layout', 'single')
    text_content = (form_data.get('text_content') or '').strip()
    image_width = form_data.get('image_width', '280')
    
    print(f"DEBUG: Dados recebidos - layout={layout}, text_content={text_content[:50] if text_content else 'VAZIO'}, image_width={image_width}")
    
    if not text_content:
        print(f"DEBUG: Texto vazio!")
        return jsonify({'success': False, 'error': 'Text content is required'}), 400
    
    # Processar imagem se fornecida
    image_path = None
    if file and file.filename:
        print(f"DEBUG: Processando imagem: {file.filename}")
        # Criar diretório de uploads se não existir
        upload_dir = os.path.join('static', 'uploads', 'pop')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Gerar nome único para o arquivo
        file_ext = os.path.splitext(file.filename)[1]
        timestamp = dt.now().strftime('%Y%m%d%H%M%S')
        unique_name = f"pop-{process_id}-{activity_id}-{timestamp}-{uuid.uuid4().hex[:8]}{file_ext}"
        
        # Salvar arquivo
        file_path = os.path.join(upload_dir, unique_name)
        file.save(file_path)
        
        # URL relativa para o arquivo
        image_path = f"uploads/pop/{unique_name}"
        print(f"DEBUG: Imagem salva em: {image_path}")
    else:
        print(f"DEBUG: Nenhuma imagem fornecida")
    
    # Criar nova etapa
    entry_data = {
        'layout': layout,
        'text_content': text_content,
        'image_path': image_path,
        'image_width': int(image_width) if image_width else 280
    }
    
    print(f"DEBUG: Criando nova etapa: {entry_data}")
    
    # Salvar no banco
    print(f"DEBUG: Salvando no banco...")
    try:
        new_id = db.create_process_activity_entry(activity_id, entry_data)
        print(f"DEBUG: Método retornou new_id={new_id}")
        
        if new_id:
            print(f"DEBUG: Etapa salva com sucesso! ID: {new_id}")
            # Buscar a etapa criada
            new_entry = db.get_process_activity_entry(new_id)
            print(f"DEBUG: Etapa buscada: {new_entry}")
            
            if new_entry:
                return jsonify({'success': True, 'data': new_entry})
            else:
                print(f"DEBUG: Falha ao buscar etapa criada!")
                return jsonify({'success': False, 'error': 'Entry created but not found', 'message': 'Falha ao buscar no banco'}), 500
        else:
            print(f"DEBUG: Falha ao salvar etapa! new_id é None")
            return jsonify({'success': False, 'error': 'create_failed', 'message': 'Falha ao criar no banco'}), 500
    except Exception as e:
        print(f"DEBUG: EXCEÇÃO ao salvar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'exception', 'message': str(e)}), 500


@grv_bp.route('/api/companies/<int:company_id>/processes/<int:process_id>/activities/<int:activity_id>/entries/<int:entry_id>', methods=['GET', 'PUT', 'DELETE'])
def api_process_activity_entry_detail(company_id: int, process_id: int, activity_id: int, entry_id: int):
    """Get, update or delete a POP entry"""
    from flask import jsonify, request
    import os
    import uuid
    from datetime import datetime
    db = get_db()
    
    # Verificar se o processo existe e pertence à empresa
    process = db.get_process(process_id)
    if not process or process.get('company_id') != company_id:
        return jsonify({'success': False, 'error': 'Process not found'}), 404
    
    # Buscar a etapa
    entry = db.get_process_activity_entry(entry_id)
    if not entry:
        return jsonify({'success': False, 'error': 'Entry not found'}), 404
    
    if request.method == 'GET':
        return jsonify({'success': True, 'data': entry})
    
    elif request.method == 'DELETE':
        # Remover etapa e sua imagem se existir
        if entry.get('image_path'):
            image_path = os.path.join('static', entry['image_path'])
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except:
                    pass
        
        success = db.delete_process_activity_entry(entry_id)
        return jsonify({'success': success})
    
    elif request.method == 'PUT':
        # Atualizar etapa
        form_data = request.form
        file = request.files.get('image')
        remove_image = form_data.get('remove_image') == 'true'
        
        layout = form_data.get('layout', 'single')
        text_content = (form_data.get('text_content') or '').strip()
        image_width = form_data.get('image_width', '280')
        
        if not text_content:
            return jsonify({'success': False, 'error': 'Text content is required'}), 400
        
        # Preparar dados para atualização
        update_data = {
            'layout': layout,
            'text_content': text_content,
            'image_width': int(image_width) if image_width else 280,
            'image_path': entry.get('image_path')  # Manter imagem atual por padrão
        }
        
        # Processar remoção de imagem
        if remove_image and entry.get('image_path'):
            image_path = os.path.join('static', entry['image_path'])
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except:
                    pass
            update_data['image_path'] = None
        
        # Processar nova imagem
        if file and file.filename:
            # Remover imagem antiga se existir
            if entry.get('image_path'):
                old_image_path = os.path.join('static', entry['image_path'])
                if os.path.exists(old_image_path):
                    try:
                        os.remove(old_image_path)
                    except:
                        pass
            
            # Salvar nova imagem
            upload_dir = os.path.join('static', 'uploads', 'pop')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_ext = os.path.splitext(file.filename)[1]
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            unique_name = f"pop-{process_id}-{activity_id}-{timestamp}-{uuid.uuid4().hex[:8]}{file_ext}"
            
            file_path = os.path.join(upload_dir, unique_name)
            file.save(file_path)
            
            update_data['image_path'] = f"uploads/pop/{unique_name}"
        
        success = db.update_process_activity_entry(entry_id, update_data)
        return jsonify({'success': success})


@grv_bp.route('/company/<int:company_id>/process/analysis')
def grv_process_analysis(company_id: int):
    db = get_db()
    company = db.get_company(company_id) or {}
    return render_template('grv_process_analysis.html', 
                         company=company, 
                         navigation=grv_navigation(), 
                         active_id='process-analysis')


@grv_bp.route('/company/<int:company_id>/routine/work-distribution')
def grv_routine_work_distribution(company_id: int):
    company = get_db().get_company(company_id) or {}
    return render_template('grv_routine_work_distribution.html', company=company, navigation=grv_navigation(), active_id='routine-work-distribution')


@grv_bp.route('/company/<int:company_id>/routine/capacity')
def grv_routine_capacity(company_id: int):
    company = get_db().get_company(company_id) or {}
    return render_template('grv_routine_capacity.html', company=company, navigation=grv_navigation(), active_id='routine-capacity')


@grv_bp.route('/company/<int:company_id>/routine/activities')
def grv_routine_activities(company_id: int):
    """Unified activity management - Projects and Process Instances"""
    from database.postgres_helper import connect as pg_connect
    import json
    db = get_db()
    company = db.get_company(company_id) or {}
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    ensure_indicator_schema(conn)
    ensure_indicator_goals_schema(conn)
    
    # Get all employees for filters
    cursor.execute('SELECT id, name FROM employees WHERE company_id = %s ORDER BY name', (company_id,))
    employees = [dict(row) for row in cursor.fetchall()]
    
    # Get all processes for filters
    cursor.execute(
        '''
        SELECT id, code, name
        FROM processes
        WHERE company_id = %s
        ORDER BY 
            CASE WHEN code IS NULL OR TRIM(code) = '' THEN 1 ELSE 0 END,
            code,
            name
        ''',
        (company_id,)
    )
    processes = [dict(row) for row in cursor.fetchall()]
    
    # Get all projects for filters
    cursor.execute('SELECT id, code, title as name FROM company_projects WHERE company_id = %s ORDER BY title', (company_id,))
    projects = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template(
        'grv_routine_activities.html',
        company=company,
        employees=employees,
        processes=processes,
        projects=projects,
        navigation=grv_navigation(),
        active_id='routine-activities'
    )


@grv_bp.route('/company/<int:company_id>/routine/incidents')
def grv_routine_incidents(company_id: int):
    """Occurrences management page"""
    from database.postgres_helper import connect as pg_connect
    db = get_db()
    company = db.get_company(company_id) or {}
    
    # Get employees, processes and projects for filters
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    # Get employees
    cursor.execute('SELECT id, name FROM employees WHERE company_id = %s ORDER BY name', (company_id,))
    employees = [dict(row) for row in cursor.fetchall()]
    
    # Get processes
    cursor.execute(
        '''
        SELECT id, code, name
        FROM processes
        WHERE company_id = %s
        ORDER BY 
            CASE WHEN code IS NULL OR TRIM(code) = '' THEN 1 ELSE 0 END,
            code,
            name
        ''',
        (company_id,)
    )
    processes = [dict(row) for row in cursor.fetchall()]
    
    # Get projects
    cursor.execute('SELECT id, code, title as name FROM company_projects WHERE company_id = %s ORDER BY title', (company_id,))
    projects = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template(
        'grv_occurrences_v2.html',
        company=company,
        employees=employees,
        processes=processes,
        projects=projects,
        navigation=grv_navigation(),
        active_id='routine-incidents'
    )


@grv_bp.route('/company/<int:company_id>/routine/efficiency')
def grv_routine_efficiency(company_id: int):
    company = get_db().get_company(company_id) or {}
    return render_template('grv_routine_efficiency.html', company=company, navigation=grv_navigation(), active_id='routine-efficiency')


@grv_bp.route('/company/<int:company_id>/projects/portfolios')
def grv_projects_portfolios(company_id: int):
    """Project portfolios management page"""
    company = get_db().get_company(company_id) or {}
    return render_template('grv_projects_portfolios.html', company=company, navigation=grv_navigation(), active_id='project-portfolios')


@grv_bp.route('/company/<int:company_id>/projects/projects')
def grv_projects_projects(company_id: int):
    """Company projects overview"""
    from database.postgres_helper import connect as pg_connect
    db = get_db()
    company = db.get_company(company_id) or {}
    
    # Get PEV plans
    pev_plans = db.get_plans_by_company(company_id) or []
    
    # Get GRV portfolios
    grv_portfolios = []
    try:
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, code, name FROM portfolios WHERE company_id = %s ORDER BY LOWER(name)",
            (company_id,)
        )
        for row in cursor.fetchall():
            grv_portfolios.append({
                'id': row['id'],
                'code': row['code'],
                'name': row['name'],
                'origin': 'GRV Portfolio'
            })
        conn.close()
    except Exception as e:
        print(f"Erro ao buscar portfólios GRV: {e}")
    
    # Get company projects (projetos criados)
    company_projects = []
    try:
        conn = pg_connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.id, p.title, p.code, p.plan_id, p.plan_type,
                   CASE 
                       WHEN p.plan_type = 'PEV' THEN pl.name
                       ELSE NULL
                   END as plan_name
            FROM company_projects p
            LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
            WHERE p.company_id = %s
            ORDER BY p.created_at DESC
            """,
            (company_id,)
        )
        for row in cursor.fetchall():
            row_dict = dict(row)
            company_projects.append({
                'id': row_dict.get('id'),
                'code': row_dict.get('code'),
                'name': row_dict.get('title'),
                'origin': 'Projeto',
                'plan_name': row_dict.get('plan_name')
            })
        conn.close()
    except Exception as e:
        print(f"Erro ao buscar company_projects: {e}")
        import traceback
        traceback.print_exc()
    
    # Mark PEV plans with origin
    for plan in pev_plans:
        plan['origin'] = 'PEV Plan'
    
    # Combine all lists
    all_plans = pev_plans + grv_portfolios + company_projects
    
    return render_template(
        'grv_projects_projects.html',
        company=company,
        plans=all_plans,
        navigation=grv_navigation(),
        active_id='project-projects'
    )


@grv_bp.route('/company/<int:company_id>/project/<int:project_id>')
def grv_project_shortcut(company_id: int, project_id: int):
    """Legacy shortcut: redirect to project management page"""
    return redirect(url_for('grv.grv_project_manage', company_id=company_id, project_id=project_id))


@grv_bp.route('/company/<int:company_id>/projects/<int:project_id>/manage')
def grv_project_manage(company_id: int, project_id: int):
    """Project management page with activities Kanban"""
    from database.postgres_helper import connect as pg_connect
    db = get_db()
    company = db.get_company(company_id) or {}
    
    # Get project details
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT
            p.*,
            CASE 
                WHEN p.plan_type = 'GRV' THEN pf.name
                WHEN p.plan_type = 'PEV' THEN pl.name
                ELSE COALESCE(pf.name, pl.name)
            END AS plan_name,
            e.name AS responsible_name
        FROM company_projects p
        LEFT JOIN portfolios pf ON pf.id = p.plan_id AND p.plan_type = 'GRV'
        LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
        LEFT JOIN employees e ON e.id = p.responsible_id
        WHERE p.company_id = %s AND p.id = %s
        """,
        (company_id, project_id)
    )
    
    project_row = cursor.fetchone()
    conn.close()
    
    if not project_row:
        from flask import abort
        abort(404)
    
    project = dict(project_row)
    
    # Define Kanban stages for activities
    stages = [
        {'slug': 'inbox', 'title': 'Caixa de Entrada', 'color': '#94a3b8'},
        {'slug': 'waiting', 'title': 'Aguardando', 'color': '#fbbf24'},
        {'slug': 'executing', 'title': 'Executando', 'color': '#3b82f6'},
        {'slug': 'pending', 'title': 'PendÃªncias', 'color': '#f59e0b'},
        {'slug': 'suspended', 'title': 'Suspensos', 'color': '#ef4444'},
        {'slug': 'completed', 'title': 'ConcluÃ­dos', 'color': '#10b981'}
    ]
    
    return render_template(
        'grv_project_manage.html',
        company=company,
        project=project,
        stages=stages,
        navigation=grv_navigation(),
        active_id='project-projects'
    )


@grv_bp.route('/company/<int:company_id>/projects/analysis')
def grv_projects_analysis(company_id: int):
    """Projects analysis page with all projects and their activities"""
    from database.postgres_helper import connect as pg_connect
    import json
    db = get_db()
    company = db.get_company(company_id) or {}
    
    # Get all projects for the company
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT
            p.*,
            CASE 
                WHEN p.plan_type = 'GRV' THEN pf.name
                WHEN p.plan_type = 'PEV' THEN pl.name
                ELSE COALESCE(pf.name, pl.name)
            END AS plan_name,
            e.name AS responsible_name
        FROM company_projects p
        LEFT JOIN portfolios pf ON pf.id = p.plan_id AND p.plan_type = 'GRV'
        LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
        LEFT JOIN employees e ON e.id = p.responsible_id
        WHERE p.company_id = %s
        ORDER BY p.created_at DESC
        """,
        (company_id,)
    )
    
    projects_rows = cursor.fetchall()
    conn.close()
    
    # Process projects and their activities
    projects = []
    project_colors = [
        '#fef3c7', '#dbeafe', '#fce7f3', '#dcfce7', '#fef7cd', 
        '#e0e7ff', '#fed7aa', '#f3e8ff', '#ecfdf5', '#fef2f2'
    ]
    
    for i, project_row in enumerate(projects_rows):
        project = dict(project_row)
        
        # Parse activities
        try:
            activities = json.loads(project.get('activities', '[]'))
        except:
            activities = []
        
        project['activities'] = activities
        project['color'] = project_colors[i % len(project_colors)]
        
        # Calculate activity stats
        project['total_activities'] = len(activities)
        project['completed_activities'] = len([a for a in activities if a.get('status') == 'completed'])
        project['in_progress_activities'] = len([a for a in activities if a.get('status') in ['executing', 'waiting']])
        project['pending_activities'] = len([a for a in activities if a.get('status') in ['inbox', 'pending']])
        
        projects.append(project)
    
    # Define Kanban stages for activities (same as project manage)
    stages = [
        {'slug': 'inbox', 'title': 'Caixa de Entrada', 'color': '#94a3b8'},
        {'slug': 'waiting', 'title': 'Aguardando', 'color': '#fbbf24'},
        {'slug': 'executing', 'title': 'Executando', 'color': '#3b82f6'},
        {'slug': 'pending', 'title': 'PendÃªncias', 'color': '#f59e0b'},
        {'slug': 'suspended', 'title': 'Suspensos', 'color': '#ef4444'},
        {'slug': 'completed', 'title': 'ConcluÃ­dos', 'color': '#10b981'}
    ]
    
    return render_template(
        'grv_projects_analysis.html',
        company=company,
        projects=projects,
        stages=stages,
        navigation=grv_navigation(),
        active_id='project-analysis'
    )


@grv_bp.route('/company/<int:company_id>/process/instances')
def grv_process_instances(company_id: int):
    """Process instances management page"""
    db = get_db()
    company = db.get_company(company_id) or {}
    
    # Define status options
    status_options = [
        {'value': 'pending', 'label': 'Pendente', 'color': '#94a3b8'},
        {'value': 'in_progress', 'label': 'Em Andamento', 'color': '#3b82f6'},
        {'value': 'waiting', 'label': 'Aguardando', 'color': '#fbbf24'},
        {'value': 'completed', 'label': 'ConcluÃ­do', 'color': '#10b981'},
        {'value': 'cancelled', 'label': 'Cancelado', 'color': '#ef4444'}
    ]
    
    # Define priority options
    priority_options = [
        {'value': 'low', 'label': 'Baixa', 'color': '#94a3b8'},
        {'value': 'normal', 'label': 'Normal', 'color': '#3b82f6'},
        {'value': 'high', 'label': 'Alta', 'color': '#f59e0b'},
        {'value': 'urgent', 'label': 'Urgente', 'color': '#ef4444'}
    ]
    
    return render_template(
        'grv_process_instances.html',
        company=company,
        status_options=status_options,
        priority_options=priority_options,
        navigation=grv_navigation(),
        active_id='process-instances'
    )


@grv_bp.route('/company/<int:company_id>/process/instances/<int:instance_id>/manage')
def grv_process_instance_manage(company_id: int, instance_id: int):
    """Process instance management page"""
    from database.postgres_helper import connect as pg_connect
    db = get_db()
    company = db.get_company(company_id) or {}
    
    # Get instance details
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT
            pi.*,
            p.name AS process_name,
            p.code AS process_code
        FROM process_instances pi
        LEFT JOIN processes p ON p.id = pi.process_id
        WHERE pi.company_id = %s AND pi.id = %s
        """,
        (company_id, instance_id)
    )
    
    instance_row = cursor.fetchone()
    conn.close()
    
    if not instance_row:
        from flask import abort
        abort(404)
    
    instance = dict(instance_row)
    
    return render_template(
        'grv_process_instance_manage.html',
        company=company,
        instance=instance,
        navigation=grv_navigation(),
        active_id='process-instances'
    )


# =============================================================================
# GESTÃƒO DE INDICADORES
# =============================================================================

@grv_bp.route('/company/<int:company_id>/indicators/tree')
def grv_indicators_tree(company_id: int):
    """Árvore de Indicadores - Grupos e Subgrupos hierÃ¡rquicos"""
    db = get_db()
    company = db.get_company(company_id) or {}
    return render_template(
        'grv_indicators_tree.html',
        company=company,
        navigation=grv_navigation(),
        active_id='indicators-tree'
    )


@grv_bp.route('/company/<int:company_id>/indicator-groups/form', defaults={'group_id': None})
@grv_bp.route('/company/<int:company_id>/indicator-groups/form/<int:group_id>')
def grv_indicator_group_form(company_id: int, group_id: Optional[int] = None):
    """FormulÃ¡rio em popup para criar ou editar grupos de indicadores."""
    db = get_db()
    company = db.get_company(company_id) or {}
    group = None

    if group_id:
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM indicator_groups
            WHERE id = %s AND company_id = %s
        """, (group_id, company_id))
        row = cursor.fetchone()
        conn.close()
        if row:
            group = dict(row)

    return render_template(
        'grv_indicator_group_form.html',
        company=company,
        company_id=company_id,
        group=group
    )


@grv_bp.route('/company/<int:company_id>/indicators/list')
def grv_indicators_list(company_id: int):
    """Lista e CRUD de Indicadores"""
    from database.postgres_helper import connect as pg_connect
    db = get_db()
    company = db.get_company(company_id) or {}
    
    # Get related data for dropdowns
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    # Get processes
    cursor.execute('SELECT id, code, name FROM processes WHERE company_id = %s ORDER BY name', (company_id,))
    processes = [dict(row) for row in cursor.fetchall()]
    
    # Get projects
    cursor.execute('SELECT id, code, title as name FROM company_projects WHERE company_id = %s ORDER BY title', (company_id,))
    projects = [dict(row) for row in cursor.fetchall()]
    
    # Get employees
    cursor.execute('SELECT id, name FROM employees WHERE company_id = %s ORDER BY name', (company_id,))
    employees = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template(
        'grv_indicators_list.html',
        company=company,
        processes=processes,
        projects=projects,
        employees=employees,
        navigation=grv_navigation(),
        active_id='indicators-list'
    )


@grv_bp.route('/company/<int:company_id>/indicators/form', defaults={'indicator_id': None})
@grv_bp.route('/company/<int:company_id>/indicators/form/<int:indicator_id>')
def grv_indicator_form(company_id: int, indicator_id: Optional[int] = None):
    """FormulÃ¡rio pop-up para criaÃ§Ã£o/ediÃ§Ã£o de indicadores"""
    from database.postgres_helper import connect as pg_connect
    db = get_db()
    company = db.get_company(company_id) or {}
    default_process_id = request.args.get('process_id', type=int)
    
    # Capturar parÃ¢metros de contexto da URL
    context_params = {
        'plan_id': request.args.get('plan_id'),
        'okr_id': request.args.get('okr_id', type=int),
        'okr_level': request.args.get('okr_level'),
        'project_id': request.args.get('project_id', type=int),
        'page_type': request.args.get('page_type')
    }

    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()

    cursor.execute('SELECT id, code, name FROM indicator_groups WHERE company_id = %s ORDER BY code', (company_id,))
    groups = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        '''
        SELECT id, code, name
        FROM processes
        WHERE company_id = %s
        ORDER BY 
            CASE WHEN code IS NULL OR TRIM(code) = '' THEN 1 ELSE 0 END,
            code,
            name
        ''',
        (company_id,)
    )
    processes = [dict(row) for row in cursor.fetchall()]

    cursor.execute('SELECT id, code, title as name FROM company_projects WHERE company_id = %s ORDER BY title', (company_id,))
    projects = [dict(row) for row in cursor.fetchall()]

    cursor.execute('SELECT id, name FROM employees WHERE company_id = %s ORDER BY name', (company_id,))
    employees = [dict(row) for row in cursor.fetchall()]

    # Buscar planejamentos da empresa
    plans = db.get_plans_by_company(company_id)
    plans_list = [{'id': p['id'], 'name': p['name']} for p in plans] if plans else []

    indicator = None
    if indicator_id:
        cursor.execute("""
            SELECT *
            FROM indicators
            WHERE id = %s AND company_id = %s
        """, (indicator_id, company_id))
        row = cursor.fetchone()
        if row:
            indicator = dict(row)

    conn.close()

    return render_template(
        'grv_indicator_form.html',
        company=company,
        company_id=company_id,
        indicator=indicator,
        groups=groups,
        processes=processes,
        projects=projects,
        employees=employees,
        plans=plans_list,
        default_process_id=default_process_id,
        context_params=context_params
    )


@grv_bp.route('/company/<int:company_id>/indicators/goals')
def grv_indicators_goals(company_id: int):
    """Metas de Indicadores"""
    from database.postgres_helper import connect as pg_connect
    db = get_db()
    company = db.get_company(company_id) or {}
    
    # Get employees for responsible dropdown
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name FROM employees WHERE company_id = %s ORDER BY name', (company_id,))
    employees = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template(
        'grv_indicators_goals.html',
        company=company,
        employees=employees,
        navigation=grv_navigation(),
        active_id='indicators-goals'
    )


@grv_bp.route('/company/<int:company_id>/indicator-goals/form', defaults={'goal_id': None})
@grv_bp.route('/company/<int:company_id>/indicator-goals/form/<int:goal_id>')
def grv_indicator_goal_form(company_id: int, goal_id: Optional[int] = None):
    """FormulÃ¡rio pop-up para metas de indicadores"""
    from database.postgres_helper import connect as pg_connect
    db = get_db()
    company = db.get_company(company_id) or {}

    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, code, name
        FROM indicators
        WHERE company_id = %s
        ORDER BY name
    """, (company_id,))
    indicators = [dict(row) for row in cursor.fetchall()]

    cursor.execute('SELECT id, name FROM employees WHERE company_id = %s ORDER BY name', (company_id,))
    employees = [dict(row) for row in cursor.fetchall()]

    goal = None
    if goal_id:
        cursor.execute("""
            SELECT *
            FROM indicator_goals
            WHERE id = %s AND company_id = %s
        """, (goal_id, company_id))
        row = cursor.fetchone()
        if row:
            goal = normalize_goal_row(dict(row))

    conn.close()

    return render_template(
        'grv_indicator_goal_form.html',
        company=company,
        company_id=company_id,
        indicators=indicators,
        employees=employees,
        goal=goal
    )


@grv_bp.route('/company/<int:company_id>/indicators/data')
def grv_indicators_data(company_id: int):
    """Registros de Dados dos Indicadores"""
    db = get_db()
    company = db.get_company(company_id) or {}
    return render_template(
        'grv_indicators_data.html',
        company=company,
        navigation=grv_navigation(),
        active_id='indicators-data'
    )


@grv_bp.route('/company/<int:company_id>/indicator-data/form', defaults={'record_id': None})
@grv_bp.route('/company/<int:company_id>/indicator-data/form/<int:record_id>')
def grv_indicator_data_form(company_id: int, record_id: Optional[int] = None):
    """FormulÃ¡rio pop-up para registros de dados"""
    from database.postgres_helper import connect as pg_connect
    db = get_db()
    company = db.get_company(company_id) or {}

    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            g.id,
            g.code as goal_code,
            i.name as indicator_name
        FROM indicator_goals g
        INNER JOIN indicators i ON g.indicator_id = i.id
        WHERE g.company_id = %s
        ORDER BY i.name
    """, (company_id,))
    goals = [dict(row) for row in cursor.fetchall()]

    record = None
    if record_id:
        cursor.execute("""
            SELECT *
            FROM indicator_data
            WHERE id = %s AND company_id = %s
        """, (record_id, company_id))
        row = cursor.fetchone()
        if row:
            record = dict(row)

    conn.close()

    return render_template(
        'grv_indicator_data_form.html',
        company=company,
        company_id=company_id,
        goals=goals,
        record=record
    )


@grv_bp.route('/company/<int:company_id>/indicators/analysis')
def grv_indicators_analysis(company_id: int):
    """AnÃ¡lises de Indicadores"""
    db = get_db()
    company = db.get_company(company_id) or {}
    return render_template(
        'grv_indicators_analysis.html',
        company=company,
        navigation=grv_navigation(),
        active_id='indicators-analysis'
    )


# =============================================================================
# API - AUXILIARES PARA INDICADORES
# =============================================================================

@grv_bp.route('/api/plans/<int:plan_id>/okrs', methods=['GET'])
def api_get_plan_okrs(plan_id: int):
    """Get OKRs for a specific plan"""
    try:
        from database.postgres_helper import connect as pg_connect
        
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()
        
        # Buscar OKRs globais aprovados
        cursor.execute("""
            SELECT id, objective, type as okr_type, owner, 'global' as okr_level, department
            FROM okr_global_records 
            WHERE plan_id = %s AND stage = 'approval'
            ORDER BY objective
        """, (plan_id,))
        
        global_okrs = [dict(row) for row in cursor.fetchall()]
        
        # Buscar OKRs de Ã¡rea finalizados
        cursor.execute("""
            SELECT id, objective, type as okr_type, owner, 'area' as okr_level, department
            FROM okr_area_records 
            WHERE plan_id = %s AND stage = 'final'
            ORDER BY objective
        """, (plan_id,))
        
        area_okrs = [dict(row) for row in cursor.fetchall()]
        
        # Combinar todos os OKRs
        all_okrs = global_okrs + area_okrs
        
        conn.close()
        
        return jsonify({'success': True, 'data': all_okrs})
        
    except Exception as e:
        print(f"Error getting plan OKRs: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# =============================================================================
# API - GESTÃƒO DE INDICADORES
# =============================================================================

# ===== Árvore de Indicadores (Grupos) =====

@grv_bp.route('/api/company/<int:company_id>/indicator-groups', methods=['GET'])
def api_get_indicator_groups(company_id: int):
    """Lista todos os grupos de indicadores da empresa"""
    from database.postgres_helper import connect as pg_connect
    import json
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            g.*,
            p.name as parent_name,
            p.code as parent_code
        FROM indicator_groups g
        LEFT JOIN indicator_groups p ON g.parent_id = p.id
        WHERE g.company_id = %s
        ORDER BY g.code
    """, (company_id,))
    
    groups = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'success': True, 'data': groups})


@grv_bp.route('/api/company/<int:company_id>/indicator-groups/<int:group_id>', methods=['GET'])
def api_get_indicator_group(company_id: int, group_id: int):
    """ObtÃ©m detalhes de um grupo especÃ­fico"""
    from database.postgres_helper import connect as pg_connect
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM indicator_groups 
        WHERE id = %s AND company_id = %s
    """, (group_id, company_id))
    
    group = cursor.fetchone()
    conn.close()
    
    if not group:
        return jsonify({'success': False, 'message': 'Grupo nÃ£o encontrado'}), 404
    
    return jsonify({'success': True, 'data': dict(group)})


@grv_bp.route('/api/company/<int:company_id>/indicator-groups', methods=['POST'])
@auto_log_crud('indicator_group')
def api_create_indicator_group(company_id: int):
    """Cria um novo grupo de indicadores"""
    from database.postgres_helper import connect as pg_connect
    from flask import request
    
    data = request.json
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    ensure_indicator_goals_schema(conn)
    
    try:
        # Gerar cÃ³digo automÃ¡tico
        cursor.execute("""
            SELECT client_code FROM companies WHERE id = %s
        """, (company_id,))
        company_row = cursor.fetchone()
        company_code = 'AA'
        if company_row:
            raw_code = (company_row[0] or '').strip()
            if raw_code:
                company_code = raw_code.upper()
        
        # Contar grupos existentes para gerar prÃ³ximo nÃºmero
        parent_id = data.get('parent_id')
        if parent_id:
            cursor.execute("""
                SELECT code FROM indicator_groups WHERE id = %s
            """, (parent_id,))
            parent_row = cursor.fetchone()
            parent_code = parent_row[0] if parent_row else ''
            
            cursor.execute("""
                SELECT COUNT(*) FROM indicator_groups 
                WHERE company_id = %s AND parent_id = %s
            """, (company_id, parent_id))
            count = cursor.fetchone()[0]
            code = f"{parent_code}.{count + 1}"
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM indicator_groups 
                WHERE company_id = %s AND parent_id IS NULL
            """, (company_id,))
            count = cursor.fetchone()[0]
            code = f"{company_code}.I.{count + 1}"
        
        cursor.execute("""
            INSERT INTO indicator_groups 
            (company_id, parent_id, code, name, description)
            VALUES (%s, %s, ?, ?, ?)
        """, (
            company_id,
            parent_id,
            code,
            data.get('name'),
            data.get('description')
        ))
        
        conn.commit()
        group_id = cursor.lastrowid
        
        cursor.execute("SELECT * FROM indicator_groups WHERE id = %s", (group_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            indicator = dict(row)
            indicator['code'] = normalize_indicator_code(indicator.get('code'))
            return jsonify({'success': True, 'data': indicator}), 201
        return jsonify({'success': True, 'data': {}}), 201
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


@grv_bp.route('/api/company/<int:company_id>/indicator-groups/<int:group_id>', methods=['PUT'])
@auto_log_crud('indicator_group')
def api_update_indicator_group(company_id: int, group_id: int):
    """Atualiza um grupo de indicadores"""
    from database.postgres_helper import connect as pg_connect
    from flask import request
    
    data = request.json
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE indicator_groups 
            SET name = %s, description = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND company_id = %s
        """, (
            data.get('name'),
            data.get('description'),
            group_id,
            company_id
        ))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM indicator_groups WHERE id = %s", (group_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            indicator = dict(row)
            indicator['code'] = normalize_indicator_code(indicator.get('code'))
            return jsonify({'success': True, 'data': indicator})
        return jsonify({'success': True, 'data': {}})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


@grv_bp.route('/api/company/<int:company_id>/indicator-groups/<int:group_id>', methods=['DELETE'])
def api_delete_indicator_group(company_id: int, group_id: int):
    """Deleta um grupo de indicadores"""
    from database.postgres_helper import connect as pg_connect
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    try:
        # Verificar se tem indicadores associados
        cursor.execute("""
            SELECT COUNT(*) FROM indicators WHERE group_id = %s
        """, (group_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return jsonify({
                'success': False, 
                'message': f'NÃ£o Ã© possÃ­vel excluir. Existem {count} indicador(es) associado(s) a este grupo.'
            }), 400
        
        cursor.execute("""
            DELETE FROM indicator_groups 
            WHERE id = %s AND company_id = %s
        """, (group_id, company_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Grupo excluÃ­do com sucesso'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


# ===== Indicadores =====

@grv_bp.route('/api/company/<int:company_id>/indicators', methods=['GET'])
def api_get_indicators(company_id: int):
    """Lista todos os indicadores da empresa"""
    from database.postgres_helper import connect as pg_connect
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    ensure_indicator_schema(conn)
    
    cursor.execute("""
        SELECT 
            i.*,
            g.code as group_code,
            g.name as group_name,
            p.code as process_code,
            p.name as process_name,
            pr.code as project_code,
            pr.title as project_name
        FROM indicators i
        LEFT JOIN indicator_groups g ON i.group_id = g.id
        LEFT JOIN processes p ON i.process_id = p.id
        LEFT JOIN company_projects pr ON i.project_id = pr.id
        WHERE i.company_id = %s
        ORDER BY i.code
    """, (company_id,))
    
    indicators = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    for indicator in indicators:
        indicator['code'] = normalize_indicator_code(indicator.get('code'))
        if 'group_code' in indicator:
            indicator['group_code'] = normalize_indicator_code(indicator.get('group_code'))
    
    return jsonify({'success': True, 'data': indicators})


@grv_bp.route('/api/company/<int:company_id>/indicators/<int:indicator_id>', methods=['GET'])
def api_get_indicator(company_id: int, indicator_id: int):
    """ObtÃ©m detalhes de um indicador especÃ­fico"""
    from database.postgres_helper import connect as pg_connect
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    ensure_indicator_schema(conn)
    
    cursor.execute("""
        SELECT * FROM indicators 
        WHERE id = %s AND company_id = %s
    """, (indicator_id, company_id))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'success': False, 'message': 'Indicador nÃ£o encontrado'}), 404
    
    indicator = dict(row)
    indicator['code'] = normalize_indicator_code(indicator.get('code'))
    
    return jsonify({'success': True, 'data': indicator})


@grv_bp.route('/api/company/<int:company_id>/processes/<int:process_id>/indicators', methods=['GET'])
def api_get_process_indicators(company_id: int, process_id: int):
    """Lista os indicadores associados a um processo especÃ­fico"""
    from database.postgres_helper import connect as pg_connect
    import json

    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            i.*,
            g.code as group_code,
            g.name as group_name
        FROM indicators i
        LEFT JOIN indicator_groups g ON i.group_id = g.id
        WHERE i.company_id = %s AND i.process_id = %s
        ORDER BY i.code
    """, (company_id, process_id))

    indicator_rows = cursor.fetchall()
    indicators = []

    for row in indicator_rows:
        indicator = dict(row)

        code = indicator.get('code')
        if code:
            indicator['code'] = normalize_indicator_code(code)

        group_code = indicator.get('group_code')
        if group_code:
            indicator['group_code'] = normalize_indicator_code(group_code)

        collaborators_value = indicator.get('collaborators') or ''
        collaborator_entries = []
        if collaborators_value:
            collaborator_ids = []
            try:
                if isinstance(collaborators_value, (list, tuple)):
                    collaborator_ids = [int(value) for value in collaborators_value]
                elif isinstance(collaborators_value, str):
                    collaborators_value = collaborators_value.strip()
                    if collaborators_value:
                        collaborator_ids = json.loads(collaborators_value)
                        if isinstance(collaborator_ids, list):
                            collaborator_ids = [
                                int(item) for item in collaborator_ids
                                if str(item).strip().isdigit()
                            ]
                        else:
                            collaborator_ids = []
                else:
                    collaborator_ids = []
            except (ValueError, json.JSONDecodeError, TypeError):
                if isinstance(collaborators_value, str):
                    collaborator_ids = [
                        int(item) for item in collaborators_value.split(',')
                        if item.strip().isdigit()
                    ]
                else:
                    collaborator_ids = []

            if collaborator_ids:
                placeholders = ",".join("%s" * len(collaborator_ids))
                cursor.execute(
                    f"""
                        SELECT id, name, email 
                        FROM employees 
                        WHERE company_id = %s AND id IN ({placeholders})
                        ORDER BY name
                    """,
                    (company_id, *collaborator_ids)
                )
                collaborator_entries = [dict(item) for item in cursor.fetchall()]

        indicator['collaborators'] = collaborator_entries

        cursor.execute("""
            SELECT 
                g.id,
                g.goal_value,
                g.goal_date,
                g.goal_type,
                g.period_start,
                g.period_end,
                g.evaluation_basis,
                g.status,
                g.notes,
                g.responsible_id,
                e.name as responsible_name
            FROM indicator_goals g
            LEFT JOIN employees e ON g.responsible_id = e.id
            WHERE g.company_id = %s AND g.indicator_id = %s
            ORDER BY COALESCE(g.period_end, g.goal_date) DESC, g.created_at DESC
        """, (company_id, indicator['id']))

        goals = [normalize_goal_row(dict(goal_row)) for goal_row in cursor.fetchall()]
        indicator['goals'] = goals
        indicator['latest_goal'] = goals[0] if goals else None

        indicators.append(indicator)

    conn.close()

    return jsonify({'success': True, 'data': indicators})


@grv_bp.route('/api/company/<int:company_id>/indicators', methods=['POST'])
@auto_log_crud('indicator')
def api_create_indicator(company_id: int):
    """Cria um novo indicador"""
    from database.postgres_helper import connect as pg_connect
    from flask import request
    
    data = request.json
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    try:
        # Gerar cÃ³digo automÃ¡tico
        group_id = data.get('group_id')
        if group_id:
            cursor.execute("""
                SELECT code FROM indicator_groups WHERE id = %s
            """, (group_id,))
            group_row = cursor.fetchone()
            group_code = group_row[0] if group_row else ''
            
            cursor.execute("""
                SELECT COUNT(*) FROM indicators 
                WHERE company_id = %s AND group_id = %s
            """, (company_id, group_id))
            count = cursor.fetchone()[0]
            code = f"{group_code}.{count + 1:03d}"
        else:
            cursor.execute("""
                SELECT client_code FROM companies WHERE id = %s
            """, (company_id,))
            company_row = cursor.fetchone()
            company_code = 'AA'
            if company_row:
                raw_code = (company_row[0] or '').strip()
                if raw_code:
                    company_code = raw_code.upper()
            
            cursor.execute("""
                SELECT COUNT(*) FROM indicators 
                WHERE company_id = %s AND group_id IS NULL
            """, (company_id,))
            count = cursor.fetchone()[0]
            code = f"{company_code}.{count + 1:03d}"
        
        # Processar colaboradores (array para JSON string)
        collaborators = data.get('collaborators', [])
        if isinstance(collaborators, list):
            import json
            collaborators = json.dumps(collaborators)
        
        okr_reference = data.get('okr_reference')
        if isinstance(okr_reference, str):
            okr_reference = okr_reference.strip() or None
        elif okr_reference is not None:
            okr_reference = str(okr_reference)
        else:
            okr_reference = None

        okr_reference_label = data.get('okr_reference_label')
        if isinstance(okr_reference_label, str):
            okr_reference_label = okr_reference_label.strip() or None
        else:
            okr_reference_label = None

        # Processar campos de OKR e Planejamento
        plan_id = data.get('plan_id')
        okr_id = data.get('okr_id')
        okr_level = data.get('okr_level')

        cursor.execute("""
            INSERT INTO indicators 
            (company_id, group_id, code, name, process_id, project_id, 
             department_id, collaborators, unit, formula, polarity, 
             data_source, notes, okr_reference, okr_reference_label,
             plan_id, okr_id, okr_level)
            VALUES (%s, %s, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            group_id,
            code,
            data.get('name'),
            data.get('process_id'),
            data.get('project_id'),
            data.get('department_id'),
            collaborators,
            data.get('unit'),
            data.get('formula'),
            data.get('polarity'),
            data.get('data_source'),
            data.get('notes'),
            okr_reference,
            okr_reference_label,
            plan_id,
            okr_id,
            okr_level
        ))
        
        conn.commit()
        indicator_id = cursor.lastrowid
        
        cursor.execute("SELECT * FROM indicators WHERE id = %s", (indicator_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            indicator = dict(row)
            indicator['code'] = normalize_indicator_code(indicator.get('code'))
            return jsonify({'success': True, 'data': indicator}), 201
        return jsonify({'success': True, 'data': {}}), 201
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


@grv_bp.route('/api/company/<int:company_id>/indicators/<int:indicator_id>', methods=['PUT'])
@auto_log_crud('indicator')
def api_update_indicator(company_id: int, indicator_id: int):
    """Atualiza um indicador"""
    from database.postgres_helper import connect as pg_connect
    from flask import request
    
    data = request.json
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    try:
        # Processar colaboradores (array para JSON string)
        collaborators = data.get('collaborators', [])
        if isinstance(collaborators, list):
            import json
            collaborators = json.dumps(collaborators)
        
        # Processar campos de OKR e Planejamento
        okr_reference = data.get('okr_reference')
        if isinstance(okr_reference, str):
            okr_reference = okr_reference.strip() or None
        elif okr_reference is not None:
            okr_reference = str(okr_reference)
        else:
            okr_reference = None
        
        plan_id = data.get('plan_id')
        okr_id = data.get('okr_id')
        okr_level = data.get('okr_level')

        cursor.execute("""
            UPDATE indicators 
            SET group_id = %s, name = %s, process_id = %s, project_id = %s,
                department_id = %s, collaborators = ?, unit = ?, formula = ?,
                polarity = ?, data_source = ?, notes = ?,
                plan_id = %s, okr_id = %s, okr_level = ?, okr_reference = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND company_id = %s
        """, (
            data.get('group_id'),
            data.get('name'),
            data.get('process_id'),
            data.get('project_id'),
            data.get('department_id'),
            collaborators,
            data.get('unit'),
            data.get('formula'),
            data.get('polarity'),
            data.get('data_source'),
            data.get('notes'),
            plan_id,
            okr_id,
            okr_level,
            okr_reference,
            indicator_id,
            company_id
        ))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM indicators WHERE id = %s", (indicator_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({'success': True, 'data': dict(row)})
        return jsonify({'success': True, 'data': {}})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


@grv_bp.route('/api/company/<int:company_id>/indicators/<int:indicator_id>', methods=['DELETE'])
@auto_log_crud('indicator')
def api_delete_indicator(company_id: int, indicator_id: int):
    """Deleta um indicador"""
    from database.postgres_helper import connect as pg_connect
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    try:
        # Verificar se tem metas associadas
        cursor.execute("""
            SELECT COUNT(*) FROM indicator_goals WHERE indicator_id = %s
        """, (indicator_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return jsonify({
                'success': False, 
                'message': f'NÃ£o Ã© possÃ­vel excluir. Existem {count} meta(s) associada(s) a este indicador.'
            }), 400
        
        cursor.execute("""
            DELETE FROM indicators 
            WHERE id = %s AND company_id = %s
        """, (indicator_id, company_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Indicador excluÃ­do com sucesso'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


# ===== Metas de Indicadores =====

@grv_bp.route('/api/company/<int:company_id>/indicator-goals', methods=['GET'])
def api_get_indicator_goals(company_id: int):
    """Lista todas as metas de indicadores da empresa"""
    from database.postgres_helper import connect as pg_connect
    
    try:
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrão
        cursor = conn.cursor()
        ensure_indicator_goals_schema(conn)
        
        cursor.execute("""
            SELECT 
                g.*,
                i.code as indicator_code,
                i.name as indicator_name,
                e.name as responsible_name
            FROM indicator_goals g
            INNER JOIN indicators i ON g.indicator_id = i.id
            LEFT JOIN employees e ON g.responsible_id = e.id
            WHERE g.company_id = %s
            ORDER BY g.code
        """, (company_id,))
        
        goals = [normalize_goal_row(dict(row)) for row in cursor.fetchall()]
        conn.close()
        
        for goal in goals:
            if 'indicator_code' in goal:
                goal['indicator_code'] = normalize_indicator_code(goal.get('indicator_code'))
        
        return jsonify({'success': True, 'data': goals})
    except Exception as e:
        print(f"Erro ao carregar metas de indicadores: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@grv_bp.route('/api/company/<int:company_id>/indicator-goals/<int:goal_id>', methods=['GET'])
def api_get_indicator_goal(company_id: int, goal_id: int):
    """ObtÃ©m detalhes de uma meta especÃ­fica"""
    from database.postgres_helper import connect as pg_connect
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM indicator_goals 
        WHERE id = %s AND company_id = %s
    """, (goal_id, company_id))
    
    goal = cursor.fetchone()
    conn.close()
    
    if not goal:
        return jsonify({'success': False, 'message': 'Meta nÃ£o encontrada'}), 404
    
    return jsonify({'success': True, 'data': normalize_goal_row(dict(goal))})


@grv_bp.route('/api/company/<int:company_id>/indicator-goals', methods=['POST'])
@auto_log_crud('indicator_goal')
def api_create_indicator_goal(company_id: int):
    """Cria uma nova meta de indicador"""
    from database.postgres_helper import connect as pg_connect
    from flask import request

    data = request.json

    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    ensure_indicator_goals_schema(conn)

    try:
        # Gerar codigo automatico (4 digitos)
        cursor.execute("""
            SELECT COUNT(*) FROM indicator_goals WHERE company_id = %s
        """, (company_id,))
        count = cursor.fetchone()[0]
        code = f"META-{count + 1:04d}"

        indicator_id = data.get('indicator_id')
        try:
            indicator_id = int(indicator_id)
        except (TypeError, ValueError):
            raise ValueError('Indicador obrigatorio nao informado ou invalido.')

        raw_value = data.get('goal_value')
        try:
            goal_value = float(raw_value)
        except (TypeError, ValueError):
            raise ValueError('Valor da meta invalido.')

        goal_type = (data.get('goal_type') or 'single').strip().lower()
        if goal_type not in ALLOWED_GOAL_TYPES:
            raise ValueError('Tipo da meta invalido.')

        period_start = data.get('period_start') or None
        period_end = data.get('period_end') or None
        evaluation_basis = (data.get('evaluation_basis') or '').strip().lower()

        if goal_type == 'single':
            goal_date = data.get('goal_date')
            if not goal_date:
                raise ValueError('Data alvo obrigatoria para metas unicas.')
            period_start = None
            period_end = None
            evaluation_basis = 'value'
        else:
            # Para todos os outros tipos (daily, weekly, monthly, quarterly, biannual, annual)
            if not period_start or not period_end:
                raise ValueError('Informe data de inicio e fim para este tipo de meta.')
            if evaluation_basis not in ALLOWED_GOAL_EVALUATIONS:
                evaluation_basis = 'sum'
            goal_date = data.get('goal_date') or period_end

        if evaluation_basis not in ALLOWED_GOAL_EVALUATIONS:
            raise ValueError('Forma de avaliacao da meta invalida.')

        if period_start and period_end:
            try:
                start_dt = datetime.fromisoformat(period_start)
                end_dt = datetime.fromisoformat(period_end)
                if end_dt < start_dt:
                    raise ValueError('Periodo da meta invalido (data final anterior a inicial).')
            except ValueError as exc:
                raise ValueError('Formato de data invalido para o periodo.') from exc

        responsible_id = data.get('responsible_id')
        if responsible_id in (None, '', 'null'):
            responsible_id = None
        else:
            try:
                responsible_id = int(responsible_id)
            except (TypeError, ValueError):
                responsible_id = None

        status = (data.get('status') or 'active').strip().lower() or 'active'
        notes = data.get('notes')

        cursor.execute("""
            INSERT INTO indicator_goals 
            (company_id, indicator_id, code, goal_type, goal_value, period_start, period_end, goal_date, 
             evaluation_basis, responsible_id, status, notes)
            VALUES (%s, %s, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            indicator_id,
            code,
            goal_type,
            goal_value,
            period_start,
            period_end,
            goal_date,
            evaluation_basis,
            responsible_id,
            status,
            notes
        ))

        conn.commit()
        goal_id = cursor.lastrowid

        cursor.execute("SELECT * FROM indicator_goals WHERE id = %s", (goal_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({'success': True, 'data': normalize_goal_row(dict(row))}), 201
        return jsonify({'success': True, 'data': {}}), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


@grv_bp.route('/api/company/<int:company_id>/indicator-goals/<int:goal_id>', methods=['PUT'])
def api_update_indicator_goal(company_id: int, goal_id: int):
    """Atualiza uma meta de indicador"""
    from database.postgres_helper import connect as pg_connect
    from flask import request

    data = request.json

    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    ensure_indicator_goals_schema(conn)

    try:
        cursor.execute("SELECT id FROM indicator_goals WHERE id = %s AND company_id = %s", (goal_id, company_id))
        if not cursor.fetchone():
            raise ValueError('Meta nao encontrada para atualizacao.')

        indicator_id = data.get('indicator_id')
        try:
            indicator_id = int(indicator_id)
        except (TypeError, ValueError):
            raise ValueError('Indicador obrigatorio nao informado ou invalido.')

        raw_value = data.get('goal_value')
        try:
            goal_value = float(raw_value)
        except (TypeError, ValueError):
            raise ValueError('Valor da meta invalido.')

        goal_type = (data.get('goal_type') or 'single').strip().lower()
        if goal_type not in ALLOWED_GOAL_TYPES:
            raise ValueError('Tipo da meta invalido.')

        period_start = data.get('period_start') or None
        period_end = data.get('period_end') or None
        evaluation_basis = (data.get('evaluation_basis') or '').strip().lower()

        if goal_type == 'single':
            goal_date = data.get('goal_date')
            if not goal_date:
                raise ValueError('Data alvo obrigatoria para metas unicas.')
            period_start = None
            period_end = None
            evaluation_basis = 'value'
        else:
            # Para todos os outros tipos (daily, weekly, monthly, quarterly, biannual, annual)
            if not period_start or not period_end:
                raise ValueError('Informe data de inicio e fim para este tipo de meta.')
            if evaluation_basis not in ALLOWED_GOAL_EVALUATIONS:
                evaluation_basis = 'sum'
            goal_date = data.get('goal_date') or period_end

        if evaluation_basis not in ALLOWED_GOAL_EVALUATIONS:
            raise ValueError('Forma de avaliacao da meta invalida.')

        if period_start and period_end:
            try:
                start_dt = datetime.fromisoformat(period_start)
                end_dt = datetime.fromisoformat(period_end)
                if end_dt < start_dt:
                    raise ValueError('Periodo da meta invalido (data final anterior a inicial).')
            except ValueError as exc:
                raise ValueError('Formato de data invalido para o periodo.') from exc

        responsible_id = data.get('responsible_id')
        if responsible_id in (None, '', 'null'):
            responsible_id = None
        else:
            try:
                responsible_id = int(responsible_id)
            except (TypeError, ValueError):
                responsible_id = None

        status = (data.get('status') or 'active').strip().lower() or 'active'
        notes = data.get('notes')

        cursor.execute("""
            UPDATE indicator_goals 
            SET indicator_id = %s, goal_type = %s, goal_value = ?, period_start = ?, period_end = ?, goal_date = ?,
                evaluation_basis = ?, responsible_id = %s, status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND company_id = %s
        """, (
            indicator_id,
            goal_type,
            goal_value,
            period_start,
            period_end,
            goal_date,
            evaluation_basis,
            responsible_id,
            status,
            notes,
            goal_id,
            company_id
        ))

        conn.commit()

        cursor.execute("SELECT * FROM indicator_goals WHERE id = %s", (goal_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({'success': True, 'data': normalize_goal_row(dict(row))})
        return jsonify({'success': True, 'data': {}})

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


@grv_bp.route('/api/company/<int:company_id>/indicator-goals/<int:goal_id>', methods=['DELETE'])
def api_delete_indicator_goal(company_id: int, goal_id: int):
    """Deleta uma meta de indicador"""
    from database.postgres_helper import connect as pg_connect
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    try:
        # Verificar se tem registros de dados associados
        cursor.execute("""
            SELECT COUNT(*) FROM indicator_data WHERE goal_id = %s
        """, (goal_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return jsonify({
                'success': False, 
                'message': f'NÃ£o Ã© possÃ­vel excluir. Existem {count} registro(s) de dados associado(s) a esta meta.'
            }), 400
        
        cursor.execute("""
            DELETE FROM indicator_goals 
            WHERE id = %s AND company_id = %s
        """, (goal_id, company_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Meta excluÃ­da com sucesso'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


# ===== Registros de Dados =====

@grv_bp.route('/api/company/<int:company_id>/indicator-data', methods=['GET'])
def api_get_indicator_data(company_id: int):
    """Lista todos os registros de dados de indicadores da empresa"""
    from database.postgres_helper import connect as pg_connect
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            d.*,
            g.code as goal_code,
            i.code as indicator_code,
            i.name as indicator_name
        FROM indicator_data d
        INNER JOIN indicator_goals g ON d.goal_id = g.id
        INNER JOIN indicators i ON g.indicator_id = i.id
        WHERE d.company_id = %s
        ORDER BY d.record_date DESC
    """, (company_id,))
    
    data_records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    for record in data_records:
        if 'indicator_code' in record:
            record['indicator_code'] = normalize_indicator_code(record.get('indicator_code'))
    
    return jsonify({'success': True, 'data': data_records})


@grv_bp.route('/api/company/<int:company_id>/indicator-data/<int:data_id>', methods=['GET'])
def api_get_indicator_data_record(company_id: int, data_id: int):
    """ObtÃ©m detalhes de um registro de dados especÃ­fico"""
    from database.postgres_helper import connect as pg_connect
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM indicator_data 
        WHERE id = %s AND company_id = %s
    """, (data_id, company_id))
    
    data_record = cursor.fetchone()
    conn.close()
    
    if not data_record:
        return jsonify({'success': False, 'message': 'Registro nÃ£o encontrado'}), 404
    
    return jsonify({'success': True, 'data': dict(data_record)})


@grv_bp.route('/api/company/<int:company_id>/indicator-data', methods=['POST'])
@auto_log_crud('indicator_data')
def api_create_indicator_data(company_id: int):
    """Cria um novo registro de dados"""
    from database.postgres_helper import connect as pg_connect
    from flask import request
    
    data = request.json
    
    conn = pg_connect()
    # PostgreSQL retorna Row objects por padrão
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO indicator_data 
            (company_id, goal_id, record_date, value, notes)
            VALUES (%s, %s, ?, ?, ?)
        """, (
            company_id,
            data.get('goal_id'),
            data.get('record_date'),
            data.get('value'),
            data.get('notes')
        ))
        
        conn.commit()
        data_id = cursor.lastrowid
        
        cursor.execute("SELECT * FROM indicator_data WHERE id = %s", (data_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({'success': True, 'data': dict(row)}), 201
        return jsonify({'success': True, 'data': {}}), 201
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


@grv_bp.route('/api/company/<int:company_id>/indicator-data/<int:data_id>', methods=['PUT'])
def api_update_indicator_data(company_id: int, data_id: int):
    """Atualiza um registro de dados"""
    from database.postgres_helper import connect as pg_connect
    from flask import request
    
    data = request.json
    
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE indicator_data 
            SET goal_id = %s, record_date = %s, value = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND company_id = %s
        """, (
            data.get('goal_id'),
            data.get('record_date'),
            data.get('value'),
            data.get('notes'),
            data_id,
            company_id
        ))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM indicator_data WHERE id = %s", (data_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({'success': True, 'data': dict(row)})
        return jsonify({'success': True, 'data': {}})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400


@grv_bp.route('/api/company/<int:company_id>/indicator-data/<int:data_id>', methods=['DELETE'])
def api_delete_indicator_data(company_id: int, data_id: int):
    """Deleta um registro de dados"""
    from database.postgres_helper import connect as pg_connect
    
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DELETE FROM indicator_data 
            WHERE id = %s AND company_id = %s
        """, (data_id, company_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Registro excluÃ­do com sucesso'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400
