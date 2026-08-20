import re
import os
import uuid
import json
from io import BytesIO
from datetime import datetime, date
from decimal import Decimal
from flask import request, current_app, session, Response, send_file
from flask_restful import Resource
from flask_login import current_user
from marshmallow import ValidationError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from schemas.process import (
    process_area_schema, process_areas_schema,
    macro_process_schema, macro_processes_schema,
    macro_process_sipoc_snapshot_schema,
    macro_process_sipoc_item_schema,
    macro_process_sipoc_regulatory_item_schema,
    process_schema, processes_schema,
    process_sipoc_snapshot_schema,
    process_sipoc_item_schema,
    process_sipoc_regulatory_item_schema,
    process_routine_schema, process_routines_schema,
    process_step_schema, process_steps_schema,
    process_instance_schema, process_instances_schema,
    process_instance_execution_schema, process_instance_executions_schema,
    process_activity_execution_contract_schema, process_activity_execution_contracts_schema,
)
from models import (
    db,
    ProcessArea,
    MacroProcess,
    Process,
    ProcessBpmnDiagram,
    MacroProcessSipocSnapshot,
    MacroProcessSipocItem,
    MacroProcessSipocRegulatoryItem,
    ProcessSipocSnapshot,
    ProcessSipocItem,
    ProcessSipocRegulatoryItem,
    ProcessRoutine,
    ProcessStep,
    ProcessInstance,
    ProcessInstanceCollaborator,
    ProcessInstanceExecution,
    ProcessActivityExecutionContract,
    Company,
    Employee,
    Indicator,
    IndicatorData,
    ActivityWorkLog,
    Routine,
    Occurrence,
    FinancialAutomationRule,
    ProcessBpmsAnalysis,
    ProcessPortalPublicationGrant,
)
from utils.permissions import get_default_company_id, has_company_full_access, has_permission, permission_required, can_model_process
from utils.sql_execution import execute_formatted_query
from database import get_db
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from services.process_bpmn_service import (
    get_latest_diagram,
    serialize_diagram,
    serialize_flow_snapshot,
    upsert_process_bpmn_diagram,
)
from services.process_pop_media_service import (
    POP_VIDEO_MAX_DURATION_SECONDS,
    coerce_video_duration_seconds,
    save_pop_video,
    save_pop_video_chunk,
    validate_step_video_upload,
)
from utils.indicator_filters import build_indicator_process_filter
from services.process_bpmn_pop_binding_service import (
    open_or_create_pop_activity_for_bpmn,
    serialize_pop_binding,
)
from services.process_pop_copilot_service import suggest_process_pop_step_description
from services.process_execution_runtime_service import (
    advance_instance_after_execution,
    apply_runtime_defaults,
    build_instance_timeline,
    build_runtime_overlay,
    build_runtime_payload,
    calculate_execution_duration_seconds,
    pause_instance,
    resume_instance,
    validate_execution_status,
    validate_instance_status,
)
from services.process_execution_contract_service import (
    apply_contract_defaults,
    resolve_activity_execution_contract,
)
from services.process_execution_mode_service import (
    get_execution_mode_catalog,
    normalize_contract_configs,
    normalize_execution_mode,
)
from services.process_ai_modeler_assistant_service import ProcessAIModelerAssistantService
from services.process_flow_copilot_service import build_process_flow_copilot_analysis
from services.process_sipoc_service import (
    archive_sipoc_snapshot,
    create_regulatory_item,
    create_sipoc_draft,
    create_sipoc_item,
    delete_regulatory_item,
    delete_sipoc_item,
    get_process_sipoc_bundle,
    publish_sipoc_snapshot,
    update_regulatory_item,
    update_sipoc_item,
    update_sipoc_snapshot,
)
from services.process_resource_service import (
    ProcessResourceValidationError,
    build_resource_catalog_bundle,
    build_process_resources_bundle,
    create_process_resource_link,
    create_resource,
    deactivate_process_resource_link,
    deactivate_resource,
    update_process_resource_link,
    update_resource,
)
from services.process_artifact_service import (
    ProcessArtifactValidationError,
    archive_artifact_definition,
    build_activity_artifacts_runtime_payload,
    build_definition_snapshot,
    create_artifact_definition,
    get_artifact_definition,
    get_artifact_execution,
    link_artifact_to_activity,
    list_process_artifact_definitions,
    materialize_activity_artifacts,
    publish_artifact_definition,
    update_artifact_definition,
    update_artifact_execution,
    evaluate_required_artifacts,
)
from services.process_artifact_file_service import resolve_artifact_execution_file, save_artifact_execution_file
from services.process_artifact_pdf_service import generate_process_artifact_pdf_bytes
from services.macro_process_sipoc_service import (
    archive_sipoc_snapshot as archive_macro_process_sipoc_snapshot,
    create_regulatory_item as create_macro_process_regulatory_item,
    create_sipoc_draft as create_macro_process_sipoc_draft,
    create_sipoc_item as create_macro_process_sipoc_item,
    delete_regulatory_item as delete_macro_process_regulatory_item,
    delete_sipoc_item as delete_macro_process_sipoc_item,
    get_macro_process_sipoc_bundle,
    publish_sipoc_snapshot as publish_macro_process_sipoc_snapshot,
    update_regulatory_item as update_macro_process_regulatory_item,
    update_sipoc_item as update_macro_process_sipoc_item,
    update_sipoc_snapshot as update_macro_process_sipoc_snapshot,
)
from services.process_ai_runtime_service import (
    execute_ai_contract,
    should_auto_run_ai_execution,
)
from services.work_journey_sync import sync_process_instance_item
from services.process_assignment_service import (
    employee_can_execute_activity,
    employee_has_assignment_for_instance,
    ensure_execution_assignment,
    extract_assignment_payload,
    sync_execution_assignment_status,
)

PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."
PROCESS_SOURCE_MODULES = ("processo", "process")


def _format_schedule_trigger_value(schedule_type: str | None, schedule_value: str | None, start_time: str | None = None) -> str:
    normalized_type = str(schedule_type or "").strip().lower()
    raw_value = str(schedule_value or "").strip()
    raw_start_time = str(start_time or "").strip()

    if normalized_type == "daily":
        return raw_start_time or raw_value or "--"

    if normalized_type == "weekly":
        return raw_value or raw_start_time or "--"

    if normalized_type == "monthly":
        try:
            day = int(raw_value)
            return f"Dia {day}"
        except (TypeError, ValueError):
            return raw_value or "--"

    if normalized_type == "quarterly":
        try:
            month_in_quarter_raw, day_raw = raw_value.split("-", 1)
            month_in_quarter = int(month_in_quarter_raw)
            day = int(day_raw)
            return f"Mês {month_in_quarter} do tri · Dia {day}"
        except (AttributeError, TypeError, ValueError):
            return raw_value or "--"

    if normalized_type == "yearly":
        try:
            day_raw, month_raw = raw_value.split("/", 1)
            day = int(day_raw)
            month = int(month_raw)
            return f"{day:02d}/{month:02d}"
        except (AttributeError, TypeError, ValueError):
            return raw_value or "--"

    if normalized_type == "specific":
        return raw_value or "--"

    return raw_value or raw_start_time or "--"


def _normalize_macro_owner_from_employee(data: dict, company_id: int | None, *, required: bool = False) -> str | None:
    """Valida que o dono do macroprocesso veio do cadastro de colaboradores do tenant."""
    if not isinstance(data, dict):
        return "Payload inválido."

    owner = str(data.get('owner') or data.get('responsible') or '').strip()
    if not owner:
        return "Selecione um colaborador para Dono do Processo." if required else None

    if not company_id:
        return "company_id is required"

    employee = (
        Employee.query
        .filter(
            Employee.company_id == company_id,
            Employee.name == owner,
            or_(Employee.status == 'active', Employee.status.is_(None)),
        )
        .order_by(Employee.name.asc())
        .first()
    )
    if not employee:
        return "Dono do Processo deve ser um colaborador ativo cadastrado nesta empresa."

    data['owner'] = employee.name
    data.pop('responsible', None)
    return None


def _sync_process_instance_work_journey_item(instance) -> None:
    employee = (
        Employee.query
        .filter_by(company_id=instance.company_id, user_id=getattr(current_user, 'id', None), status='active')
        .first()
    )
    sync_process_instance_item(
        instance.company_id,
        int(instance.id),
        preferred_employee_id=getattr(employee, 'id', None),
    )
    db.session.commit()


def _append_process_instance_put_debug(message: str):
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_path = os.path.join(base_dir, 'request_debug.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"  ProcessInstance PUT Debug: {message}\n")
    except Exception:
        pass


def _build_linked_process_indicator_query(company_id: int, process_id: int):
    return (
        Indicator.query
        .filter_by(company_id=company_id)
        .filter(build_indicator_process_filter(process_id))
    )


def _get_area_in_company(area_id: int, company_id: int):
    return ProcessArea.query.filter_by(id=area_id, company_id=company_id).first()


def _get_macro_in_company(macro_id: int, company_id: int):
    return MacroProcess.query.filter_by(id=macro_id, company_id=company_id).first()

def _instance_visible_to_employee(instance, employee_id):
    if not instance or not employee_id:
        return False
    if instance.owner_employee_id == employee_id or instance.responsible_id == employee_id or instance.executor_id == employee_id:
        return True
    if employee_has_assignment_for_instance(instance.company_id, employee_id, instance.id):
        return True

    collaborators = instance.collaborators_json or []
    if isinstance(collaborators, list):
        for item in collaborators:
            if item == employee_id:
                return True
            if isinstance(item, dict):
                raw_id = item.get('employee_id') or item.get('id')
                try:
                    if raw_id is not None and int(raw_id) == int(employee_id):
                        return True
                except (TypeError, ValueError):
                    continue
    return False


def _user_can_execute_instance_activity(instance, activity_execution_id=None):
    """Autoriza gestores ou executores vinculados, sempre dentro do tenant."""
    if not instance:
        return False
    if has_permission(instance.company_id, 'processes', 'edit'):
        return True
    employee = Employee.query.filter_by(
        user_id=getattr(current_user, 'id', None),
        company_id=instance.company_id,
        status='active',
    ).first()
    if not employee:
        return False
    if activity_execution_id is None:
        return _instance_visible_to_employee(instance, employee.id)
    return employee_can_execute_activity(
        instance.company_id,
        employee.id,
        instance,
        int(activity_execution_id),
    )

def apply_instance_employee_filter(query, company_id):
    from flask_login import current_user

    if not current_user.is_authenticated:
        return query.filter(ProcessInstance.id == None)

    if has_company_full_access(company_id):
        return query

    # Para colaborador, a filtragem final é feita em Python para suportar collaborators_json no PostgreSQL.
    return query


def _resolve_instance_role_employee_id(instance, role):
    """Resolve colaborador principal da instância com fallback para o processo legado."""
    if not instance:
        return None

    role_to_field = {
        'owner': 'owner_employee_id',
        'responsible': 'responsible_id',
        'executor': 'executor_id',
    }
    field_name = role_to_field.get(role)
    if not field_name:
        return None

    direct_value = getattr(instance, field_name, None)
    if direct_value:
        return direct_value

    process_rel = getattr(instance, 'process_rel', None)
    if role in {'owner', 'responsible'} and process_rel:
        fallback_value = getattr(process_rel, field_name, None)
        if fallback_value:
            return fallback_value

    return None

def generate_area_code(company_id, sequence):
    company = Company.query.get(company_id)
    if not company or not company.client_code:
        return f"C.{sequence}"
    return f"{company.client_code}.C.{sequence}"

def generate_macro_code(area_id, sequence):
    area = ProcessArea.query.get(area_id)
    if not area or not area.code:
        return f"?.{sequence}"
    return f"{area.code}.{sequence}"

def generate_process_code(macro_id, sequence):
    macro = MacroProcess.query.get(macro_id)
    if not macro or not macro.code:
        return f"?.{sequence}"
    return f"{macro.code}.{sequence}"

def natural_sort_key(s):
    if s is None:
        s = ""
    # Returns a list of tuples (0, int) for numbers and (1, str) for text
    # This ensures types are always comparable in Python 3
    return [(0, int(text)) if text.isdigit() else (1, text.lower())
            for text in re.split('([0-9]+)', str(s)) if text]

def get_request_company_id():
    from flask import session
    from flask_login import current_user
    from models import Company, Employee
    
    def clean(val):
        if val is None: return None
        s = str(val).strip().lower()
        if s in ('null', 'undefined', 'none', ''): return None
        try:
            # Handle possible float strings like "1.0"
            return int(float(val))
        except (ValueError, TypeError):
            return None

    # 1. Try Query Arg
    cid = clean(request.args.get('company_id'))
    if cid is not None: return cid
    
    # 2. Try JSON Body (if it's a POST/PUT)
    try:
        if request.is_json:
            # use silent=True to avoid 400 if body is empty or not JSON
            # though usually Resource handles this
            data = request.get_json(silent=True)
            if data:
                cid = clean(data.get('company_id'))
                if cid is not None: return cid
    except Exception:
        pass

    # 3. Try Session
    cid = clean(session.get('active_company_id'))
    if cid:
        return cid

    # 4. Fallback: pick a company the user can access
    if current_user.is_authenticated:
        default_company_id = get_default_company_id()
        if default_company_id:
            return default_company_id

    return None


def fetch_pop_routines(process_id: int, include_schedules: bool = False):
    """
    Retorna atividades de POP (process_routines).
    Se include_schedules for True, também inclui dados da tabela routines (legado ou agendamentos).
    """
    if not process_id:
        return []

    conn = None
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        if include_schedules:
            cursor.execute(
                """
                SELECT id, process_id, code, name, description,
                       COALESCE(order_index, 0) AS order_index,
                       bpmn_element_id, bpmn_element_type, bpmn_data_objects,
                       CAST(created_at AS TIMESTAMP) AS created_at,
                       CAST(is_active AS BOOLEAN) AS is_active,
                       'process_routines' AS source,
                       NULL as schedule_type, NULL as schedule_value, 0 as deadline_days, 0 as deadline_hours, NULL as deadline_date
                FROM process_routines
                WHERE process_id = %s AND (is_active = TRUE OR is_active IS NULL)
                UNION ALL
                SELECT id, process_id, NULL as code, name, description,
                       0 AS order_index,
                       NULL AS bpmn_element_id, NULL AS bpmn_element_type, NULL::jsonb AS bpmn_data_objects,
                       CAST(created_at AS TIMESTAMP) AS created_at,
                       CAST(is_active AS BOOLEAN) AS is_active,
                       'routines' AS source,
                       schedule_type, schedule_value, deadline_days, deadline_hours, deadline_date
                FROM routines
                WHERE process_id = %s AND (is_active = TRUE OR is_active IS NULL)
                ORDER BY order_index, id
                """,
                (process_id, process_id),
            )
        else:
            cursor.execute(
                """
                SELECT id, process_id, code, name, description,
                       COALESCE(order_index, 0) AS order_index,
                       bpmn_element_id, bpmn_element_type, bpmn_data_objects,
                       CAST(created_at AS TIMESTAMP) AS created_at,
                       CAST(is_active AS BOOLEAN) AS is_active,
                       'process_routines' AS source,
                       NULL as schedule_type, NULL as schedule_value, 0 as deadline_days, 0 as deadline_hours, NULL as deadline_date
                FROM process_routines
                WHERE process_id = %s AND (is_active = TRUE OR is_active IS NULL)
                ORDER BY order_index, id
                """,
                (process_id,),
            )

        routines = [dict(row) for row in cursor.fetchall()]

        # Ensure JSON serializable dates
        for r in routines:
            for k, v in r.items():
                if isinstance(v, (datetime, date)):
                    r[k] = v.isoformat()
                elif isinstance(v, Decimal):
                    r[k] = float(v)

        routine_ids = [r["id"] for r in routines]

        if routine_ids:
            placeholders = ",".join(["%s"] * len(routine_ids))
            execute_formatted_query(
                cursor,
                """
                SELECT id, routine_id, name, description, expected_result,
                       COALESCE(order_index, 0) AS order_index,
                       image_path, image_width, layout, video_path, video_duration_seconds, video_narration
                FROM process_steps
                WHERE routine_id IN ({placeholders})
                ORDER BY COALESCE(order_index,0), id
                """,
                tuple(routine_ids),
            )
            steps = [
                {
                    "id": row[0],
                    "routine_id": row[1],
                    "name": row[2],
                    "description": row[3],
                    "expected_result": row[4],
                    "order_index": row[5],
                    "image_path": row[6],
                    "image_width": row[7],
                    "layout": row[8],
                    "video_path": row[9],
                    "video_duration_seconds": row[10],
                    "video_narration": row[11],
                }
                for row in cursor.fetchall()
            ]
            steps_map = {}
            for step in steps:
                steps_map.setdefault(step["routine_id"], []).append(step)
            for routine in routines:
                routine["steps"] = steps_map.get(routine["id"], [])
        else:
            for routine in routines:
                routine["steps"] = []

        return routines
    except Exception as e:
        current_app.logger.error(f"Error fetching routines for process {process_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _get_process_with_access(process_id: int, action: str = 'view', sync_session: bool = False):
    process = Process.query.get_or_404(process_id)

    if not current_user.is_authenticated:
        return None

    if not has_permission(process.company_id, 'processes', action):
        return None

    if sync_session:
        session['active_company_id'] = process.company_id

    return process


def _get_process_routine_with_access(routine_id: int, action: str = 'view'):
    """Resolve uma rotina POP no tenant autorizado do usuário."""
    active_company_id = session.get('active_company_id')
    routine_queries = (ProcessRoutine.query, Routine.query)

    if active_company_id:
        for query in routine_queries:
            routine = query.filter_by(id=routine_id, company_id=active_company_id).first()
            if routine and has_permission(active_company_id, 'processes', action):
                return routine

    for query in routine_queries:
        routine = query.filter_by(id=routine_id).first()
        company_id = getattr(routine, 'company_id', None)
        if company_id and has_permission(company_id, 'processes', action):
            return routine

    return None


def _get_process_step_with_access(step_id: int, action: str = 'view'):
    """Resolve o tenant do passo via rotina e nega acesso cruzado por ID."""
    step = ProcessStep.query.get_or_404(step_id)
    if _get_process_routine_with_access(step.routine_id, action=action):
        return step

    return None


def _get_macro_process_with_access(macro_id: int, action: str = 'view', sync_session: bool = False):
    macro = MacroProcess.query.get_or_404(macro_id)

    if not current_user.is_authenticated:
        return None

    if not has_permission(macro.company_id, 'processes', action):
        return None

    if sync_session:
        session['active_company_id'] = macro.company_id

    return macro


def _dump_process_with_bpmn_flow(process: Process) -> dict:
    payload = process_schema.dump(process)
    published_bpmn = get_latest_diagram(
        process_id=process.id,
        company_id=process.company_id,
        status="published",
    )
    payload['bpmn_flow'] = serialize_flow_snapshot(published_bpmn)
    return payload


def _get_process_ids_with_bpmn_flow(company_id: int, process_ids: list[int]) -> set[int]:
    """Retorna processos que possuem diagrama BPMN salvo/publicado para o badge FLX."""
    if not company_id or not process_ids:
        return set()

    rows = (
        db.session.query(ProcessBpmnDiagram.process_id)
        .filter(ProcessBpmnDiagram.company_id == company_id)
        .filter(ProcessBpmnDiagram.process_id.in_(process_ids))
        .filter(ProcessBpmnDiagram.status.in_(["draft", "published"]))
        .filter(ProcessBpmnDiagram.bpmn_xml.isnot(None))
        .distinct()
        .all()
    )
    return {int(row[0]) for row in rows if row and row[0]}


def _get_process_delete_blockers(process: Process) -> dict[str, int]:
    if not process:
        return {}

    company_id = getattr(process, 'company_id', None)
    process_id = getattr(process, 'id', None)
    if not company_id or not process_id:
        return {}

    blocker_queries = {
        'linked_routines_count': (
            Routine.query
            .filter_by(company_id=company_id, process_id=process_id)
            .filter(or_(Routine.is_active.is_(True), Routine.is_active.is_(None)))
        ),
        'linked_instances_count': ProcessInstance.query.filter_by(company_id=company_id, process_id=process_id),
        'linked_indicators_count': _build_linked_process_indicator_query(company_id, process_id),
        'linked_occurrences_count': Occurrence.query.filter_by(company_id=company_id, process_id=process_id),
        'linked_financial_automations_count': FinancialAutomationRule.query.filter_by(company_id=company_id, process_id=process_id),
        'linked_bpms_analyses_count': ProcessBpmsAnalysis.query.filter_by(company_id=company_id, process_id=process_id),
        'linked_portal_grants_count': ProcessPortalPublicationGrant.query.filter_by(company_id=company_id, process_id=process_id),
    }

    blockers = {}
    for key, query in blocker_queries.items():
        count = query.count()
        if count > 0:
            blockers[key] = count

    return blockers


def _unlink_soft_deleted_routines(process: Process) -> None:
    if not process:
        return

    company_id = getattr(process, 'company_id', None)
    process_id = getattr(process, 'id', None)
    if not company_id or not process_id:
        return

    (
        Routine.query
        .filter_by(company_id=company_id, process_id=process_id)
        .filter(Routine.is_active.is_(False))
        .update({Routine.process_id: None}, synchronize_session=False)
    )
    db.session.flush()


def _build_process_delete_conflict(process: Process, blockers: dict[str, int]):
    labels = {
        'linked_routines_count': 'rotina(s) agendada(s)',
        'linked_instances_count': 'instância(s)',
        'linked_indicators_count': 'indicador(es)',
        'linked_occurrences_count': 'ocorrência(s)',
        'linked_financial_automations_count': 'automação(ões) financeira(s)',
        'linked_bpms_analyses_count': 'análise(s) BPMS',
        'linked_portal_grants_count': 'vínculo(s) de acesso no portal de processos',
    }
    blocker_summary = ", ".join(
        f"{count} {labels[key]}"
        for key, count in blockers.items()
    )

    return {
        "error": (
            "Não é possível excluir este processo porque existem registros vinculados: "
            f"{blocker_summary}. Remova ou desvincule esses itens primeiro."
        ),
        "code": "PROCESS_HAS_LINKED_DATA",
        "details": {
            "process_id": getattr(process, 'id', None),
            "company_id": getattr(process, 'company_id', None),
            **blockers,
        }
    }, 409


def fetch_pop_routine_by_id(routine_id: int):
    """Busca uma rotina específica (POP) em ambas as tabelas e anexa passos."""
    if not routine_id:
        return None
    pg = get_db()
    conn = pg._get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, process_id, code, name, description,
               COALESCE(order_index, 0) AS order_index,
               bpmn_element_id, bpmn_element_type, bpmn_data_objects,
               CAST(created_at AS TIMESTAMP) AS created_at,
               CAST(is_active AS BOOLEAN) AS is_active,
               'process_routines' AS source
        FROM process_routines
        WHERE id = %s
        UNION ALL
        SELECT id, process_id, code, name, description,
               COALESCE(order_index, 0) AS order_index,
               NULL AS bpmn_element_id, NULL AS bpmn_element_type, NULL::jsonb AS bpmn_data_objects,
               CAST(created_at AS TIMESTAMP) AS created_at,
               CAST(is_active AS BOOLEAN) AS is_active,
               'routines' AS source
        FROM routines
        WHERE id = %s
        """,
        (routine_id, routine_id),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    routine = dict(row)

    # Ensure JSON serializable dates
    for k, v in routine.items():
        if isinstance(v, (datetime, date)):
            routine[k] = v.isoformat()
        elif isinstance(v, Decimal):
            routine[k] = float(v)

    cursor.execute(
        """
        SELECT id, routine_id, name, description, expected_result,
               COALESCE(order_index, 0) AS order_index,
               image_path, image_width, layout, video_path, video_duration_seconds, video_narration
        FROM process_steps
        WHERE routine_id = %s
        ORDER BY COALESCE(order_index,0), id
        """,
        (routine_id,),
    )
    routine["steps"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return routine


class ProcessInstanceListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, company_id=None):
        if not company_id:
            company_id = get_request_company_id()
        
        if not company_id:
            return [], 200
            
        query = ProcessInstance.query.filter_by(company_id=company_id)
        query = apply_instance_employee_filter(query, company_id)
        
        process_id = request.args.get('process_id')
        if process_id:
            query = query.filter_by(process_id=process_id)
            
        instances = query.all()
        if not has_company_full_access(company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
            if employee:
                instances = [inst for inst in instances if _instance_visible_to_employee(inst, employee.id)]
            else:
                instances = []
        
        # Enrich with normalized collaborators (Owner, Responsible, Executors)
        from models.employee import Employee
        employees = {e.id: e.name for e in Employee.query.filter_by(company_id=company_id).all()}
        
        results = []
        for inst in instances:
            data = process_instance_schema.dump(inst)
            collabs = []
            owner_employee_id = _resolve_instance_role_employee_id(inst, 'owner')
            responsible_employee_id = _resolve_instance_role_employee_id(inst, 'responsible')
            executor_employee_id = _resolve_instance_role_employee_id(inst, 'executor')
            
            # Owner
            if owner_employee_id and owner_employee_id in employees:
                collabs.append({
                    'role': 'owner',
                    'name': employees[owner_employee_id],
                    'id': owner_employee_id
                })
            
            # Responsible
            if responsible_employee_id and responsible_employee_id in employees:
                collabs.append({
                    'role': 'responsible',
                    'name': employees[responsible_employee_id],
                    'id': responsible_employee_id
                })
            
            # Executors
            if executor_employee_id and executor_employee_id in employees:
                collabs.append({
                    'role': 'executor',
                    'name': employees[executor_employee_id],
                    'id': executor_employee_id
                })
            
            # Check collaborators_json
            if inst.collaborators_json and isinstance(inst.collaborators_json, list):
                for c in inst.collaborators_json:
                    if isinstance(c, dict):
                        e_id = c.get('employee_id') or c.get('id')
                        if e_id and e_id in employees:
                            # Avoid duplicates
                            if not any(x['id'] == e_id and x['role'] == c.get('role', 'executor') for x in collabs):
                                collabs.append({
                                    'role': c.get('role', 'executor'),
                                    'name': employees[e_id],
                                    'id': e_id
                                })
                    elif isinstance(c, int):
                         if c in employees:
                             collabs.append({
                                'role': 'executor',
                                'name': employees[c],
                                'id': c
                             })
            
            data['normalized_collaborators'] = collabs
            results.append(data)

        return results, 200

    @permission_required('processes', 'create')
    def post(self, company_id=None):
        try:
            data = request.get_json()
            if not data:
                data = {}
            
            # Determine company_id: URL > Body > Session
            cid = company_id
            if not cid:
                cid = data.get('company_id')
            if not cid:
                cid = get_request_company_id()
            
            if cid:
                data['company_id'] = cid
            
            # Auto-generate instance_code if missing
            if not data.get('instance_code'):
                from models import Company, Process
                
                comp = Company.query.get(cid)
                proc = Process.query.get(data.get('process_id'))
                
                c_code = comp.client_code if comp and comp.client_code else str(cid)
                p_code = proc.code if proc and proc.code else (proc.name[:3].upper() if proc else 'PRC')
                
                # Count existing instances for this company/process
                count = ProcessInstance.query.filter_by(company_id=cid, process_id=data.get('process_id')).count()
                data['instance_code'] = f"{p_code}-{count + 1}"

            # Auto-populate collaborators from Process definition if not provided
            if not data.get('collaborators_json'):
                from models import Employee
                collaborators = []
                
                # Fetch Process Owner
                if proc and proc.owner_employee_id:
                    owner = Employee.query.get(proc.owner_employee_id)
                    if owner:
                        collaborators.append({
                            "id": owner.id,
                            "name": owner.name,
                            "role": "owner",
                            "hours": 0,
                            "actual_hours": 0
                        })
                
                # Fetch Process Responsible
                if proc and proc.responsible_id:
                     resp = Employee.query.get(proc.responsible_id)
                     if resp:
                        # Avoid duplicate if owner is same as responsible
                        if not any(c['id'] == resp.id for c in collaborators):
                            collaborators.append({
                                "id": resp.id,
                                "name": resp.name,
                                "role": "responsible", 
                                "hours": 0,
                                "actual_hours": 0
                            })
                
                # If there is a routine, check for routine specific roles
                if data.get('routine_id'):
                    routine_id = data.get('routine_id')
                    try:
                        pg = get_db()
                        conn = pg._get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT rc.employee_id, e.name 
                            FROM routine_collaborators rc
                            JOIN employees e ON rc.employee_id = e.id
                            WHERE rc.routine_id = %s
                        """, (routine_id,))
                        
                        rows = cursor.fetchall()
                        cursor.close()
                        
                        for row in rows:
                            # Row can be dict or tuple depending on driver/factory
                            # Based on other files, it seems to support dict-like access or valid access
                            if hasattr(row, 'get'): 
                                emp_id = row['employee_id']
                                emp_name = row['name']
                            else:
                                emp_id = row[0]
                                emp_name = row[1]
                                
                            # Avoid duplicates
                            if not any(c['id'] == emp_id for c in collaborators):
                                collaborators.append({
                                    "id": emp_id,
                                    "name": emp_name,
                                    "role": "executor",
                                    "hours": 0,
                                    "actual_hours": 0
                                })
                    except Exception as e:
                        current_app.logger.warning(
                            "Error fetching routine collaborators: %s",
                            e,
                        )

                if collaborators:
                    data['collaborators_json'] = collaborators
                    # Also set the legacy ID columns for compatibility
                    if proc.owner_employee_id:
                        data['owner_employee_id'] = proc.owner_employee_id
                    if proc.responsible_id:
                        data['responsible_id'] = proc.responsible_id

            if data.get('status') is not None:
                data['status'] = validate_instance_status(data.get('status'))

            instance = process_instance_schema.load(data)
            instance.status = validate_instance_status(getattr(instance, 'status', None))
            apply_runtime_defaults(instance)
            db.session.add(instance)
            db.session.commit()
            
            # Populate normalized collaborators table
            if data.get('collaborators_json'):
                from models import ProcessInstanceCollaborator
                for c in data['collaborators_json']:
                    try:
                        collab_obj = ProcessInstanceCollaborator(
                            process_instance_id=instance.id,
                            employee_id=c.get('id') or c.get('employee_id'),
                            role=c.get('role', 'executor'),
                            estimated_hours=c.get('hours', 0),
                            notes=c.get('notes')
                        )
                        db.session.add(collab_obj)
                    except Exception:
                        continue
                db.session.commit()

            return process_instance_schema.dump(instance), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            current_app.logger.exception("Erro ao criar instância de processo process_id=%s company_id=%s", data.get("process_id") if data else None, data.get("company_id") if data else None)
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProcessInstanceResource(Resource):
    @permission_required('processes', 'view')
    def get(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        if not has_company_full_access(instance.company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=instance.company_id).first()
            if not employee or not _instance_visible_to_employee(instance, employee.id):
                return {"error": "Acesso negado à instância."}, 403
        return process_instance_schema.dump(instance), 200

    @permission_required('processes', 'view')
    def put(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        company_id = instance.company_id
        can_edit_company_processes = has_permission(company_id, 'processes', 'edit')
        is_contextual_collaborator_edit = False
        _append_process_instance_put_debug(
            f"enter instance_id={instance_id} company_id={company_id} "
            f"user_id={getattr(current_user, 'id', None)} can_edit_company_processes={can_edit_company_processes}"
        )

        # Colaboradores restritos só podem editar se participarem diretamente
        if not has_company_full_access(company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=instance.company_id).first()
            if not employee:
                _append_process_instance_put_debug("deny: employee_not_found")
                return {"error": "Viewer only: You can only view this process instance."}, 403
            if not _instance_visible_to_employee(instance, employee.id):
                _append_process_instance_put_debug(
                    f"deny: employee_not_in_instance employee_id={employee.id}"
                )
                return {"error": "Viewer only: You can only view this process instance."}, 403
            is_contextual_collaborator_edit = not can_edit_company_processes
        elif not can_edit_company_processes:
            _append_process_instance_put_debug("deny: no_edit_permission_even_with_full_access")
            return {"error": "Permission denied: edit on processes"}, 403

        try:
            data = request.get_json()
            _append_process_instance_put_debug(f"payload={json.dumps(data or {}, ensure_ascii=False)}")

            if is_contextual_collaborator_edit:
                allowed_fields = {
                    'status',
                    'actual_end_date',
                    'completed_at',
                    'notes',
                }
                data_keys = set(data.keys()) if isinstance(data, dict) else set()
                if not data_keys:
                    _append_process_instance_put_debug("deny: empty_payload")
                    return {"error": "Nenhum dado informado para atualizar a instância."}, 400
                disallowed_fields = sorted(data_keys - allowed_fields)
                if disallowed_fields:
                    _append_process_instance_put_debug(
                        f"deny: disallowed_fields={disallowed_fields}"
                    )
                    return {
                        "error": (
                            "Colaborador vinculado pode apenas concluir a instância "
                            "ou registrar observações finais."
                        ),
                        "details": {
                            "blocked_fields": disallowed_fields,
                            "allowed_fields": sorted(allowed_fields),
                        },
                    }, 403

            # Map frontend 'end_date' is now handled by Schema alias

            instance = process_instance_schema.load(data, instance=instance, partial=True)
            instance.status = validate_instance_status(getattr(instance, 'status', None))
            apply_runtime_defaults(instance)
            if instance.status == 'paused' and not instance.paused_at:
                instance.paused_at = datetime.utcnow()
            if instance.status != 'paused':
                instance.paused_at = None
                instance.pause_reason = None if instance.status == 'in_progress' else instance.pause_reason
            db.session.commit()
            current_status = getattr(instance, 'status', None)
            current_actual_end_date = getattr(instance, 'actual_end_date', None)
            _append_process_instance_put_debug(
                f"success: status={current_status} actual_end_date={current_actual_end_date}"
            )
            return process_instance_schema.dump(instance), 200
        except ValidationError as err:
            _append_process_instance_put_debug(f"validation_error={err.messages}")
            return {"errors": err.messages}, 400
        except Exception as e:
            _append_process_instance_put_debug(f"exception={repr(e)}")
            raise

    @permission_required('processes', 'delete')
    def delete(self, instance_id):
        company_id = get_request_company_id()
        if not company_id:
            return {"error": "company_id é obrigatório para excluir instâncias de processo."}, 400

        instance = ProcessInstance.query.filter_by(id=instance_id, company_id=company_id).first_or_404()

        if not has_company_full_access(company_id):
            return {"error": "Viewer only: You cannot delete process instances."}, 403

        try:
            linked_measurements_count = IndicatorData.query.filter_by(
                company_id=company_id,
                process_instance_id=instance.id
            ).count()

            if linked_measurements_count > 0:
                return {
                    "error": (
                        "Não é possível excluir esta instância porque existem "
                        "medições/lançamentos de indicador vinculados a ela."
                    ),
                    "code": "PROCESS_INSTANCE_HAS_INDICATOR_DATA",
                    "details": {
                        "instance_id": instance.id,
                        "company_id": company_id,
                        "linked_measurements_count": linked_measurements_count,
                    }
                }, 409

            ProcessInstanceCollaborator.query.filter_by(
                process_instance_id=instance.id
            ).delete(synchronize_session=False)

            ActivityWorkLog.query.filter_by(
                activity_type='process_instance',
                activity_id=instance.id
            ).delete(synchronize_session=False)

            db.session.delete(instance)
            db.session.commit()
            return {"message": "Process instance deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(
                "Erro ao excluir instância de processo instance_id=%s company_id=%s",
                instance_id,
                company_id,
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProcessInstanceWorkLogResource(Resource):
    @permission_required('processes', 'view')
    def get(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        if not has_company_full_access(instance.company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=instance.company_id).first()
            if not employee or not _instance_visible_to_employee(instance, employee.id):
                return {"error": "Acesso negado à instância."}, 403
        logs = ActivityWorkLog.query.filter_by(
            activity_type='process_instance',
            activity_id=instance_id
        ).order_by(ActivityWorkLog.created_at.desc()).all()
        
        return [log.to_dict() for log in logs], 200

    @permission_required('processes', 'edit')
    def post(self, instance_id):
        try:
            data = request.get_json()
            instance = ProcessInstance.query.get_or_404(instance_id)
            if not has_permission(instance.company_id, 'processes', 'edit'):
                return {"error": "Permission denied: edit on processes"}, 403
            
            # Create Log
            log = ActivityWorkLog(
                activity_type='process_instance',
                activity_id=instance_id,
                employee_id=data.get('employee_id'),
                employee_name=data.get('employee_name'),
                hours_worked=data.get('hours_worked'),
                description=data.get('description'),
                work_date=datetime.strptime(data.get('work_date'), '%Y-%m-%d').date() if data.get('work_date') else date.today()
            )
            
            db.session.add(log)
            
            # Update Instance Total
            current_total = float(instance.actual_hours or 0)
            added = float(log.hours_worked or 0)
            instance.actual_hours = current_total + added
            # Also update worked_hours to keep in sync if they are duplicates
            instance.worked_hours = instance.actual_hours
            
            db.session.commit()
            
            return log.to_dict(), 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessInstanceRuntimeResource(Resource):
    @permission_required('processes', 'view')
    def get(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        if not has_company_full_access(instance.company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=instance.company_id).first()
            if not employee or not _instance_visible_to_employee(instance, employee.id):
                return {"error": "Acesso negado à instância."}, 403
        return build_runtime_payload(instance, execution_id=request.args.get('execution_id', type=int)), 200


class ProcessInstanceTimelineResource(Resource):
    @permission_required('processes', 'view')
    def get(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        if not has_company_full_access(instance.company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=instance.company_id).first()
            if not employee or not _instance_visible_to_employee(instance, employee.id):
                return {"error": "Acesso negado à instância."}, 403
        return build_instance_timeline(instance), 200


class ProcessInstanceOverlayResource(Resource):
    @permission_required('processes', 'view')
    def get(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        if not has_company_full_access(instance.company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=instance.company_id).first()
            if not employee or not _instance_visible_to_employee(instance, employee.id):
                return {"error": "Acesso negado à instância."}, 403
        return build_runtime_overlay(instance), 200


class ProcessInstancePauseResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        if not has_permission(instance.company_id, 'processes', 'edit'):
            return {"error": "Permission denied: edit on processes"}, 403
        payload = request.get_json(silent=True) or {}
        pause_instance(instance=instance, reason=payload.get('reason'))
        db.session.commit()
        return build_runtime_payload(instance), 200


class ProcessInstanceResumeResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        if not has_permission(instance.company_id, 'processes', 'edit'):
            return {"error": "Permission denied: edit on processes"}, 403
        resume_instance(instance=instance)
        db.session.commit()
        return build_runtime_payload(instance), 200


class ProcessInstanceExecutionListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        if not has_company_full_access(instance.company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=instance.company_id).first()
            if not employee or not _instance_visible_to_employee(instance, employee.id):
                return {"error": "Acesso negado à instância."}, 403

        executions = (
            ProcessInstanceExecution.query
            .filter_by(company_id=instance.company_id, process_instance_id=instance.id)
            .order_by(ProcessInstanceExecution.created_at.asc(), ProcessInstanceExecution.id.asc())
            .all()
        )
        return process_instance_executions_schema.dump(executions), 200

    @permission_required('processes', 'view')
    def post(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        if not _user_can_execute_instance_activity(instance):
            return {"error": "Acesso negado à execução desta atividade."}, 403
        try:
            payload = request.get_json(silent=True) or {}
            requested_next_element_id = payload.pop('next_bpmn_element_id', None)
            assignment_payload = extract_assignment_payload(payload)
            contract = resolve_activity_execution_contract(
                company_id=instance.company_id,
                process_id=instance.process_id,
                bpmn_element_id=payload.get('bpmn_element_id'),
                process_routine_id=payload.get('process_routine_id'),
            )
            payload['company_id'] = instance.company_id
            payload['process_instance_id'] = instance.id
            payload['process_id'] = instance.process_id
            payload['process_bpmn_diagram_id'] = payload.get('process_bpmn_diagram_id') or instance.process_bpmn_diagram_id
            payload['status'] = validate_execution_status(payload.get('status'))
            payload = apply_contract_defaults(payload, contract)

            execution = process_instance_execution_schema.load(payload)
            if execution.status == 'in_progress' and not execution.started_at:
                execution.started_at = datetime.utcnow()
            if execution.status == 'completed' and not execution.completed_at:
                execution.completed_at = datetime.utcnow()
            if execution.status == 'paused' and not execution.paused_at:
                execution.paused_at = datetime.utcnow()
            if execution.status == 'waiting_external' and not execution.waiting_since:
                execution.waiting_since = datetime.utcnow()

            db.session.add(execution)
            db.session.flush()
            artifact_executions = materialize_activity_artifacts(
                instance.company_id,
                execution.id,
                commit=False,
            )
            artifact_gate = evaluate_required_artifacts(artifact_executions)
            if execution.status == 'completed' and not artifact_gate.get('activity_may_complete', True):
                execution.status = 'in_progress'
                execution.completed_at = None
                execution.started_at = execution.started_at or datetime.utcnow()
            if execution.bpmn_element_id and execution.status != 'completed':
                instance.current_bpmn_element_id = execution.bpmn_element_id
            if instance.status == 'pending':
                instance.status = 'in_progress'
                if not instance.started_at:
                    instance.started_at = datetime.utcnow()
            if should_auto_run_ai_execution(
                execution_mode=execution.execution_mode,
                status=execution.status,
            ):
                execute_ai_contract(
                    instance=instance,
                    execution=execution,
                    contract=contract,
                    user_id=getattr(current_user, 'id', None),
                )
                artifact_gate = evaluate_required_artifacts(artifact_executions)
                if execution.status == 'completed' and not artifact_gate.get('activity_may_complete', True):
                    execution.status = 'in_progress'
                    execution.completed_at = None
            ensure_execution_assignment(
                company_id=instance.company_id,
                instance=instance,
                execution=execution,
                assignment_payload=assignment_payload,
                assigned_by_user_id=getattr(current_user, 'id', None),
            )
            if execution.status == 'completed':
                advance_instance_after_execution(
                    instance=instance,
                    execution=execution,
                    requested_next_element_id=requested_next_element_id,
                )
            sync_execution_assignment_status(instance.company_id, execution)
            db.session.commit()
            try:
                _sync_process_instance_work_journey_item(instance)
            except Exception:
                db.session.rollback()
                current_app.logger.exception(
                    "Falha ao materializar tarefa operacional da instância %s após criar execution %s",
                    instance.id,
                    execution.id,
                )
            return process_instance_execution_schema.dump(execution), 201
        except ValidationError as err:
            db.session.rollback()
            return {"errors": err.messages}, 400
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Erro ao criar execução de atividade instance_id=%s company_id=%s",
                instance_id,
                instance.company_id,
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessInstanceExecutionResource(Resource):
    @permission_required('processes', 'view')
    def put(self, instance_id, execution_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        execution = ProcessInstanceExecution.query.filter_by(
            id=execution_id,
            process_instance_id=instance.id,
            company_id=instance.company_id,
        ).first_or_404()
        if not _user_can_execute_instance_activity(instance, execution.id):
            return {"error": "Acesso negado à execução desta atividade."}, 403
        try:
            payload = request.get_json(silent=True) or {}
            requested_next_element_id = payload.pop('next_bpmn_element_id', None)
            assignment_payload = extract_assignment_payload(payload)
            run_now = bool(payload.pop('run_now', False))
            if payload.get('status') is not None:
                payload['status'] = validate_execution_status(payload.get('status'))
            if payload.get('execution_mode') is not None:
                payload['execution_mode'] = normalize_execution_mode(payload.get('execution_mode'))
            execution = process_instance_execution_schema.load(payload, instance=execution, partial=True)
            execution.status = validate_execution_status(execution.status)
            execution.execution_mode = normalize_execution_mode(execution.execution_mode)

            if execution.status == 'completed':
                artifact_gate = build_activity_artifacts_runtime_payload(
                    instance.company_id,
                    instance.process_id,
                    execution.bpmn_element_id,
                    activity_execution_id=execution.id,
                ).get('completion') or {}
                if not artifact_gate.get('activity_may_complete', True):
                    raise ProcessArtifactValidationError("Conclua os artefatos obrigatórios antes de finalizar a atividade.")

            if execution.status == 'in_progress' and not execution.started_at:
                execution.started_at = datetime.utcnow()
            if execution.status == 'completed' and not execution.completed_at:
                execution.completed_at = datetime.utcnow()
            if execution.status == 'paused' and not execution.paused_at:
                execution.paused_at = datetime.utcnow()
            if execution.status == 'waiting_external' and not execution.waiting_since:
                execution.waiting_since = datetime.utcnow()
            if execution.status == 'completed' and execution.started_at and not execution.duration_seconds:
                execution.duration_seconds = calculate_execution_duration_seconds(
                    execution.started_at,
                    execution.completed_at,
                )

            if execution.bpmn_element_id and execution.status != 'completed':
                instance.current_bpmn_element_id = execution.bpmn_element_id
            if should_auto_run_ai_execution(
                execution_mode=execution.execution_mode,
                status=execution.status,
                trigger_on_update=True,
                run_now=run_now,
            ):
                contract = resolve_activity_execution_contract(
                    company_id=instance.company_id,
                    process_id=instance.process_id,
                    bpmn_element_id=execution.bpmn_element_id,
                )
                execute_ai_contract(
                    instance=instance,
                    execution=execution,
                    contract=contract,
                    user_id=getattr(current_user, 'id', None),
                )
                artifact_gate = build_activity_artifacts_runtime_payload(
                    instance.company_id,
                    instance.process_id,
                    execution.bpmn_element_id,
                    activity_execution_id=execution.id,
                ).get('completion') or {}
                if execution.status == 'completed' and not artifact_gate.get('activity_may_complete', True):
                    execution.status = 'in_progress'
                    execution.completed_at = None

            ensure_execution_assignment(
                company_id=instance.company_id,
                instance=instance,
                execution=execution,
                assignment_payload=assignment_payload,
                assigned_by_user_id=getattr(current_user, 'id', None),
            )
            if execution.status == 'completed':
                advance_instance_after_execution(
                    instance=instance,
                    execution=execution,
                    requested_next_element_id=requested_next_element_id,
                )
            sync_execution_assignment_status(instance.company_id, execution)
            db.session.commit()
            try:
                _sync_process_instance_work_journey_item(instance)
            except Exception:
                db.session.rollback()
                current_app.logger.exception(
                    "Falha ao materializar tarefa operacional da instância %s após atualizar execution %s",
                    instance.id,
                    execution.id,
                )
            return process_instance_execution_schema.dump(execution), 200
        except ValidationError as err:
            db.session.rollback()
            return {"errors": err.messages}, 400
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Erro ao atualizar execução de atividade execution_id=%s instance_id=%s company_id=%s",
                execution_id,
                instance_id,
                instance.company_id,
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ActivityWorkLogItemResource(Resource):
    @permission_required('processes', 'edit')
    def put(self, log_id):
        try:
            log = ActivityWorkLog.query.get_or_404(log_id)
            data = request.get_json()
            
            # Helper to update instance total if hours changed
            if 'hours_worked' in data:
                old_hours = float(log.hours_worked or 0)
                new_hours = float(data['hours_worked'])
                diff = new_hours - old_hours
                
                if log.activity_type == 'process_instance' and diff != 0:
                    instance = ProcessInstance.query.get(log.activity_id)
                    if instance:
                         current_total = float(instance.actual_hours or 0)
                         instance.actual_hours = current_total + diff
                         instance.worked_hours = instance.actual_hours
            
            if 'employee_id' in data: log.employee_id = data['employee_id']
            if 'employee_name' in data: log.employee_name = data['employee_name']
            if 'hours_worked' in data: log.hours_worked = data['hours_worked']
            if 'description' in data: log.description = data['description']
            if 'work_date' in data: 
                log.work_date = datetime.strptime(data['work_date'], '%Y-%m-%d').date()

            db.session.commit()
            return log.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def delete(self, log_id):
        try:
            log = ActivityWorkLog.query.get_or_404(log_id)
            
            # Update instance total before deleting
            if log.activity_type == 'process_instance':
                instance = ProcessInstance.query.get(log.activity_id)
                if instance:
                    current_total = float(instance.actual_hours or 0)
                    removed = float(log.hours_worked or 0)
                    instance.actual_hours = max(0, current_total - removed)
                    instance.worked_hours = instance.actual_hours
            
            db.session.delete(log)
            db.session.commit()
            return {"message": "Log deleted"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProcessAreaListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, company_id=None):
        try:
            if not company_id:
                company_id = get_request_company_id()
                
            if not company_id:
                return [], 200
                
            query = ProcessArea.query.filter_by(company_id=company_id)
            areas = query.all()
            # Natural sort by code, then order_index, then name
            areas.sort(key=lambda x: (natural_sort_key(x.code), x.order_index or 0, x.name or ""))
            return process_areas_schema.dump(areas), 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in ProcessAreaListResource.get: {e}")
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'create')
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {"error": "No data provided"}, 400
                
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
            
            if not data.get('company_id'):
                return {"error": "company_id is required"}, 400
                
            area = process_area_schema.load(data)
            
            # Generate code automatically
            if area.company_id and area.code:
                area.code = generate_area_code(area.company_id, area.code)
            
            db.session.add(area)
            db.session.commit()
            return process_area_schema.dump(area), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in ProcessAreaListResource.post: {e}")
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProcessAreaResource(Resource):
    @permission_required('processes', 'view')
    def get(self, area_id):
        area = ProcessArea.query.get_or_404(area_id)
        return process_area_schema.dump(area), 200

    @permission_required('processes', 'edit')
    def put(self, area_id):
        area = ProcessArea.query.get_or_404(area_id)
        try:
            data = request.get_json()
            area = process_area_schema.load(data, instance=area, partial=True)
            
            # Recalculate code if sequence changed
            if 'code' in data and area.company_id:
                # Need to check if user passed only the sequence part
                # If it contains dots, it might already be the full code
                if '.' not in str(data['code']):
                    area.code = generate_area_code(area.company_id, data['code'])
            
            db.session.commit()
            return process_area_schema.dump(area), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400

    @permission_required('processes', 'delete')
    def delete(self, area_id):
        area = ProcessArea.query.get_or_404(area_id)
        try:
            db.session.delete(area)
            db.session.commit()
            return {"message": "Process area deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class MacroProcessListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, company_id=None):
        try:
            if not company_id:
                company_id = get_request_company_id()
                
            if not company_id:
                return [], 200
                
            area_id = request.args.get('area_id')
            query = MacroProcess.query.filter_by(company_id=company_id)
            if area_id:
                query = query.filter_by(area_id=area_id)
            macros = query.all()
            # Natural sort by code, fallback to order_index
            macros.sort(key=lambda x: (natural_sort_key(x.code), x.order_index or 0, x.name or ""))
            return macro_processes_schema.dump(macros), 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in MacroProcessListResource.get: {e}")
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'create')
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {"error": "No data provided"}, 400
                
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
            
            if not data.get('company_id'):
                return {"error": "company_id is required"}, 400

            area = _get_area_in_company(data.get('area_id'), int(data.get('company_id')))
            if not area:
                return {"error": "Área de processo não encontrada na empresa informada."}, 400

            owner_error = _normalize_macro_owner_from_employee(data, data.get('company_id'), required=True)
            if owner_error:
                return {"error": owner_error}, 400
                
            macro = macro_process_schema.load(data)
            
            # Generate code automatically
            if macro.area_id and macro.order_index:
                macro.code = generate_macro_code(macro.area_id, macro.order_index)
            
            db.session.add(macro)
            db.session.commit()
            return macro_process_schema.dump(macro), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in MacroProcessListResource.post: {e}")
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class MacroProcessResource(Resource):
    @permission_required('processes', 'view')
    def get(self, macro_id):
        macro = MacroProcess.query.get_or_404(macro_id)
        return macro_process_schema.dump(macro), 200

    @permission_required('processes', 'edit')
    def put(self, macro_id):
        macro = MacroProcess.query.get_or_404(macro_id)
        try:
            data = request.get_json()
            if data and ('owner' in data or 'responsible' in data):
                owner_error = _normalize_macro_owner_from_employee(
                    data, data.get('company_id') or macro.company_id, required=True
                )
                if owner_error:
                    return {"error": owner_error}, 400
            if data and 'area_id' in data:
                target_company_id = int(data.get('company_id') or macro.company_id)
                area = _get_area_in_company(data.get('area_id'), target_company_id)
                if not area:
                    return {"error": "Área de processo não encontrada na empresa informada."}, 400

            macro = macro_process_schema.load(data, instance=macro, partial=True)
            
            # Recalculate code if sequence or area changed
            if 'order_index' in data or 'area_id' in data:
                macro.code = generate_macro_code(macro.area_id, macro.order_index)
                
            db.session.commit()
            return macro_process_schema.dump(macro), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400

    @permission_required('processes', 'delete')
    def delete(self, macro_id):
        macro = MacroProcess.query.get_or_404(macro_id)
        try:
            db.session.delete(macro)
            db.session.commit()
            return {"message": "Macro process deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProcessListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, company_id=None):
        try:
            if not company_id:
                company_id = get_request_company_id()
                
            if not company_id:
                return [], 200
                
            macro_id = request.args.get('macro_id')
            query = Process.query.filter_by(company_id=company_id)
            if macro_id:
                query = query.filter_by(macro_id=macro_id)
            processes = query.all()
            # Natural sort by code, fallback to order_index
            processes.sort(key=lambda x: (natural_sort_key(x.code), x.order_index or 0, x.name or ""))
            
            # Dump basic data
            result = processes_schema.dump(processes)
            process_ids = [process.id for process in processes if getattr(process, 'id', None)]
            bpmn_flow_process_ids = _get_process_ids_with_bpmn_flow(company_id, process_ids)
            
            # Enrich with Routines (RTN/POP) and Indicators (IND) for badges
            for p_data in result:
                pid = p_data.get('id')
                if pid:
                    p_data['has_bpmn_flow'] = pid in bpmn_flow_process_ids
                    # Fetch Routines (unifying `routines` and `process_routines`)
                    p_data['routines'] = fetch_pop_routines(pid)
                    
                    # Fetch Indicators
                    try:
                        inds = (
                            _build_linked_process_indicator_query(company_id, pid)
                            .with_entities(Indicator.id, Indicator.name)
                            .all()
                        )
                        p_data['indicators'] = [{"id": i.id, "name": i.name} for i in inds]
                    except Exception:
                        p_data['indicators'] = []
            
            return result, 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in ProcessListResource.get: {e}")
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'create')
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {"error": "No data provided"}, 400
                
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
            
            if not data.get('company_id'):
                return {"error": "company_id is required"}, 400

            macro = _get_macro_in_company(data.get('macro_id'), int(data.get('company_id')))
            if not macro:
                return {"error": "Macroprocesso não encontrado na empresa informada."}, 400
                
            process = process_schema.load(data)
            
            # Generate code automatically
            if process.macro_id and process.order_index:
                process.code = generate_process_code(process.macro_id, process.order_index)
                
            db.session.add(process)
            db.session.commit()
            return process_schema.dump(process), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in ProcessListResource.post: {e}")
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

from utils.storage import save_file, delete_file

class ProcessResource(Resource):
    @permission_required('processes', 'view')
    def get(self, process_id):
        current_app.logger.info(
            'ProcessResource.get start process_id=%s path=%s user_id=%s active_company_id=%s args=%s',
            process_id,
            request.path,
            getattr(current_user, 'id', None),
            session.get('active_company_id'),
            dict(request.args),
        )

        try:
            process = _get_process_with_access(process_id, action='view', sync_session=True)
            if not process:
                current_app.logger.warning(
                    'ProcessResource.get denied process_id=%s user_id=%s active_company_id=%s',
                    process_id,
                    getattr(current_user, 'id', None),
                    session.get('active_company_id'),
                )
                return {"error": "Permission denied: view on processes"}, 403

            payload = _dump_process_with_bpmn_flow(process)
            current_app.logger.info(
                'ProcessResource.get success process_id=%s company_id=%s macro_id=%s user_id=%s',
                process_id,
                getattr(process, 'company_id', None),
                getattr(process, 'macro_id', None),
                getattr(current_user, 'id', None),
            )
            return payload, 200
        except Exception:
            current_app.logger.exception(
                'ProcessResource.get failure process_id=%s user_id=%s active_company_id=%s',
                process_id,
                getattr(current_user, 'id', None),
                session.get('active_company_id'),
            )
            raise

    @permission_required('processes', 'view')
    def put(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: model on processes"}, 403
        try:
            if request.mimetype == 'multipart/form-data':
                # Handle flow document upload
                file = request.files.get('flow_document')
                if file and file.filename:
                    # Delete old file
                    if process.flow_document:
                        delete_file(process.flow_document)
                    
                    # Save new file
                    process.flow_document = save_file(file, subfolder='flows')
                
                # Update other fields from form data
                if 'name' in request.form: process.name = request.form.get('name')
                if 'description' in request.form: process.description = request.form.get('description')
                # ... other fields if needed
                
                db.session.commit()
                return _dump_process_with_bpmn_flow(process), 200
            else:
                # Handle standard JSON
                data = request.get_json()
                if data and 'macro_id' in data:
                    target_company_id = int(data.get('company_id') or process.company_id)
                    macro = _get_macro_in_company(data.get('macro_id'), target_company_id)
                    if not macro:
                        return {"error": "Macroprocesso não encontrado na empresa informada."}, 400
                process = process_schema.load(data, instance=process, partial=True)
                
                # Recalculate code if sequence or macro changed
                if 'order_index' in data or 'macro_id' in data:
                    process.code = generate_process_code(process.macro_id, process.order_index)
                    
                db.session.commit()
                return _dump_process_with_bpmn_flow(process), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except ValueError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'delete')
    def delete(self, process_id):
        process = _get_process_with_access(process_id, action='delete', sync_session=True)
        if not process:
            return {"error": "Permission denied: delete on processes"}, 403
        try:
            _unlink_soft_deleted_routines(process)
            blockers = _get_process_delete_blockers(process)
            if blockers:
                return _build_process_delete_conflict(process, blockers)

            db.session.delete(process)
            db.session.commit()
            return {"message": "Process deleted successfully"}, 200
        except IntegrityError:
            db.session.rollback()
            current_app.logger.exception(
                "Erro de integridade ao excluir processo process_id=%s company_id=%s",
                process_id,
                getattr(process, 'company_id', None),
            )
            return {
                "error": (
                    "Não foi possível excluir o processo porque ainda existem "
                    "registros vinculados em outras estruturas do sistema."
                ),
                "code": "PROCESS_DELETE_BLOCKED_BY_REFERENCES",
                "details": {
                    "process_id": process_id,
                    "company_id": getattr(process, 'company_id', None),
                }
            }, 409
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(
                "Erro ao excluir processo process_id=%s company_id=%s",
                process_id,
                getattr(process, 'company_id', None),
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProcessBpmnDiagramResource(Resource):
    @permission_required('processes', 'view')
    def get(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403

        status = request.args.get('status')
        if status:
            status = status.strip().lower()
            if status not in {"draft", "published", "archived"}:
                return {"error": "Status BPMN inválido."}, 400

        try:
            diagram = get_latest_diagram(
                process_id=process.id,
                company_id=process.company_id,
                status=status,
            )
            return serialize_diagram(diagram, process), 200
        except Exception:
            current_app.logger.exception(
                "Erro ao carregar BPMN process_id=%s company_id=%s",
                process_id,
                getattr(process, 'company_id', None),
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def put(self, process_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process:
            return {"error": "Permission denied: edit on processes"}, 403

        try:
            payload = request.get_json(silent=True) or {}
            diagram = upsert_process_bpmn_diagram(
                process=process,
                payload=payload,
                user_id=getattr(current_user, 'id', None),
            )
            return serialize_diagram(diagram, process), 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Erro ao salvar BPMN process_id=%s company_id=%s",
                process_id,
                getattr(process, 'company_id', None),
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'view')
    def post(self, process_id):
        return self.put(process_id)


class ProcessBpmnDiagramExportResource(Resource):
    @permission_required('processes', 'view')
    def get(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403

        try:
            status = request.args.get('status')
            if status:
                status = status.strip().lower()
                if status not in {"draft", "published", "archived"}:
                    return {"error": "Status BPMN inválido."}, 400
            diagram = get_latest_diagram(
                process_id=process.id,
                company_id=process.company_id,
                status=status,
            )
            payload = serialize_diagram(diagram, process)
            filename_code = (getattr(process, 'code', None) or f"processo_{process.id}").replace("/", "-").replace("\\", "-")
            filename = f"{filename_code}.bpmn"
            return Response(
                payload.get("bpmn_xml") or "",
                mimetype="application/xml",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except Exception:
            current_app.logger.exception(
                "Erro ao exportar BPMN process_id=%s company_id=%s",
                process_id,
                getattr(process, 'company_id', None),
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessBpmnPopBindingResource(Resource):
    @permission_required('processes', 'view')
    def post(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: model on processes"}, 403

        try:
            payload = request.get_json(silent=True) or {}
            routine, created = open_or_create_pop_activity_for_bpmn(
                process=process,
                payload=payload,
            )
            return serialize_pop_binding(routine, created=created), (201 if created else 200)
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Erro ao abrir/criar POP por BPMN process_id=%s company_id=%s",
                process_id,
                getattr(process, 'company_id', None),
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessActivityExecutionContractListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403

        contracts = (
            ProcessActivityExecutionContract.query
            .filter_by(company_id=process.company_id, process_id=process.id)
            .order_by(
                ProcessActivityExecutionContract.bpmn_element_id.asc().nulls_last(),
                ProcessActivityExecutionContract.version.desc(),
                ProcessActivityExecutionContract.id.desc(),
            )
            .all()
        )
        return process_activity_execution_contracts_schema.dump(contracts), 200

    @permission_required('processes', 'view')
    def post(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: model on processes"}, 403
        try:
            payload = request.get_json(silent=True) or {}
            payload['company_id'] = process.company_id
            payload['process_id'] = process.id
            payload = normalize_contract_configs(payload)

            contract = process_activity_execution_contract_schema.load(payload)
            db.session.add(contract)
            db.session.commit()
            return process_activity_execution_contract_schema.dump(contract), 201
        except ValidationError as err:
            db.session.rollback()
            return {"errors": err.messages}, 400
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Erro ao criar contrato de execução process_id=%s company_id=%s",
                process_id,
                getattr(process, 'company_id', None),
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessActivityExecutionContractResource(Resource):
    @permission_required('processes', 'view')
    def get(self, contract_id):
        contract = ProcessActivityExecutionContract.query.get_or_404(contract_id)
        process = _get_process_with_access(contract.process_id, action='view', sync_session=True)
        if not process or process.company_id != contract.company_id:
            return {"error": "Permission denied: view on processes"}, 403
        return process_activity_execution_contract_schema.dump(contract), 200

    @permission_required('processes', 'view')
    def put(self, contract_id):
        contract = ProcessActivityExecutionContract.query.get_or_404(contract_id)
        process = _get_process_with_access(contract.process_id, action='view', sync_session=True)
        if not process or process.company_id != contract.company_id or not can_model_process(process.company_id):
            return {"error": "Permission denied: model on processes"}, 403
        try:
            payload = request.get_json(silent=True) or {}
            baseline = {
                "execution_mode": payload.get("execution_mode") or contract.execution_mode,
                "interaction_mode": payload.get("interaction_mode") or contract.interaction_mode,
                "ui_schema_json": payload.get("ui_schema_json") if "ui_schema_json" in payload else contract.ui_schema_json,
                "rest_config_json": payload.get("rest_config_json") if "rest_config_json" in payload else contract.rest_config_json,
                "mcp_config_json": payload.get("mcp_config_json") if "mcp_config_json" in payload else contract.mcp_config_json,
                "ai_config_json": payload.get("ai_config_json") if "ai_config_json" in payload else contract.ai_config_json,
                "auto_service_key": payload.get("auto_service_key") or contract.auto_service_key,
            }
            payload = {
                **payload,
                **normalize_contract_configs(baseline),
            }

            contract = process_activity_execution_contract_schema.load(payload, instance=contract, partial=True)
            contract.execution_mode = normalize_execution_mode(contract.execution_mode)
            db.session.commit()
            return process_activity_execution_contract_schema.dump(contract), 200
        except ValidationError as err:
            db.session.rollback()
            return {"errors": err.messages}, 400
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Erro ao atualizar contrato de execução contract_id=%s company_id=%s",
                contract_id,
                contract.company_id,
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'view')
    def delete(self, contract_id):
        contract = ProcessActivityExecutionContract.query.get_or_404(contract_id)
        process = _get_process_with_access(contract.process_id, action='view', sync_session=True)
        if not process or process.company_id != contract.company_id or not can_model_process(process.company_id):
            return {"error": "Permission denied: model on processes"}, 403
        contract.is_active = False
        db.session.commit()
        return {"message": "Contrato de execução desativado com sucesso."}, 200


class ProcessBpmnAiAssistantResource(Resource):
    @permission_required('processes', 'view')
    def get(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403
        flow_copilot = None
        try:
            flow_copilot = build_process_flow_copilot_analysis(
                company_id=process.company_id,
                process_id=process.id,
            )
        except Exception:
            current_app.logger.exception(
                "Erro ao montar análise do copiloto de fluxo process_id=%s company_id=%s",
                process.id,
                process.company_id,
            )
        return {
            "ok": True,
            "catalog": ProcessAIModelerAssistantService.build_catalog(),
            "execution_modes": get_execution_mode_catalog(),
            "flow_copilot_analysis": flow_copilot,
        }, 200

    @permission_required('processes', 'view')
    def post(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: model on processes"}, 403
        try:
            payload = request.get_json(silent=True) or {}
            payload["process_id"] = process.id
            payload["company_id"] = process.company_id
            return ProcessAIModelerAssistantService.suggest(payload), 200
        except ValueError as exc:
            return {"error": str(exc)}, 400
        except Exception:
            current_app.logger.exception(
                "Erro ao sugerir configuração IA BPMN process_id=%s company_id=%s",
                process_id,
                getattr(process, 'company_id', None),
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessArtifactExecutionResource(Resource):
    @permission_required('processes', 'view')
    def get(self, artifact_execution_id):
        company_id = get_request_company_id()
        try:
            artifact_execution = get_artifact_execution(company_id, artifact_execution_id)
            instance = ProcessInstance.query.filter_by(
                id=artifact_execution.process_instance_id,
                company_id=company_id,
            ).first()
            if not instance:
                return {"error": "Execução de processo não encontrada para este tenant."}, 404
            if not has_company_full_access(company_id):
                from models.employee import Employee
                employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
                if not employee or not _instance_visible_to_employee(instance, employee.id):
                    return {"error": "Acesso negado à instância."}, 403
            return artifact_execution.to_dict(), 200
        except ProcessArtifactValidationError as exc:
            return {"error": str(exc)}, 404

    @permission_required('processes', 'view')
    def put(self, artifact_execution_id):
        company_id = get_request_company_id()
        try:
            artifact_execution = get_artifact_execution(company_id, artifact_execution_id)
            instance = ProcessInstance.query.filter_by(
                id=artifact_execution.process_instance_id,
                company_id=company_id,
            ).first()
            if not instance:
                return {"error": "Execução de processo não encontrada para este tenant."}, 404
            if not has_company_full_access(company_id):
                from models.employee import Employee
                employee = Employee.query.filter_by(
                    user_id=current_user.id,
                    company_id=company_id,
                    status='active',
                ).first()
                if not employee or not employee_can_execute_activity(
                    company_id,
                    employee.id,
                    instance,
                    artifact_execution.activity_execution_id,
                ):
                    return {"error": "Acesso negado à execução deste artefato."}, 403
            activity_execution = ProcessInstanceExecution.query.filter_by(
                id=artifact_execution.activity_execution_id,
                process_instance_id=instance.id,
                company_id=company_id,
            ).first()
            if activity_execution:
                activity_execution.performed_by_user_id = getattr(current_user, 'id', None)
                activity_execution.performer_type = activity_execution.performer_type or 'user'
            artifact_execution = update_artifact_execution(
                company_id,
                artifact_execution_id,
                request.get_json(silent=True) or {},
            )
            return artifact_execution.to_dict(), 200
        except ProcessArtifactValidationError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Erro ao atualizar execução de artefato artifact_execution_id=%s company_id=%s",
                artifact_execution_id,
                company_id,
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessArtifactExecutionPdfResource(Resource):
    @permission_required('processes', 'view')
    def get(self, artifact_execution_id):
        company_id = get_request_company_id()
        try:
            artifact_execution = get_artifact_execution(company_id, artifact_execution_id)
            instance = ProcessInstance.query.filter_by(
                id=artifact_execution.process_instance_id,
                company_id=company_id,
            ).first()
            if not instance:
                return {"error": "Execução de processo não encontrada para este tenant."}, 404
            if not has_company_full_access(company_id):
                from models.employee import Employee
                employee = Employee.query.filter_by(
                    user_id=current_user.id,
                    company_id=company_id,
                    status='active',
                ).first()
                if not employee or not _instance_visible_to_employee(instance, employee.id):
                    return {"error": "Acesso negado à instância."}, 403
            if artifact_execution.artifact_type not in {'form', 'check'}:
                return {"error": "A emissão em PDF está disponível para formulário e checklist."}, 400

            pdf_bytes = generate_process_artifact_pdf_bytes(
                artifact_execution,
                instance=instance,
            )
            safe_key = re.sub(r'[^a-zA-Z0-9_-]+', '-', artifact_execution.artifact_key or str(artifact_execution.id)).strip('-')
            return send_file(
                BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'{safe_key or "registro"}-{artifact_execution.id}.pdf',
            )
        except ProcessArtifactValidationError as exc:
            return {"error": str(exc)}, 404
        except Exception:
            current_app.logger.exception(
                "Erro ao emitir PDF do artefato artifact_execution_id=%s company_id=%s",
                artifact_execution_id,
                company_id,
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessArtifactExecutionFileResource(Resource):
    @permission_required('processes', 'view')
    def post(self, artifact_execution_id, file_key=None):
        company_id = get_request_company_id()
        try:
            artifact_execution = get_artifact_execution(company_id, artifact_execution_id)
            instance = ProcessInstance.query.filter_by(
                id=artifact_execution.process_instance_id,
                company_id=company_id,
            ).first()
            if not instance:
                return {"error": "Execução de processo não encontrada para este tenant."}, 404
            if not has_company_full_access(company_id):
                from models.employee import Employee
                employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id, status='active').first()
                if not employee or not employee_can_execute_activity(
                    company_id, employee.id, instance, artifact_execution.activity_execution_id
                ):
                    return {"error": "Acesso negado à execução deste artefato."}, 403
            uploaded = request.files.get('file')
            if not uploaded:
                return {"error": "Arquivo é obrigatório."}, 400
            return save_artifact_execution_file(company_id, artifact_execution_id, uploaded), 201
        except ProcessArtifactValidationError as exc:
            return {"error": str(exc)}, 400

    @permission_required('processes', 'view')
    def get(self, artifact_execution_id, file_key=None):
        company_id = get_request_company_id()
        try:
            artifact_execution = get_artifact_execution(company_id, artifact_execution_id)
            instance = ProcessInstance.query.filter_by(
                id=artifact_execution.process_instance_id,
                company_id=company_id,
            ).first()
            if not instance:
                return {"error": "Execução de processo não encontrada para este tenant."}, 404
            if not has_company_full_access(company_id):
                from models.employee import Employee
                employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id, status='active').first()
                if not employee or not _instance_visible_to_employee(instance, employee.id):
                    return {"error": "Acesso negado à instância."}, 403
            path, original_name, mime_type = resolve_artifact_execution_file(company_id, artifact_execution_id, file_key)
            return send_file(path, mimetype=mime_type, as_attachment=True, download_name=original_name)
        except ProcessArtifactValidationError as exc:
            return {"error": str(exc)}, 404


class ProcessActivityArtifactListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403
        try:
            payload = list_process_artifact_definitions(
                process.company_id,
                process.id,
                artifact_type=request.args.get('artifact_type'),
                bpmn_element_id=request.args.get('bpmn_element_id'),
            )
            return {"artifacts": payload}, 200
        except ProcessArtifactValidationError as exc:
            return {"error": str(exc)}, 400

    @permission_required('processes', 'view')
    def post(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: model on processes"}, 403
        try:
            payload = request.get_json(silent=True) or {}
            definition = create_artifact_definition(
                process.company_id,
                process.id,
                payload,
                user_id=getattr(current_user, 'id', None),
                commit=False,
            )
            link = None
            if payload.get('bpmn_element_id'):
                link = link_artifact_to_activity(
                    process.company_id,
                    process.id,
                    definition.id,
                    {
                        "bpmn_element_id": payload.get('bpmn_element_id'),
                        "display_order": payload.get('display_order', 0),
                        "is_required": payload.get('is_required', False),
                        "completion_policy_json": payload.get('completion_policy_json') or {},
                    },
                    commit=False,
                )
            db.session.commit()
            response = build_definition_snapshot(definition)
            response['link'] = link.to_dict(include_definition=False) if link else None
            return response, 201
        except ProcessArtifactValidationError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Erro ao criar artefato process_id=%s company_id=%s",
                process_id,
                getattr(process, 'company_id', None),
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessActivityArtifactResource(Resource):
    @permission_required('processes', 'view')
    def get(self, artifact_id):
        company_id = get_request_company_id()
        try:
            definition = get_artifact_definition(company_id, artifact_id)
            process = _get_process_with_access(definition.process_id, action='view', sync_session=True)
            if not process or process.company_id != definition.company_id:
                return {"error": "Permission denied: view on processes"}, 403
            return build_definition_snapshot(definition), 200
        except ProcessArtifactValidationError as exc:
            return {"error": str(exc)}, 404

    @permission_required('processes', 'view')
    def put(self, artifact_id):
        company_id = get_request_company_id()
        try:
            definition = get_artifact_definition(company_id, artifact_id)
            process = _get_process_with_access(definition.process_id, action='view', sync_session=True)
            if not process or process.company_id != definition.company_id or not can_model_process(company_id):
                return {"error": "Permission denied: model on processes"}, 403
            definition = update_artifact_definition(
                company_id,
                artifact_id,
                request.get_json(silent=True) or {},
                user_id=getattr(current_user, 'id', None),
                commit=False,
            )
            payload = request.get_json(silent=True) or {}
            if payload.get('bpmn_element_id'):
                link_artifact_to_activity(
                    company_id,
                    definition.process_id,
                    definition.id,
                    {
                        "bpmn_element_id": payload.get('bpmn_element_id'),
                        "display_order": payload.get('display_order', 0),
                        "is_required": payload.get('is_required', False),
                        "completion_policy_json": payload.get('completion_policy_json') or {},
                    },
                    commit=False,
                )
            db.session.commit()
            return build_definition_snapshot(definition), 200
        except ProcessArtifactValidationError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar artefato artifact_id=%s company_id=%s", artifact_id, company_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'view')
    def delete(self, artifact_id):
        company_id = get_request_company_id()
        try:
            definition = get_artifact_definition(company_id, artifact_id)
            process = _get_process_with_access(definition.process_id, action='view', sync_session=True)
            if not process or process.company_id != definition.company_id or not can_model_process(company_id):
                return {"error": "Permission denied: model on processes"}, 403
            archive_artifact_definition(company_id, artifact_id)
            return {"message": "Artefato arquivado com sucesso."}, 200
        except ProcessArtifactValidationError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400


class ProcessActivityArtifactPublishResource(Resource):
    @permission_required('processes', 'view')
    def post(self, artifact_id):
        company_id = get_request_company_id()
        try:
            definition = get_artifact_definition(company_id, artifact_id)
            process = _get_process_with_access(definition.process_id, action='view', sync_session=True)
            if not process or process.company_id != definition.company_id or not can_model_process(company_id):
                return {"error": "Permission denied: model on processes"}, 403
            definition = publish_artifact_definition(
                company_id,
                artifact_id,
                user_id=getattr(current_user, 'id', None),
            )
            return build_definition_snapshot(definition), 200
        except ProcessArtifactValidationError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao publicar artefato artifact_id=%s company_id=%s", artifact_id, company_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class MacroProcessSipocSnapshotResource(Resource):
    @permission_required('processes', 'view')
    def get(self, macro_id):
        macro = _get_macro_process_with_access(macro_id, action='view', sync_session=True)
        if not macro:
            return {"error": "Permission denied: view on processes"}, 403
        try:
            return get_macro_process_sipoc_bundle(macro_process_id=macro.id, company_id=macro.company_id), 200
        except ValueError as exc:
            return {"error": str(exc)}, 404
        except Exception:
            current_app.logger.exception("Erro ao carregar SIPOC do macroprocesso macro_id=%s", macro_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def post(self, macro_id):
        macro = _get_macro_process_with_access(macro_id, action='edit', sync_session=True)
        if not macro or not can_model_process(macro.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            payload = create_macro_process_sipoc_draft(
                macro_process_id=macro.id,
                company_id=macro.company_id,
                user_id=getattr(current_user, 'id', None),
            )
            return payload, 201
        except ValueError as exc:
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao criar rascunho SIPOC do macroprocesso macro_id=%s", macro_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def put(self, macro_id, sipoc_id):
        macro = _get_macro_process_with_access(macro_id, action='edit', sync_session=True)
        if not macro or not can_model_process(macro.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            data = request.get_json(silent=True) or {}
            payload = update_macro_process_sipoc_snapshot(
                macro_process_id=macro.id,
                company_id=macro.company_id,
                sipoc_id=sipoc_id,
                data=data,
                user_id=getattr(current_user, 'id', None),
            )
            return payload, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar SIPOC do macroprocesso macro_id=%s sipoc_id=%s", macro_id, sipoc_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class MacroProcessSipocItemListResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, macro_id, sipoc_id):
        macro = _get_macro_process_with_access(macro_id, action='edit', sync_session=True)
        if not macro or not can_model_process(macro.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            data = request.get_json(silent=True) or {}
            payload = create_macro_process_sipoc_item(
                macro_process_id=macro.id,
                company_id=macro.company_id,
                sipoc_id=sipoc_id,
                data=data,
            )
            return payload, 201
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao criar item SIPOC do macroprocesso macro_id=%s sipoc_id=%s", macro_id, sipoc_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class MacroProcessSipocItemResource(Resource):
    @permission_required('processes', 'edit')
    def put(self, macro_id, sipoc_id, item_id):
        macro = _get_macro_process_with_access(macro_id, action='edit', sync_session=True)
        if not macro or not can_model_process(macro.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            data = request.get_json(silent=True) or {}
            payload = update_macro_process_sipoc_item(
                macro_process_id=macro.id,
                company_id=macro.company_id,
                sipoc_id=sipoc_id,
                item_id=item_id,
                data=data,
            )
            return payload, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar item SIPOC do macroprocesso macro_id=%s sipoc_id=%s item_id=%s", macro_id, sipoc_id, item_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def delete(self, macro_id, sipoc_id, item_id):
        macro = _get_macro_process_with_access(macro_id, action='edit', sync_session=True)
        if not macro or not can_model_process(macro.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            delete_macro_process_sipoc_item(
                macro_process_id=macro.id,
                company_id=macro.company_id,
                sipoc_id=sipoc_id,
                item_id=item_id,
            )
            return {"message": "Item SIPOC removido com sucesso."}, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao remover item SIPOC do macroprocesso macro_id=%s sipoc_id=%s item_id=%s", macro_id, sipoc_id, item_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class MacroProcessSipocRegulatoryItemListResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, macro_id, sipoc_id):
        macro = _get_macro_process_with_access(macro_id, action='edit', sync_session=True)
        if not macro or not can_model_process(macro.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            data = request.get_json(silent=True) or {}
            payload = create_macro_process_regulatory_item(
                macro_process_id=macro.id,
                company_id=macro.company_id,
                sipoc_id=sipoc_id,
                data=data,
            )
            return payload, 201
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao criar item regulatório do macroprocesso macro_id=%s sipoc_id=%s", macro_id, sipoc_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class MacroProcessSipocRegulatoryItemResource(Resource):
    @permission_required('processes', 'edit')
    def put(self, macro_id, sipoc_id, regulatory_item_id):
        macro = _get_macro_process_with_access(macro_id, action='edit', sync_session=True)
        if not macro or not can_model_process(macro.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            data = request.get_json(silent=True) or {}
            payload = update_macro_process_regulatory_item(
                macro_process_id=macro.id,
                company_id=macro.company_id,
                sipoc_id=sipoc_id,
                regulatory_item_id=regulatory_item_id,
                data=data,
            )
            return payload, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar item regulatório do macroprocesso macro_id=%s sipoc_id=%s regulatory_item_id=%s", macro_id, sipoc_id, regulatory_item_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def delete(self, macro_id, sipoc_id, regulatory_item_id):
        macro = _get_macro_process_with_access(macro_id, action='edit', sync_session=True)
        if not macro or not can_model_process(macro.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            delete_macro_process_regulatory_item(
                macro_process_id=macro.id,
                company_id=macro.company_id,
                sipoc_id=sipoc_id,
                regulatory_item_id=regulatory_item_id,
            )
            return {"message": "Item regulatório removido com sucesso."}, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao remover item regulatório do macroprocesso macro_id=%s sipoc_id=%s regulatory_item_id=%s", macro_id, sipoc_id, regulatory_item_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class MacroProcessSipocPublishResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, macro_id, sipoc_id):
        macro = _get_macro_process_with_access(macro_id, action='edit', sync_session=True)
        if not macro or not can_model_process(macro.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            payload = publish_macro_process_sipoc_snapshot(
                macro_process_id=macro.id,
                company_id=macro.company_id,
                sipoc_id=sipoc_id,
                user_id=getattr(current_user, 'id', None),
            )
            return payload, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao publicar SIPOC do macroprocesso macro_id=%s sipoc_id=%s", macro_id, sipoc_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class MacroProcessSipocArchiveResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, macro_id, sipoc_id):
        macro = _get_macro_process_with_access(macro_id, action='edit', sync_session=True)
        if not macro or not can_model_process(macro.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            payload = archive_macro_process_sipoc_snapshot(
                macro_process_id=macro.id,
                company_id=macro.company_id,
                sipoc_id=sipoc_id,
                user_id=getattr(current_user, 'id', None),
            )
            return payload, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao arquivar SIPOC do macroprocesso macro_id=%s sipoc_id=%s", macro_id, sipoc_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessSipocSnapshotResource(Resource):
    @permission_required('processes', 'view')
    def get(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403
        try:
            return get_process_sipoc_bundle(process_id=process.id, company_id=process.company_id), 200
        except ValueError as exc:
            return {"error": str(exc)}, 404
        except Exception:
            current_app.logger.exception("Erro ao carregar SIPOC process_id=%s", process_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def post(self, process_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            payload = create_sipoc_draft(
                process_id=process.id,
                company_id=process.company_id,
                user_id=getattr(current_user, 'id', None),
            )
            return payload, 201
        except ValueError as exc:
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao criar rascunho SIPOC process_id=%s", process_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def put(self, process_id, sipoc_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            data = request.get_json(silent=True) or {}
            payload = update_sipoc_snapshot(
                process_id=process.id,
                company_id=process.company_id,
                sipoc_id=sipoc_id,
                data=data,
                user_id=getattr(current_user, 'id', None),
            )
            return payload, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar SIPOC process_id=%s sipoc_id=%s", process_id, sipoc_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessSipocItemListResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, process_id, sipoc_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            data = request.get_json(silent=True) or {}
            payload = create_sipoc_item(
                process_id=process.id,
                company_id=process.company_id,
                sipoc_id=sipoc_id,
                data=data,
            )
            return payload, 201
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao criar item SIPOC process_id=%s sipoc_id=%s", process_id, sipoc_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessSipocItemResource(Resource):
    @permission_required('processes', 'edit')
    def put(self, process_id, sipoc_id, item_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            data = request.get_json(silent=True) or {}
            payload = update_sipoc_item(
                process_id=process.id,
                company_id=process.company_id,
                sipoc_id=sipoc_id,
                item_id=item_id,
                data=data,
            )
            return payload, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar item SIPOC process_id=%s sipoc_id=%s item_id=%s", process_id, sipoc_id, item_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def delete(self, process_id, sipoc_id, item_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            delete_sipoc_item(
                process_id=process.id,
                company_id=process.company_id,
                sipoc_id=sipoc_id,
                item_id=item_id,
            )
            return {"message": "Item SIPOC removido com sucesso."}, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao remover item SIPOC process_id=%s sipoc_id=%s item_id=%s", process_id, sipoc_id, item_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessSipocRegulatoryItemListResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, process_id, sipoc_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            data = request.get_json(silent=True) or {}
            payload = create_regulatory_item(
                process_id=process.id,
                company_id=process.company_id,
                sipoc_id=sipoc_id,
                data=data,
            )
            return payload, 201
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao criar item regulatório SIPOC process_id=%s sipoc_id=%s", process_id, sipoc_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessSipocRegulatoryItemResource(Resource):
    @permission_required('processes', 'edit')
    def put(self, process_id, sipoc_id, regulatory_item_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            data = request.get_json(silent=True) or {}
            payload = update_regulatory_item(
                process_id=process.id,
                company_id=process.company_id,
                sipoc_id=sipoc_id,
                regulatory_item_id=regulatory_item_id,
                data=data,
            )
            return payload, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar item regulatório SIPOC process_id=%s sipoc_id=%s regulatory_item_id=%s", process_id, sipoc_id, regulatory_item_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def delete(self, process_id, sipoc_id, regulatory_item_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            delete_regulatory_item(
                process_id=process.id,
                company_id=process.company_id,
                sipoc_id=sipoc_id,
                regulatory_item_id=regulatory_item_id,
            )
            return {"message": "Item regulatório removido com sucesso."}, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao remover item regulatório SIPOC process_id=%s sipoc_id=%s regulatory_item_id=%s", process_id, sipoc_id, regulatory_item_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessSipocPublishResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, process_id, sipoc_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            payload = publish_sipoc_snapshot(
                process_id=process.id,
                company_id=process.company_id,
                sipoc_id=sipoc_id,
                user_id=getattr(current_user, 'id', None),
            )
            return payload, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao publicar SIPOC process_id=%s sipoc_id=%s", process_id, sipoc_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessSipocArchiveResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, process_id, sipoc_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process or not can_model_process(process.company_id):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            payload = archive_sipoc_snapshot(
                process_id=process.id,
                company_id=process.company_id,
                sipoc_id=sipoc_id,
                user_id=getattr(current_user, 'id', None),
            )
            return payload, 200
        except ValueError as exc:
            db.session.rollback()
            return {"error": str(exc)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao arquivar SIPOC process_id=%s sipoc_id=%s", process_id, sipoc_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessRoutineListResource(Resource):
    @permission_required('processes', 'view')
    def get(self):
        process_id = request.args.get('process_id', type=int)
        if not process_id:
            return [], 200
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403
        try:
            routines = fetch_pop_routines(process.id)
            return routines, 200
        except Exception as e:
            current_app.logger.exception("Erro ao listar POP routines do processo process_id=%s", process_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'create')
    def post(self):
        try:
            data = request.get_json()
            process_id = data.get('process_id') if data else None
            if process_id:
                proc = _get_process_with_access(process_id, action='create', sync_session=True)
                if not proc:
                    return {"error": "Permission denied: create on processes"}, 403
                if not data.get('company_id'):
                    data['company_id'] = proc.company_id

            routine = process_routine_schema.load(data)
            
            # Ensure company_id is set on object (in case schema ignored it)
            if not getattr(routine, 'company_id', None) and data.get('company_id'):
                 routine.company_id = data.get('company_id')

            # Persistir sempre em process_routines (POP)
            db.session.add(routine)
            db.session.commit()
            resp = process_routine_schema.dump(routine)
            resp["source"] = "process_routines"
            return resp, 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except ValueError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProcessRoutineResource(Resource):
    @permission_required('processes', 'view')
    def get(self, routine_id):
        routine = fetch_pop_routine_by_id(routine_id)
        if routine:
            return routine, 200
        return {"error": "Routine not found"}, 404

    @permission_required('processes', 'edit')
    def put(self, routine_id):
        try:
            data = request.get_json()
            # Tenta atualizar primeiro em process_routines (POP)
            updated = False
            pg = get_db()
            conn = pg._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM process_routines WHERE id = %s", (routine_id,))
            if cursor.fetchone():
                cursor.execute(
                    """
                    UPDATE process_routines
                    SET name = COALESCE(%s, name), 
                        description = COALESCE(%s, description), 
                        code = COALESCE(%s, code), 
                        order_index = COALESCE(%s, order_index), 
                        process_id = COALESCE(%s, process_id),
                        is_active = COALESCE(%s, is_active)
                    WHERE id = %s
                    """,
                    (
                        data.get("name"),
                        data.get("description"),
                        data.get("code"),
                        data.get("order_index"),
                        data.get("process_id"),
                        data.get("is_active"),
                        routine_id,
                    ),
                )
                conn.commit()
                updated = True
            else:
                cursor.execute("SELECT id FROM routines WHERE id = %s", (routine_id,))
                if cursor.fetchone():
                    cursor.execute(
                        """
                        UPDATE routines
                        SET name = COALESCE(%s, name), 
                            description = COALESCE(%s, description), 
                            code = COALESCE(%s, code), 
                            order_index = COALESCE(%s, order_index), 
                            process_id = COALESCE(%s, process_id), 
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (
                            data.get("name"),
                            data.get("description"),
                            data.get("code"),
                            data.get("order_index"),
                            data.get("process_id"),
                            routine_id,
                        ),
                    )
                    conn.commit()
                    updated = True
            conn.close()
            if not updated:
                return {"error": "Routine not found"}, 404
            # Retornar registro atualizado
            routine = fetch_pop_routine_by_id(routine_id)
            if routine:
                return routine, 200
            return {"message": "Rotina atualizada"}, 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            current_app.logger.exception("Erro ao atualizar POP routine routine_id=%s", routine_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'delete')
    def delete(self, routine_id):
        try:
            pg = get_db()
            conn = pg._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM process_routines WHERE id = %s", (routine_id,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE process_routines SET is_active = FALSE WHERE id = %s",
                    (routine_id,),
                )
                conn.commit()
                conn.close()
                return {"message": "Routine deleted successfully"}, 200

            cursor.execute("SELECT id FROM routines WHERE id = %s", (routine_id,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE routines SET is_active = FALSE WHERE id = %s",
                    (routine_id,),
                )
                conn.commit()
                conn.close()
                return {"message": "Routine deleted successfully"}, 200

            conn.close()
            return {"error": "Routine not found"}, 404
        except Exception as e:
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProcessStepListResource(Resource):
    @permission_required('processes', 'view')
    def get(self):
        routine_id = request.args.get('routine_id')
        if not routine_id:
            return [], 200
        if not _get_process_routine_with_access(routine_id, action='view'):
            return {"error": "Permission denied: view on processes"}, 403
            
        query = ProcessStep.query.filter_by(routine_id=routine_id)
        steps = query.order_by(ProcessStep.order_index).all()
        return process_steps_schema.dump(steps), 200

    @permission_required('processes', 'create')
    def post(self):
        try:
            if request.mimetype == 'multipart/form-data':
                # Handle form data (with optional file)
                routine_id = request.form.get('routine_id')
                name = request.form.get('name')
                description = request.form.get('description')
                expected_result = request.form.get('expected_result')
                layout = request.form.get('layout', 'single')
                image_width = request.form.get('image_width', 280)
                order_index = request.form.get('order_index', 0)
                video_duration_seconds = coerce_video_duration_seconds(request.form.get('video_duration_seconds'))
                video_narration = request.form.get('video_narration')
                if not _get_process_routine_with_access(routine_id, action='create'):
                    return {"error": "Permission denied: create on processes"}, 403
                
                step = ProcessStep(
                    routine_id=routine_id,
                    name=name,
                    description=description,
                    expected_result=expected_result,
                    layout=layout,
                    image_width=int(image_width),
                    order_index=int(order_index),
                    video_duration_seconds=video_duration_seconds,
                    video_narration=video_narration,
                )

                file = request.files.get('image')
                if file and file.filename:
                    step.image_path = save_file(file, subfolder='pop')

                video_file = request.files.get('video')
                if video_file and video_file.filename:
                    validate_step_video_upload(
                        video_file,
                        duration_seconds=video_duration_seconds,
                        content_length=request.content_length,
                    )
                    step.video_path = save_pop_video(video_file, subfolder='pop/video')
                
                db.session.add(step)
                db.session.commit()
                return process_step_schema.dump(step), 201
            else:
                # Handle standard JSON
                data = request.get_json()
                routine_id = data.get('routine_id') if data else None
                if not _get_process_routine_with_access(routine_id, action='create'):
                    return {"error": "Permission denied: create on processes"}, 403
                step = process_step_schema.load(data)
                db.session.add(step)
                db.session.commit()
                return process_step_schema.dump(step), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except ValueError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except RequestEntityTooLarge:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProcessStepResource(Resource):
    @permission_required('processes', 'view')
    def get(self, step_id):
        step = _get_process_step_with_access(step_id, action='view')
        if not step:
            return {"error": "Permission denied: view on processes"}, 403
        return process_step_schema.dump(step), 200

    @permission_required('processes', 'edit')
    def put(self, step_id):
        step = _get_process_step_with_access(step_id, action='edit')
        if not step:
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            if request.mimetype == 'multipart/form-data':
                # Handle form data (with optional file)
                if 'name' in request.form: step.name = request.form.get('name')
                if 'description' in request.form: step.description = request.form.get('description')
                if 'expected_result' in request.form: step.expected_result = request.form.get('expected_result')
                if 'layout' in request.form: step.layout = request.form.get('layout')
                if 'image_width' in request.form: step.image_width = int(request.form.get('image_width'))
                if 'order_index' in request.form: step.order_index = int(request.form.get('order_index'))
                if 'video_duration_seconds' in request.form:
                    step.video_duration_seconds = coerce_video_duration_seconds(request.form.get('video_duration_seconds'))
                if 'video_narration' in request.form:
                    step.video_narration = request.form.get('video_narration')
                
                remove_image = request.form.get('remove_image') == '1'
                if remove_image and step.image_path:
                    delete_file(step.image_path)
                    step.image_path = None

                remove_video = request.form.get('remove_video') == '1'
                if remove_video and step.video_path:
                    delete_file(step.video_path)
                    step.video_path = None
                    step.video_duration_seconds = None

                file = request.files.get('image')
                if file and file.filename:
                    # Delete old file
                    if step.image_path:
                        delete_file(step.image_path)
                    
                    step.image_path = save_file(file, subfolder='pop')

                video_file = request.files.get('video')
                if video_file and video_file.filename:
                    validate_step_video_upload(
                        video_file,
                        duration_seconds=step.video_duration_seconds,
                        content_length=request.content_length,
                    )
                    previous_video_path = step.video_path
                    optimized_video_path = save_pop_video(video_file, subfolder='pop/video')
                    step.video_path = optimized_video_path
                    if previous_video_path:
                        delete_file(previous_video_path)
                
                db.session.commit()
                return process_step_schema.dump(step), 200
            else:
                # Handle standard JSON
                data = request.get_json()
                step = process_step_schema.load(data, instance=step, partial=True)
                db.session.commit()
                return process_step_schema.dump(step), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except ValueError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except RequestEntityTooLarge:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar vídeo POP step_id=%s", step_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'delete')
    def delete(self, step_id):
        step = _get_process_step_with_access(step_id, action='delete')
        if not step:
            return {"error": "Permission denied: delete on processes"}, 403
        try:
            if step.image_path:
                delete_file(step.image_path)
            if step.video_path:
                delete_file(step.video_path)
            db.session.delete(step)
            db.session.commit()
            return {"message": "Step deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessStepVideoChunkResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, step_id):
        step = _get_process_step_with_access(step_id, action='edit')
        if not step:
            return {"error": "Permission denied: edit on processes"}, 403

        routine = _get_process_routine_with_access(step.routine_id, action='edit')
        company_id = getattr(routine, 'company_id', None)
        if not company_id:
            return {"error": "Contexto da empresa não encontrado."}, 400

        try:
            chunk = request.files.get('chunk')
            chunk_index = int(request.form.get('chunk_index', -1))
            total_chunks = int(request.form.get('total_chunks', 0))
            total_size = int(request.form.get('total_size', 0))
            duration_seconds = coerce_video_duration_seconds(
                request.form.get('video_duration_seconds')
            )
            validate_step_video_upload(
                type(
                    'ChunkedVideoMetadata',
                    (),
                    {
                        'filename': request.form.get('filename'),
                        'mimetype': request.form.get('mimetype'),
                    },
                )(),
                duration_seconds=duration_seconds,
                content_length=total_size,
            )

            optimized_video_path = save_pop_video_chunk(
                chunk,
                company_id=company_id,
                step_id=step.id,
                upload_id=request.form.get('upload_id'),
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                total_size=total_size,
                original_filename=request.form.get('filename'),
                original_mimetype=request.form.get('mimetype'),
                subfolder='pop/video',
            )
            if not optimized_video_path:
                return {
                    "completed": False,
                    "received_chunk": chunk_index,
                    "total_chunks": total_chunks,
                }, 202

            previous_video_path = step.video_path
            step.video_path = optimized_video_path
            step.video_duration_seconds = duration_seconds
            db.session.commit()
            if previous_video_path:
                delete_file(previous_video_path)
            payload = process_step_schema.dump(step)
            payload['completed'] = True
            return payload, 200
        except ValueError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except RequestEntityTooLarge:
            db.session.rollback()
            raise
        except Exception:
            db.session.rollback()
            current_app.logger.exception(
                "Erro no upload em blocos do vídeo POP step_id=%s company_id=%s",
                step_id,
                company_id,
            )
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessStepAIDraftResource(Resource):
    @permission_required('processes', 'edit')
    def post(self, step_id):
        step = ProcessStep.query.get_or_404(step_id)
        routine = ProcessRoutine.query.filter_by(id=step.routine_id).first()
        if not routine:
            return {"error": "Atividade POP não encontrada para este passo."}, 404
        if not has_permission(routine.company_id, 'processes', 'edit'):
            return {"error": "Permission denied: edit on processes"}, 403

        data = request.get_json(silent=True) or {}
        apply_to_step = bool(data.get('apply_to_step'))

        try:
            payload = suggest_process_pop_step_description(
                company_id=int(routine.company_id),
                step_id=int(step_id),
            )
            draft = dict(payload.get("draft") or {})
            if apply_to_step and draft.get("suggested_description"):
                step.description = draft.get("suggested_description")
                if not step.expected_result and draft.get("suggested_expected_result"):
                    step.expected_result = draft.get("suggested_expected_result")
                db.session.commit()
            return {"ok": True, **payload, "applied": apply_to_step}, 200
        except ValueError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao gerar rascunho IA do passo POP step_id=%s", step_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProcessScheduleListResource(Resource):
    @permission_required('processes', 'view')
    def get(self):
        process_id = request.args.get('process_id', type=int)
        if not process_id:
            return [], 400

        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403

        try:
            pg = get_db()
            conn = pg._get_connection()
            cursor = conn.cursor()

            # Compatível com ambientes legados: consulta apenas colunas estáveis
            # e aplica multi-tenancy explícito por company_id.
            cursor.execute(
                """
                SELECT
                    r.id,
                    r.process_id,
                    r.name,
                    r.description,
                    r.schedule_type,
                    r.schedule_value,
                    r.schedule_value AS trigger_value,
                    r.deadline_days,
                    r.deadline_hours,
                    r.deadline_date,
                    r.created_at
                FROM routines r
                WHERE
                    r.company_id = %s
                    AND r.process_id = %s
                    AND (r.is_active = TRUE OR r.is_active IS NULL)
                ORDER BY r.created_at DESC
                """,
                (process.company_id, process.id),
            )

            routines = [dict(row) for row in cursor.fetchall()]

            if routines:
                routine_ids = [r['id'] for r in routines if r.get('id') is not None]
                collaborators_by_routine = {}

                if routine_ids:
                    placeholders = ",".join(["%s"] * len(routine_ids))
                    execute_formatted_query(
                        cursor,
                        """
                        SELECT
                            rc.routine_id,
                            e.name
                        FROM routine_collaborators rc
                        JOIN routines r ON r.id = rc.routine_id
                        JOIN employees e ON e.id = rc.employee_id
                        WHERE
                            rc.routine_id IN ({placeholders})
                            AND r.company_id = %s
                        ORDER BY e.name
                        """,
                        tuple(routine_ids) + (process.company_id,),
                    )

                    for row in cursor.fetchall():
                        collaborators_by_routine.setdefault(row['routine_id'], []).append(row['name'])

                for r in routines:
                    for k, v in r.items():
                        if isinstance(v, (datetime, date)):
                            r[k] = v.isoformat()
                        elif isinstance(v, Decimal):
                            r[k] = float(v)

                    r['trigger_value'] = _format_schedule_trigger_value(
                        r.get('schedule_type'),
                        r.get('schedule_value'),
                        r.get('start_time'),
                    )
                    r['team'] = collaborators_by_routine.get(r['id'], [])

            return routines, 200
        except Exception as e:
            current_app.logger.exception("Erro ao listar POP routines do processo process_id=%s", process_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500
        finally:
            if 'conn' in locals() and conn:
                conn.close()


class ResourceCatalogListResource(Resource):
    @permission_required('processes', 'view')
    def get(self):
        company_id = request.args.get('company_id', type=int) or get_default_company_id()
        if not company_id or not has_permission(company_id, 'processes', 'view'):
            return {"error": "Permission denied: view on processes"}, 403
        try:
            return build_resource_catalog_bundle(
                company_id,
                resource_type=request.args.get('type'),
                active_only=request.args.get('active_only', '').lower() in ('1', 'true', 'yes'),
            ), 200
        except ProcessResourceValidationError as err:
            return {"error": str(err)}, 400
        except Exception:
            current_app.logger.exception("Erro ao listar catálogo de recursos company_id=%s", company_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def post(self):
        data = request.get_json(silent=True) or {}
        company_id = data.get('company_id') or request.args.get('company_id', type=int) or get_default_company_id()
        if not company_id or not has_permission(int(company_id), 'processes', 'edit'):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            resource = create_resource(int(company_id), data)
            return resource.to_dict(), 201
        except ProcessResourceValidationError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao criar recurso company_id=%s", company_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ResourceCatalogResource(Resource):
    @permission_required('processes', 'edit')
    def put(self, resource_id):
        data = request.get_json(silent=True) or {}
        company_id = data.get('company_id') or request.args.get('company_id', type=int) or get_default_company_id()
        if not company_id or not has_permission(int(company_id), 'processes', 'edit'):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            resource = update_resource(int(company_id), int(resource_id), data)
            return resource.to_dict(), 200
        except ProcessResourceValidationError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar recurso resource_id=%s", resource_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def delete(self, resource_id):
        company_id = request.args.get('company_id', type=int) or get_default_company_id()
        if not company_id or not has_permission(int(company_id), 'processes', 'edit'):
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            resource = deactivate_resource(int(company_id), int(resource_id))
            return resource.to_dict(), 200
        except ProcessResourceValidationError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao inativar recurso resource_id=%s", resource_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessResourceLinkListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, process_id):
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403
        try:
            return build_process_resources_bundle(process.company_id, process.id), 200
        except ProcessResourceValidationError as err:
            return {"error": str(err)}, 400
        except Exception:
            current_app.logger.exception("Erro ao listar recursos do processo process_id=%s", process_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def post(self, process_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process:
            return {"error": "Permission denied: edit on processes"}, 403
        data = request.get_json(silent=True) or {}
        try:
            link = create_process_resource_link(process.company_id, process.id, data)
            return link.to_dict(include_resource=True), 201
        except ProcessResourceValidationError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao vincular recurso ao processo process_id=%s", process_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProcessResourceLinkResource(Resource):
    @permission_required('processes', 'edit')
    def put(self, process_id, link_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process:
            return {"error": "Permission denied: edit on processes"}, 403
        data = request.get_json(silent=True) or {}
        try:
            link = update_process_resource_link(process.company_id, process.id, int(link_id), data)
            return link.to_dict(include_resource=True), 200
        except ProcessResourceValidationError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao atualizar vínculo de recurso link_id=%s", link_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('processes', 'edit')
    def delete(self, process_id, link_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process:
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            link = deactivate_process_resource_link(process.company_id, process.id, int(link_id))
            return link.to_dict(include_resource=True), 200
        except ProcessResourceValidationError as err:
            db.session.rollback()
            return {"error": str(err)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao inativar vínculo de recurso link_id=%s", link_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500
