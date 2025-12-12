import logging
logger = logging.getLogger(__name__)

"""
Service para My Work - Lógica de negócio
Gerencia atividades pessoais, de equipe e da empresa
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Any, Optional, Sequence, Tuple, Set
import json

from database.postgres_helper import connect as pg_connect
from utils.project_activity_utils import normalize_project_activities

DELIVERY_TAGS = [
    "open",
    "completed",
]

TEAM_DEFAULT_WEEKLY_HOURS = 40.0
RECENT_ACTIVITY_DAYS = 30
_CLOSED_STATUSES = {"completed", "done", "cancelled", "canceled", "archived"}


def _activity_delivery_category(activity: Dict[str, Any]) -> str:
    """Return the simplified delivery category for an activity."""
    status = (activity.get("status") or "").lower()
    return "completed" if status in _CLOSED_STATUSES else "open"


def _activity_matches_delivery_filter(
    activity: Dict[str, Any], tags: Sequence[str]
) -> bool:
    """Check if an activity matches at least one delivery filter tag."""
    if not tags:
        return True
    return _activity_delivery_category(activity) in tags


def get_employee_from_user(user_id: int) -> Optional[int]:
    """
    Mapeia user_id para employee_id

    EstratÃ©gia:
    1. Busca direta por user_id (relacionamento FK)
    2. Fallback: busca por email (para dados legados)

    Args:
        user_id: ID do usuÃ¡rio logado

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
            cursor.execute(
                """
                SELECT id FROM employees 
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
            """,
                (user.email,),
            )
            row = cursor.fetchone()

            if row:
                employee_id = row[0]

                # Auto-vincular para prÃ³ximas consultas
                try:
                    cursor.execute(
                        """
                        UPDATE employees 
                        SET user_id = %s 
                        WHERE id = %s AND user_id IS NULL
                    """,
                        (user_id, employee_id),
                    )
                    conn.commit()
                    logger.info(
                        f"âœ… Auto-vinculado: User #{user_id} -> Employee #{employee_id}"
                    )
                except Exception as exc:
                    conn.rollback()

                conn.close()
                return employee_id

        conn.close()
        return None

    except Exception as e:
        logger.info(f"âŒ Erro ao mapear user_id para employee_id: {e}")
        conn.close()
        return None


_EMPLOYEE_HAS_IS_DELETED_COLUMN: Optional[bool] = None
_PROJECT_ACTIVITIES_TABLE_EXISTS: Optional[bool] = None
_PROCESS_COLLAB_TABLE_EXISTS: Optional[bool] = None


def _build_employee_active_filter(cursor) -> str:
    """Return SQL snippet that filters out deleted/inactive employees."""
    global _EMPLOYEE_HAS_IS_DELETED_COLUMN

    if _EMPLOYEE_HAS_IS_DELETED_COLUMN is None:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'employees'
              AND column_name = 'is_deleted'
            LIMIT 1
            """
        )
        _EMPLOYEE_HAS_IS_DELETED_COLUMN = cursor.fetchone() is not None

    if _EMPLOYEE_HAS_IS_DELETED_COLUMN:
        return "AND COALESCE(e.is_deleted, FALSE) = FALSE"

    # Fallback for schemas sem coluna is_deleted
    return "AND (e.status IS NULL OR LOWER(e.status) <> 'inactive')"


def _project_activities_table_available(cursor) -> bool:
    """Detecta se a tabela project_activities existe no schema atual."""
    global _PROJECT_ACTIVITIES_TABLE_EXISTS
    if _PROJECT_ACTIVITIES_TABLE_EXISTS is None:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'project_activities'
            )
            """
        )
        row = cursor.fetchone()
        if isinstance(row, dict):
            exists = list(row.values())[0]
        else:
            exists = row[0] if row else False
        _PROJECT_ACTIVITIES_TABLE_EXISTS = bool(exists)
    return bool(_PROJECT_ACTIVITIES_TABLE_EXISTS)


def _process_collaborators_table_available(cursor) -> bool:
    """Detecta se process_instance_collaborators está disponível."""
    global _PROCESS_COLLAB_TABLE_EXISTS
    if _PROCESS_COLLAB_TABLE_EXISTS is None:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'process_instance_collaborators'
            )
            """
        )
        row = cursor.fetchone()
        if isinstance(row, dict):
            exists = list(row.values())[0]
        else:
            exists = row[0] if row else False
        _PROCESS_COLLAB_TABLE_EXISTS = bool(exists)
    return bool(_PROCESS_COLLAB_TABLE_EXISTS)


def get_user_employees(user_id: int) -> List[Dict[str, Any]]:
    """Return companies/employees associated with a user.

    First tries the explicit FK `employees.user_id`, and if nothing is found it
    falls back to matching by e-mail (covers legacy records that still lack
    the user_id linkage).
    """
    conn = pg_connect()
    cursor = conn.cursor()

    def _fetch_by_user_id() -> List[tuple]:
        cursor.execute(
            f"""
            SELECT e.id,
                   e.name,
                   e.email,
                   e.company_id,
                   c.name AS company_name,
                   c.client_code AS company_code
            FROM employees e
            LEFT JOIN companies c ON c.id = e.company_id
            WHERE e.user_id = %s
              {_build_employee_active_filter(cursor)}
            """,
            (user_id,),
        )
        return cursor.fetchall()

    def _fetch_by_email(email: str) -> List[tuple]:
        cursor.execute(
            f"""
            SELECT e.id,
                   e.name,
                   e.email,
                   e.company_id,
                   c.name AS company_name,
                   c.client_code AS company_code
            FROM employees e
            LEFT JOIN companies c ON c.id = e.company_id
            WHERE LOWER(TRIM(e.email)) = LOWER(TRIM(%s))
              {_build_employee_active_filter(cursor)}
            """,
            (email,),
        )
        return cursor.fetchall()

    try:
        rows = _fetch_by_user_id()
        if not rows:
            from models.user import User  # Import lazily to avoid circular refs

            user = User.query.get(user_id)
            if user and user.email:
                rows = _fetch_by_email(user.email)

        companies: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            employee_id, employee_name, employee_email, company_id, company_name, company_code = row
            if not company_id:
                # Ignore orphan employees that are not linked to a company yet
                continue

            companies[company_id] = {
                "company_id": company_id,
                "company_name": company_name or "Empresa sem nome",
                "company_code": company_code,
                "employee_id": employee_id,
                "employee_name": employee_name,
                "employee_email": employee_email,
            }

        return list(companies.values())
    except Exception:
        raise
    finally:
        conn.close()


def get_filter_options(user_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Return company, collaborator, project and process directories for filters.
    
    Regras por role:
    - admin: vê todas as empresas e todos os colaboradores
    - client: vê apenas empresas vinculadas e seus colaboradores
    - collaborator: vê apenas empresas vinculadas, mas apenas ele mesmo nos colaboradores
    """
    from models.user import User
    
    # Obter role do usuário
    user = User.query.get(user_id)
    if not user:
        return {
            "companies": [],
            "collaborators": [],
            "projects": [],
            "processes": [],
        }
    
    user_role = user.role
    if user_role == 'consultant':
        user_role = 'collaborator'  # Normalizar legado
    
    # Admin: buscar todas as empresas
    if user_role == 'admin':
        from models.company import Company
        all_companies = Company.query.order_by(Company.name).all()
        unique_companies = [
            {
                "company_id": c.id,
                "company_name": c.name,
                "company_code": getattr(c, "client_code", None),
            }
            for c in all_companies
        ]
        company_ids = [c.id for c in all_companies]
    else:
        # Client e Collaborator: apenas empresas vinculadas
        base_companies = get_user_employees(user_id)
        unique_companies: List[Dict[str, Any]] = []
        seen_ids = set()

        for company in base_companies:
            company_id = company.get("company_id")
            if not company_id or company_id in seen_ids:
                continue
            seen_ids.add(company_id)
            unique_companies.append(
                {
                    "company_id": company_id,
                    "company_name": company.get("company_name") or "Empresa",
                    "company_code": company.get("company_code"),
                }
            )

        company_ids = [item["company_id"] for item in unique_companies]

    result = {
        "companies": unique_companies,
        "collaborators": [],
        "projects": [],
        "processes": [],
    }

    if not company_ids:
        return result

    conn = pg_connect()
    cursor = conn.cursor()
    try:
        # Collaborator: retorna apenas ele mesmo nos colaboradores
        if user_role == 'collaborator':
            employee_id = get_employee_from_user(user_id)
            if employee_id:
                from models.employee import Employee
                employee = Employee.query.get(employee_id)
                if employee:
                    result["collaborators"] = [
                        {
                            "id": employee.id,
                            "name": employee.name,
                            "email": employee.email,
                            "company_id": employee.company_id,
                            "company_name": employee.company.name if employee.company else "Empresa",
                        }
                    ]
        else:
            # Admin e Client: todos os colaboradores das empresas
            result["collaborators"] = _fetch_collaborator_directory(cursor, company_ids)
        
        result["projects"] = _fetch_project_directory(cursor, company_ids)
        result["processes"] = _fetch_process_directory(cursor, company_ids)
        return result
    finally:
        conn.close()


def _fetch_collaborator_directory(cursor, company_ids: List[int]) -> List[Dict[str, Any]]:
    if not company_ids:
        return []

    placeholders = ",".join(["%s"] * len(company_ids))
    active_filter = _build_employee_active_filter(cursor)
    cursor.execute(
        f"""
        SELECT e.id,
               e.name,
               e.email,
               e.company_id,
               c.name AS company_name
        FROM employees e
        LEFT JOIN companies c ON c.id = e.company_id
        WHERE e.company_id IN ({placeholders})
          {active_filter}
        ORDER BY c.name, e.name
        """,
        tuple(company_ids),
    )

    collaborators = []
    for row in cursor.fetchall():
        collaborator_id = row[0]
        if collaborator_id is None:
            continue
        collaborators.append(
            {
                "id": collaborator_id,
                "name": row[1] or "Colaborador",
                "email": row[2],
                "company_id": row[3],
                "company_name": row[4],
            }
        )
    return collaborators


def _fetch_project_directory(cursor, company_ids: List[int]) -> List[Dict[str, Any]]:
    if not company_ids:
        return []

    placeholders = ",".join(["%s"] * len(company_ids))
    projects = []
    try:
        cursor.execute(
            f"""
            SELECT cp.id,
                   cp.title,
                   cp.code,
                   cp.company_id,
                   c.name AS company_name,
                   c.client_code AS company_code
            FROM company_projects cp
            LEFT JOIN companies c ON c.id = cp.company_id
            WHERE cp.company_id IN ({placeholders})
            ORDER BY c.name, cp.code NULLS LAST, cp.title
            """,
            tuple(company_ids),
        )
        rows = cursor.fetchall() or []
        for row in rows:
            row_dict = dict(row)
            project_id = row_dict.get("id")
            if project_id is None:
                continue
            code = row_dict.get("code")
            if isinstance(code, str):
                code = code.strip() or None
            projects.append(
                {
                    "id": project_id,
                    "title": row_dict.get("title") or "Projeto sem título",
                    "code": code,
                    "company_id": row_dict.get("company_id"),
                    "company_name": row_dict.get("company_name"),
                    "company_code": row_dict.get("company_code"),
                }
            )
        return projects
    except Exception as exc:
        logger.warning("Fallback project directory (sem código): %s", exc)
        cursor.execute(
            f"""
            SELECT cp.id,
                   cp.title,
                   cp.company_id,
                   c.name AS company_name
            FROM company_projects cp
            LEFT JOIN companies c ON c.id = cp.company_id
            WHERE cp.company_id IN ({placeholders})
            ORDER BY c.name, cp.title
            """,
            tuple(company_ids),
        )
        rows = cursor.fetchall() or []
        for row in rows:
            row_dict = dict(row)
            project_id = row_dict.get("id")
            if project_id is None:
                continue
            projects.append(
                {
                    "id": project_id,
                    "title": row_dict.get("title") or "Projeto sem título",
                    "company_id": row_dict.get("company_id"),
                    "company_name": row_dict.get("company_name"),
                }
            )
        return projects


def _build_in_clause(values: Sequence[int], prefix: str) -> Tuple[str, Dict[str, int]]:
    placeholders = []
    params: Dict[str, int] = {}
    for idx, value in enumerate(values):
        key = f"{prefix}_{idx}"
        placeholders.append(f":{key}")
        params[key] = value
    clause = ", ".join(placeholders) if placeholders else ""
    return clause, params


def _normalize_identity_value(value: Any) -> Optional[str]:
    """Normalize textual identifiers (names/emails) for comparisons."""
    if value in (None, "", False):
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    normalized = " ".join(text.split())
    return normalized or None


def _build_employee_lookup(
    cursor, employee_ids: Set[int]
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Set[int]]]:
    """Return directory (id -> info) and lookup (normalized string -> ids)."""
    if not employee_ids:
        return {}, {}

    placeholders = ",".join(["%s"] * len(employee_ids))
    cursor.execute(
        f"""
        SELECT id, name, email
        FROM employees
        WHERE id IN ({placeholders})
        """,
        tuple(employee_ids),
    )

    directory: Dict[int, Dict[str, Any]] = {}
    lookup: Dict[str, Set[int]] = {}
    for row in cursor.fetchall() or []:
        emp_id = row[0]
        directory[emp_id] = {"name": row[1], "email": row[2]}
        for value in (row[1], row[2]):
            key = _normalize_identity_value(value)
            if not key:
                continue
            lookup.setdefault(key, set()).add(emp_id)
    return directory, lookup


def _build_employee_lookup_by_companies(
    cursor, company_ids: List[int]
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Set[int]]]:
    """Return directory and lookup for ALL employees in specified companies."""
    if not company_ids:
        return {}, {}

    placeholders = ",".join(["%s"] * len(company_ids))
    cursor.execute(
        f"""
        SELECT id, name, email
        FROM employees
        WHERE company_id IN ({placeholders})
        AND status = 'active'
        """,
        tuple(company_ids),
    )

    directory: Dict[int, Dict[str, Any]] = {}
    lookup: Dict[str, Set[int]] = {}
    for row in cursor.fetchall() or []:
        emp_id = row[0]
        directory[emp_id] = {"name": row[1], "email": row[2]}
        for value in (row[1], row[2]):
            key = _normalize_identity_value(value)
            if not key:
                continue
            lookup.setdefault(key, set()).add(emp_id)
    return directory, lookup


def _match_employee_from_lookup(
    raw_value: Any, lookup: Dict[str, Set[int]]
) -> Optional[int]:
    """Resolve employee id from textual identifier."""
    if not lookup or raw_value is None:
        return None

    if isinstance(raw_value, (int, float)):
        try:
            candidate = int(raw_value)
            return candidate
        except (TypeError, ValueError):
            return None

    text = _normalize_identity_value(raw_value)
    if not text:
        return None
    candidates = lookup.get(text)
    if not candidates:
        return None
    # Deterministic selection
    return sorted(candidates)[0]


def _enrich_activity_assignments(
    activity: Dict[str, Any],
    employee_lookup: Dict[str, Set[int]],
    employee_directory: Dict[int, Dict[str, Any]],
) -> None:
    """Populate responsible/executor/collaborator IDs based on textual info."""
    if not employee_lookup:
        return

    def _assign(field: str, sources: Sequence[str]):
        if _safe_int(activity.get(field)):
            return
        for source in sources:
            match = _match_employee_from_lookup(activity.get(source), employee_lookup)
            if match:
                activity[field] = match
                if source.endswith("_name") and not activity.get(source):
                    activity[source] = employee_directory.get(match, {}).get("name")
                return

    _assign("responsible_id", ["responsible_name", "responsible", "who"])
    _assign("executor_id", ["executor_name", "executor"])
    _assign("owner_id", ["owner_name", "owner"])

    collaborators = activity.get("collaborators") or activity.get(
        "assigned_collaborators"
    )
    if isinstance(collaborators, list):
        for entry in collaborators:
            if not isinstance(entry, dict):
                continue
            if _safe_int(entry.get("employee_id") or entry.get("id")):
                continue
            match = _match_employee_from_lookup(
                entry.get("name") or entry.get("email"), employee_lookup
            )
            if match:
                entry["employee_id"] = match
                entry.setdefault("id", match)


def _parse_project_activities_payload(raw: Any) -> List[Dict[str, Any]]:
    """Converte payloads variados em lista de dicts."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except Exception:
            return []
    return []


def _extract_activity_employee_ids(activity: Dict[str, Any]) -> Set[int]:
    """Retorna conjunto de employee_ids referenciados na atividade."""
    ids: Set[int] = set()

    def _collect(value: Any):
        candidate = _safe_int(value)
        if candidate:
            ids.add(candidate)

    for key in ("responsible_id", "executor_id", "owner_id", "employee_id"):
        _collect(activity.get(key))

    collaborators = activity.get("collaborators") or activity.get(
        "assigned_collaborators"
    )
    if isinstance(collaborators, list):
        for entry in collaborators:
            if isinstance(entry, dict):
                _collect(entry.get("id") or entry.get("employee_id"))
            else:
                _collect(entry)

    return ids


def _build_activity_row_from_json(
    project_row: Dict[str, Any], activity: Dict[str, Any]
) -> Dict[str, Any]:
    """Monta estrutura compatível com _project_activity_row_from_normalized."""
    deadline = (
        activity.get("deadline")
        or activity.get("when")
        or activity.get("due_date")
        or activity.get("completion_date")
    )
    title = (
        activity.get("title")
        or activity.get("name")
        or activity.get("what")
        or project_row.get("title")
    )
    description = (
        activity.get("description")
        or activity.get("notes")
        or activity.get("how")
        or activity.get("observations")
    )
    return {
        "activity_id": activity.get("id"),
        "activity_code": activity.get("code"),
        "activity_title": title,
        "activity_description": description,
        "activity_status": activity.get("status"),
        "activity_stage": activity.get("stage"),
        "activity_priority": activity.get("priority"),
        "activity_deadline": deadline,
        "estimated_hours": activity.get("estimated_hours"),
        "worked_hours": activity.get("worked_hours") or activity.get("actual_hours"),
        "metadata": json.dumps(activity, ensure_ascii=False),
        "project_id": project_row.get("id"),
        "responsible_id": _safe_int(activity.get("responsible_id")),
        "responsible_name": activity.get("responsible_name")
        or activity.get("responsible")
        or activity.get("who")
        or activity.get("owner"),
        "executor_id": _safe_int(activity.get("executor_id")),
        "executor_name": activity.get("executor_name")
        or activity.get("executor")
        or activity.get("assigned_to")
        or activity.get("assigned")
        or activity.get("executor_responsible"),
        "company_id": project_row.get("company_id"),
        "plan_id": project_row.get("plan_id"),
        "project_title": project_row.get("title"),
        "project_description": project_row.get("description"),
        "project_status": project_row.get("status"),
        "project_priority": project_row.get("priority"),
        "start_date": project_row.get("start_date"),
        "end_date": project_row.get("end_date"),
        "created_at": project_row.get("created_at"),
        "updated_at": project_row.get("updated_at"),
        "project_code": project_row.get("code"),
        "plan_name": project_row.get("plan_name"),
        "plan_mode": project_row.get("plan_mode"),
        "plan_origin": project_row.get("plan_origin"),
        "company_name": project_row.get("company_name"),
    }


def _project_activity_row_from_normalized(row) -> Dict[str, Any]:
    """Converte linha normalizada em estrutura esperada pelo serializer legado."""
    data = dict(row)
    return {
        "id": data.get("activity_id"),
        "company_id": data.get("company_id"),
        "plan_id": data.get("plan_id"),
        "title": data.get("activity_title") or data.get("project_title"),
        "description": data.get("activity_description") or data.get("project_description"),
        "status": data.get("activity_status") or data.get("project_status"),
        "priority": data.get("activity_priority") or data.get("project_priority"),
        "responsible_id": data.get("responsible_id"),
        "responsible_name": data.get("responsible_name"),
        "executor_id": data.get("executor_id"),
        "executor_name": data.get("executor_name"),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "deadline_date": data.get("activity_deadline") or data.get("end_date"),
        "estimated_hours": data.get("estimated_hours"),
        "worked_hours": data.get("worked_hours"),
        "company_name": data.get("company_name"),
        "plan_name": data.get("plan_name"),
        "plan_origin": data.get("plan_origin"),
        "plan_mode": data.get("plan_mode"),
        "project_id": data.get("project_id") or data.get("id"),
        "project_code": data.get("project_code"),
        "project_title": data.get("project_title"),
        "activity_code": data.get("activity_code"),
        "metadata": data.get("metadata"),
    }


def _project_activity_identity(activity: Dict[str, Any]) -> Tuple[Any, Any, Any, Any]:
    """Return identity tuple used to deduplicate activity sources."""
    project_id = activity.get("project_id") or activity.get("id")
    return (
        project_id,
        activity.get("activity_code") or activity.get("code"),
        activity.get("id"),
        activity.get("title"),
    )


def _merge_activity_sources(
    primary: List[Dict[str, Any]], secondary: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge project activities coming from different sources avoiding duplicates.

    Args:
        primary: Activities fetched from the normalized table.
        secondary: Activities parsed directly from the legacy JSON column.

    Returns:
        Unique list prioritizing the normalized records.
    """
    if not secondary:
        return primary

    merged = list(primary)
    seen = {_project_activity_identity(item) for item in primary if item}

    for activity in secondary:
        identity = _project_activity_identity(activity)
        if identity in seen:
            continue
        merged.append(activity)
        seen.add(identity)

    return merged


def _fetch_normalized_project_rows(
    cursor,
    employee_ids: Optional[Sequence[int]] = None,
    company_ids: Optional[Sequence[int]] = None,
    project_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    conditions = ["pa.is_deleted = FALSE"]
    params: Dict[str, Any] = {}
    filters_applied = False

    if employee_ids:
        clause, clause_params = _build_in_clause(employee_ids, "target_ids")
        if clause:
            params.update(clause_params)
            conditions.append(
                f"(pa.responsible_id IN ({clause}) OR pa.executor_id IN ({clause}))"
            )
            filters_applied = True

    if company_ids:
        clause, clause_params = _build_in_clause(company_ids, "company_ids")
        if clause:
            params.update(clause_params)
            conditions.append(f"cp.company_id IN ({clause})")
            filters_applied = True

    if project_ids:
        clause, clause_params = _build_in_clause(project_ids, "project_ids")
        if clause:
            params.update(clause_params)
            conditions.append(f"pa.project_id IN ({clause})")
            filters_applied = True

    if not filters_applied:
        return []

    if not _project_activities_table_available(cursor):
        return _fetch_project_rows_from_json(
            cursor,
            employee_ids=employee_ids,
            company_ids=company_ids,
            project_ids=project_ids,
        )

    query = f"""
        SELECT
            pa.id AS activity_id,
            pa.code AS activity_code,
            pa.title AS activity_title,
            pa.description AS activity_description,
            pa.status AS activity_status,
            pa.stage AS activity_stage,
            pa.priority AS activity_priority,
            pa.deadline AS activity_deadline,
            pa.estimated_hours,
            pa.worked_hours,
            pa.amount,
            pa.metadata,
            pa.project_id,
            pa.responsible_id,
            pa.executor_id,
            resp.name AS responsible_name,
            exec.name AS executor_name,
            cp.company_id,
            cp.plan_id,
            cp.title AS project_title,
            cp.description AS project_description,
            cp.status AS project_status,
            cp.priority AS project_priority,
            cp.start_date,
            cp.end_date,
            cp.created_at,
            cp.updated_at,
            cp.code AS project_code,
            pl.name AS plan_name,
            c.name AS company_name
        FROM project_activities pa
        JOIN company_projects cp ON cp.id = pa.project_id
        LEFT JOIN employees resp ON resp.id = pa.responsible_id
        LEFT JOIN employees exec ON exec.id = pa.executor_id
        LEFT JOIN plans pl ON pl.id = cp.plan_id
        LEFT JOIN companies c ON c.id = cp.company_id
        WHERE {" AND ".join(conditions)}
        ORDER BY pa.deadline NULLS LAST, pa.updated_at DESC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    table_activities = [_project_activity_row_from_normalized(row) for row in rows]

    legacy_activities = _fetch_project_rows_from_json(
        cursor,
        employee_ids=employee_ids,
        company_ids=company_ids,
        project_ids=project_ids,
    )

    if not legacy_activities:
        return table_activities

    return _merge_activity_sources(table_activities, legacy_activities)


def _fetch_project_rows_from_json(
    cursor,
    employee_ids: Optional[Sequence[int]] = None,
    company_ids: Optional[Sequence[int]] = None,
    project_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    employee_filter = {
        value for value in (_safe_int(eid) for eid in (employee_ids or [])) if value
    }

    # Construir lookup com TODOS os colaboradores das empresas filtradas
    # para permitir mapeamento de nomes para IDs
    employee_directory: Dict[int, Dict[str, Any]] = {}
    employee_lookup: Dict[str, Set[int]] = {}
    if company_ids:
        employee_directory, employee_lookup = _build_employee_lookup_by_companies(
            cursor, company_ids
        )
    elif employee_filter:
        employee_directory, employee_lookup = _build_employee_lookup(
            cursor, employee_filter
        )

    conditions: List[str] = []
    params: List[Any] = []

    if company_ids:
        placeholders = ",".join(["%s"] * len(company_ids))
        conditions.append(f"cp.company_id IN ({placeholders})")
        params.extend(company_ids)

    if project_ids:
        placeholders = ",".join(["%s"] * len(project_ids))
        conditions.append(f"cp.id IN ({placeholders})")
        params.extend(project_ids)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    cursor.execute(
        f"""
        SELECT
            cp.id,
            cp.company_id,
            cp.plan_id,
            cp.title,
            cp.description,
            cp.status,
            cp.priority,
            cp.start_date,
            cp.end_date,
            cp.created_at,
            cp.updated_at,
            cp.code,
            cp.activities,
            pl.name AS plan_name,
            pl.plan_mode,
            c.name AS company_name,
            c.client_code AS company_code
        FROM company_projects cp
        LEFT JOIN plans pl ON pl.id = cp.plan_id
        LEFT JOIN companies c ON c.id = cp.company_id
        WHERE {where_clause}
        """,
        tuple(params),
    )

    rows = cursor.fetchall()
    results: List[Dict[str, Any]] = []
    for row in rows:
        project_row = dict(row)
        activities = _parse_project_activities_payload(project_row.get("activities"))
        normalized, _, _ = normalize_project_activities(
            activities, project_row.get("code"), project_row.get("company_code")
        )
        for activity in normalized:
            if employee_lookup:
                _enrich_activity_assignments(activity, employee_lookup, employee_directory)
            if employee_filter:
                if not (_extract_activity_employee_ids(activity) & employee_filter):
                    continue
            payload = _build_activity_row_from_json(project_row, activity)
            results.append(_project_activity_row_from_normalized(payload))

    return results


def _fetch_process_directory(cursor, company_ids: List[int]) -> List[Dict[str, Any]]:
    if not company_ids:
        return []

    placeholders = ",".join(["%s"] * len(company_ids))
    processes = []
    try:
        cursor.execute(
            f"""
            SELECT p.id,
                   p.name,
                   p.code,
                   p.company_id,
                   c.name AS company_name
            FROM processes p
            LEFT JOIN companies c ON c.id = p.company_id
            WHERE p.company_id IN ({placeholders})
            ORDER BY c.name, p.code NULLS LAST, p.name
            """,
            tuple(company_ids),
        )
        rows = cursor.fetchall() or []
        for row in rows:
            row_dict = dict(row)
            process_id = row_dict.get("id")
            if process_id is None:
                continue
            name = row_dict.get("name") or "Processo sem título"
            code = row_dict.get("code")
            if isinstance(code, str):
                code = code.strip() or None
            processes.append(
                {
                    "id": process_id,
                    "title": name,
                    "name": name,
                    "code": code,
                    "company_id": row_dict.get("company_id"),
                    "company_name": row_dict.get("company_name"),
                }
            )
        return processes
    except Exception as exc:
        logger.warning("Fallback process directory (instâncias): %s", exc)
        cursor.execute(
            f"""
            SELECT pi.id,
                   pi.title,
                   pi.company_id,
                   c.name AS company_name
            FROM process_instances pi
            LEFT JOIN companies c ON c.id = pi.company_id
            WHERE pi.company_id IN ({placeholders})
            ORDER BY c.name, pi.title
            """,
            tuple(company_ids),
        )
        rows = cursor.fetchall() or []
        for row in rows:
            row_dict = dict(row)
            process_id = row_dict.get("id")
            if process_id is None:
                continue
            processes.append(
                {
                    "id": process_id,
                    "title": row_dict.get("title") or "Processo sem título",
                    "company_id": row_dict.get("company_id"),
                    "company_name": row_dict.get("company_name"),
                }
            )
        return processes


def _process_row_from_normalized(row) -> Dict[str, Any]:
    data = dict(row)
    collaborators = data.get("normalized_collaborators")
    if isinstance(collaborators, list):
        assigned_collaborators = json.dumps(collaborators)
    else:
        assigned_collaborators = data.get("assigned_collaborators")

    return {
        "id": data.get("id"),
        "company_id": data.get("company_id"),
        "process_id": data.get("process_id") or data.get("id"),
        "title": data.get("title"),
        "description": data.get("description"),
        "status": data.get("status") or "pending",
        "priority": data.get("priority") or "normal",
        "due_date": data.get("due_date"),
        "deadline_date": data.get("due_date"),
        "estimated_hours": data.get("estimated_hours"),
        "worked_hours": data.get("worked_hours") or data.get("actual_hours"),
        "actual_hours": data.get("actual_hours"),
        "assigned_collaborators": assigned_collaborators,
        "company_name": data.get("company_name"),
        "process_name": data.get("process_name"),
        "process_code": data.get("process_code"),
        "instance_code": data.get("instance_code"),
        "trigger_type": data.get("trigger_type"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
    }


def _fetch_normalized_process_rows(
    cursor,
    employee_ids: Optional[Sequence[int]] = None,
    company_ids: Optional[Sequence[int]] = None,
    process_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {}
    joins: List[str] = []
    filters: List[str] = []

    if employee_ids:
        clause, clause_params = _build_in_clause(employee_ids, "proc_target_ids")
        if clause:
            params.update(clause_params)
            joins.append(
                f"""
                JOIN (
                    SELECT DISTINCT process_instance_id
                    FROM process_instance_collaborators
                    WHERE is_deleted = FALSE
                      AND employee_id IN ({clause})
                ) pic_filter ON pic_filter.process_instance_id = pi.id
                """
            )

    if company_ids:
        clause, clause_params = _build_in_clause(company_ids, "proc_company_ids")
        if clause:
            params.update(clause_params)
            filters.append(f"pi.company_id IN ({clause})")

    if process_ids:
        clause, clause_params = _build_in_clause(process_ids, "proc_ids")
        if clause:
            params.update(clause_params)
            filters.append(f"pi.process_id IN ({clause})")

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    if not employee_ids and not company_ids and not process_ids:
        return []

    if not _process_collaborators_table_available(cursor):
        return _fetch_process_rows_from_json(
            cursor,
            employee_ids=employee_ids,
            company_ids=company_ids,
            process_ids=process_ids,
        )

    query = f"""
        WITH collaborator_data AS (
            SELECT
                pic.process_instance_id,
                json_agg(
                    json_build_object(
                        'id', pic.employee_id,
                        'name', collab.name,
                        'role', pic.role,
                        'hours', pic.estimated_hours
                    )
                ) FILTER (WHERE pic.id IS NOT NULL) AS collaborators_json
            FROM process_instance_collaborators pic
            LEFT JOIN employees collab ON collab.id = pic.employee_id
            WHERE pic.is_deleted = FALSE
            GROUP BY pic.process_instance_id
        )
        SELECT
            pi.*,
            c.name AS company_name,
            p.name AS process_name,
            p.code AS process_code,
            coalesce(collab.collaborators_json, '[]'::json) AS normalized_collaborators
        FROM process_instances pi
        {' '.join(joins)}
        LEFT JOIN collaborator_data collab ON collab.process_instance_id = pi.id
        LEFT JOIN companies c ON c.id = pi.company_id
        LEFT JOIN processes p ON p.id = pi.process_id
        {where_clause}
        ORDER BY pi.due_date NULLS LAST, pi.updated_at DESC
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [_process_row_from_normalized(row) for row in rows]


def _fetch_process_rows_from_json(
    cursor,
    employee_ids: Optional[Sequence[int]] = None,
    company_ids: Optional[Sequence[int]] = None,
    process_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    target_ids = {
        value for value in (_safe_int(eid) for eid in (employee_ids or [])) if value
    }
    
    # Construir lookup com TODOS os colaboradores das empresas filtradas
    employee_directory: Dict[int, Dict[str, Any]] = {}
    employee_lookup: Dict[str, Set[int]] = {}
    if company_ids:
        employee_directory, employee_lookup = _build_employee_lookup_by_companies(
            cursor, company_ids
        )
    elif target_ids:
        employee_directory, employee_lookup = _build_employee_lookup(
            cursor, target_ids
        )
    
    filters: List[str] = []
    params: List[Any] = []

    if company_ids:
        placeholders = ",".join(["%s"] * len(company_ids))
        filters.append(f"pi.company_id IN ({placeholders})")
        params.extend(company_ids)

    if process_ids:
        placeholders = ",".join(["%s"] * len(process_ids))
        filters.append(f"pi.process_id IN ({placeholders})")
        params.extend(process_ids)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    cursor.execute(
        f"""
        SELECT
            pi.*,
            c.name AS company_name,
            p.name AS process_name,
            p.code AS process_code
        FROM process_instances pi
        LEFT JOIN companies c ON c.id = pi.company_id
        LEFT JOIN processes p ON p.id = pi.process_id
        {where_clause}
        ORDER BY pi.due_date NULLS LAST, pi.updated_at DESC
        """,
        tuple(params),
    )

    results: List[Dict[str, Any]] = []
    for row in cursor.fetchall():
        collaborators = _parse_collaborators(row.get("assigned_collaborators"))
        
        # Enriquecer collaborators com employee_id baseado em nome/email
        if employee_lookup:
            for collab in collaborators:
                if not _safe_int(collab.get("id") or collab.get("employee_id")):
                    match = _match_employee_from_lookup(
                        collab.get("name") or collab.get("email"), employee_lookup
                    )
                    if match:
                        collab["id"] = match
                        collab["employee_id"] = match
        
        if target_ids:
            collaborator_ids = {
                cid
                for cid in (_safe_int(collab.get("id") or collab.get("employee_id")) for collab in collaborators)
                if cid is not None
            }
            if not collaborator_ids & target_ids:
                continue

        data = dict(row)
        data["normalized_collaborators"] = collaborators
        results.append(_process_row_from_normalized(data))

    return results


def get_user_activities(
    employee_id: Optional[int],
    scope: str = "me",
    filters: Optional[Dict] = None,
    company_id: Optional[int] = None,
    company_ids: Optional[List[int]] = None,
    employee_ids: Optional[List[int]] = None,
) -> List[Dict]:
    """
    Retorna atividades conforme escopo

    Args:
        employee_id: ID do colaborador
        scope: 'me', 'team' ou 'company'
        filters: Filtros adicionais (filter, search, sort)
        company_id: ID da empresa para filtrar (opcional, legado)
        company_ids: Lista de empresas para filtrar (prioritário)

    Returns:
        Lista de atividades (projetos + processos)
    """
    if employee_id is None:
        return []

    filters = (filters or {}).copy()

    if company_id and not company_ids:
        company_ids = [company_id]

    conn = pg_connect()
    cursor = conn.cursor()

    target_employee_ids = _normalize_employee_ids(employee_id, employee_ids)

    try:
        if scope == "me":
            activities: List[Dict] = []
            for target_id in target_employee_ids:
                activities.extend(
                    _collect_my_activities(cursor, target_id, company_ids=company_ids)
                )
            activities = _apply_filters(activities, filters)
            activities = _apply_sort(activities, filters.get("sort", "deadline"))
        elif scope == "team":
            activities = _get_team_activities(
                cursor, employee_id, filters, company_ids=company_ids
            )
        elif scope == "company":
            activities = _get_company_activities(
                cursor, employee_id, filters, company_ids=company_ids
            )
        else:
            activities = []

        conn.close()
        return activities

    except Exception as e:
        conn.close()
        raise e


def _get_my_activities(
    cursor, employee_id: int, filters: Optional[Dict], company_ids: Optional[List[int]] = None
) -> List[Dict]:
    """Busca atividades pessoais do colaborador"""

    filters = filters or {}
    activities = _collect_my_activities(cursor, employee_id, company_ids=company_ids)
    activities = _apply_filters(activities, filters)
    activities = _apply_sort(activities, filters.get("sort", "deadline"))

    return activities


def _collect_my_activities(
    cursor, employee_id: int, company_ids: Optional[List[int]] = None
) -> List[Dict]:
    """Retorna atividades do colaborador sem aplicar filtros."""
    project_rows = _fetch_projects_for_employee(cursor, employee_id)
    process_rows = _fetch_processes_for_employee(cursor, employee_id)

    activities = [_serialize_project_activity(row, employee_id) for row in project_rows]
    activities.extend(
        _serialize_process_activity(row, employee_id) for row in process_rows
    )

    if company_ids:
        activities = [
            activity for activity in activities if activity.get("company_id") in company_ids
        ]

    return activities


def _get_team_activities(
    cursor, employee_id: int, filters: Optional[Dict], company_ids: Optional[List[int]] = None
) -> List[Dict]:
    """Busca atividades da equipe do colaborador"""
    filters = filters or {}
    member_ids = _fetch_team_member_ids(cursor, employee_id)
    if not member_ids:
        return []

    project_rows = _fetch_projects_for_members(cursor, member_ids)
    process_rows = _fetch_processes_for_members(cursor, member_ids)

    activities = [
        _serialize_project_activity(row, employee_id, member_ids=member_ids)
        for row in project_rows
    ]
    activities.extend(
        _serialize_process_activity(row, employee_id, member_ids=member_ids)
        for row in process_rows
    )

    if company_ids:
        activities = [
            activity for activity in activities if activity.get("company_id") in company_ids
        ]

    activities = _apply_filters(activities, filters)
    activities = _apply_sort(activities, filters.get("sort", "deadline"))

    return activities


def _get_company_activities(cursor, employee_id: int, filters: Optional[Dict], company_ids: Optional[List[int]] = None) -> List[Dict]:
    """Busca todas as atividades da empresa"""
    filters = filters or {}

    # Verificar permissão
    if not _can_view_company(cursor, employee_id):
        raise PermissionError(
            "Usuário sem permissão para visualizar atividades da empresa"
        )

    target_company_ids = company_ids or []
    if not target_company_ids:
        company_id = _fetch_employee_company_id(cursor, employee_id)
        if company_id is None:
            return []
        target_company_ids = [company_id]

    activities = []
    for company_id in target_company_ids:
        project_rows = _fetch_company_projects(cursor, company_id)
        process_rows = _fetch_company_processes(cursor, company_id)

        activities.extend(
            _serialize_project_activity(row, employee_id) for row in project_rows
        )
        activities.extend(
            _serialize_process_activity(row, employee_id) for row in process_rows
        )

    if company_ids:
        activities = [
            activity for activity in activities if activity.get("company_id") in company_ids
        ]

    activities = _apply_filters(activities, filters)
    activities = _apply_sort(activities, filters.get("sort", "deadline"))

    return activities


def get_user_stats(
    employee_id: Optional[int],
    scope: str = "me",
    company_id: Optional[int] = None,
    company_ids: Optional[List[int]] = None,
    filters: Optional[Dict] = None,
    employee_ids: Optional[List[int]] = None,
) -> Dict:
    """
    Retorna estatísticas conforme escopo

    Args:
        employee_id: ID do colaborador
        scope: 'me', 'team' ou 'company'
        company_id: ID da empresa para filtrar (opcional)
        company_ids: Lista de IDs de empresa (prioritário)

    Returns:
        Dict com contadores
    """
    if employee_id is None:
        return {"pending": 0, "in_progress": 0, "overdue": 0, "completed": 0}

    company_ids = _normalize_company_ids(company_id, company_ids)
    filters = filters or {}

    conn = pg_connect()
    cursor = conn.cursor()

    target_employee_ids = _normalize_employee_ids(employee_id, employee_ids)

    try:
        if scope == "me":
            activities: List[Dict] = []
            for target_id in target_employee_ids:
                activities.extend(
                    _collect_my_activities(cursor, target_id, company_ids=company_ids)
                )
            activities = _apply_filters(activities, filters)
            stats = _calculate_stats_from_activities(activities)
        elif scope == "team":
            stats = _get_team_stats(cursor, employee_id, company_ids=company_ids, filters=filters)
        elif scope == "company":
            stats = _get_company_stats(cursor, employee_id, company_ids=company_ids, filters=filters)
        else:
            stats = {}

        conn.close()
        return stats

    except Exception as e:
        conn.close()
        raise e

def _normalize_company_ids(
    company_id: Optional[int], company_ids: Optional[List[int]]
) -> Optional[List[int]]:
    if company_ids:
        return company_ids
    if company_id:
        return [company_id]
    return None


def _normalize_employee_ids(
    employee_id: Optional[int], employee_ids: Optional[List[int]]
) -> List[int]:
    collected: List[int] = []
    if employee_ids:
        collected.extend([value for value in employee_ids if value is not None])
    if employee_id is not None:
        collected.append(employee_id)

    normalized: List[int] = []
    seen = set()
    for value in collected:
        if value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def _get_my_stats(
    cursor,
    employee_id: int,
    company_ids: Optional[List[int]] = None,
    filters: Optional[Dict] = None,
) -> Dict:
    """Estatísticas pessoais"""
    activities = _get_my_activities(
        cursor, employee_id, filters=filters, company_ids=company_ids
    )
    return _calculate_stats_from_activities(activities)


def _get_team_stats(
    cursor,
    employee_id: int,
    company_ids: Optional[List[int]] = None,
    filters: Optional[Dict] = None,
) -> Dict:
    """Estatísticas da equipe"""
    activities = _get_team_activities(
        cursor, employee_id, filters=filters, company_ids=company_ids
    )
    return _calculate_stats_from_activities(activities)


def _get_company_stats(
    cursor,
    employee_id: int,
    company_ids: Optional[List[int]] = None,
    filters: Optional[Dict] = None,
) -> Dict:
    """Estatísticas da empresa"""
    activities = _get_company_activities(
        cursor, employee_id, filters=filters, company_ids=company_ids
    )
    return _calculate_stats_from_activities(activities)


def count_activities_by_scope(
    employee_id: Optional[int],
    company_id: Optional[int] = None,
    company_ids: Optional[List[int]] = None,
    filters: Optional[Dict] = None,
    employee_ids: Optional[List[int]] = None,
) -> Dict:
    """Conta atividades em cada escopo para os contadores das abas"""

    if employee_id is None:
        return {"me": 0, "team": 0, "company": 0}

    company_ids = _normalize_company_ids(company_id, company_ids)
    filters = filters or {}
    target_employee_ids = _normalize_employee_ids(employee_id, employee_ids)

    conn = pg_connect()
    cursor = conn.cursor()

    try:
        count_me = _count_my_activities(
            cursor,
            employee_id,
            company_ids=company_ids,
            filters=filters,
            employee_ids_list=target_employee_ids,
        )
        count_team = _count_team_activities(
            cursor, employee_id, company_ids=company_ids, filters=filters
        )
        try:
            count_company = _count_company_activities(
                cursor, employee_id, company_ids=company_ids, filters=filters
            )
        except PermissionError:
            count_company = 0

        conn.close()
        return {"me": count_me, "team": count_team, "company": count_company}

    except Exception as e:
        conn.close()
        raise e


def _extract_company_id_from_row(row) -> Optional[int]:
    if not row:
        return None
    if hasattr(row, "get"):
        return row.get("company_id")
    try:
        return row["company_id"]
    except Exception:
        pass
    try:
        return row[1]
    except Exception:
        return None


def _filter_rows_by_companies(rows, company_ids: Optional[List[int]]):
    if not company_ids:
        return rows
    return [row for row in rows if _extract_company_id_from_row(row) in company_ids]


def _count_my_activities(
    cursor,
    employee_id: int,
    company_ids: Optional[List[int]] = None,
    filters: Optional[Dict] = None,
    employee_ids_list: Optional[List[int]] = None,
) -> int:
    target_ids = employee_ids_list or [employee_id]
    activities: List[Dict] = []
    for target_id in target_ids:
        activities.extend(
            _collect_my_activities(cursor, target_id, company_ids=company_ids)
        )
    activities = _apply_filters(activities, filters or {})
    return len(activities)


def _count_team_activities(
    cursor,
    employee_id: int,
    company_ids: Optional[List[int]] = None,
    filters: Optional[Dict] = None,
) -> int:
    activities = _get_team_activities(
        cursor, employee_id, filters or {}, company_ids=company_ids
    )
    return len(activities)


def _count_company_activities(
    cursor,
    employee_id: int,
    company_ids: Optional[List[int]] = None,
    filters: Optional[Dict] = None,
) -> int:
    activities = _get_company_activities(
        cursor, employee_id, filters or {}, company_ids=company_ids
    )
    return len(activities)


def _fetch_projects_for_employee(cursor, employee_id: int):
    """Busca projetos onde o colaborador é responsável ou executor."""
    rows = _fetch_normalized_project_rows(cursor, [employee_id])
    if rows:
        return rows

    cursor.execute(
        """
        SELECT 
            cp.id,
            cp.company_id,
            cp.plan_id,
            cp.title,
            cp.description,
            COALESCE(cp.status, 'planned') AS status,
            LOWER(COALESCE(cp.priority, 'normal')) AS priority,
            cp.responsible_id,
            cp.executor_id,
            resp.name AS responsible_name,
            exec.name AS executor_name,
            cp.start_date,
            cp.end_date AS deadline_date,
            cp.estimated_hours,
            cp.worked_hours,
            cp.created_at,
            cp.updated_at,
            pl.name AS plan_name,
            co.name AS company_name
        FROM company_projects cp
        LEFT JOIN employees resp ON resp.id = cp.responsible_id
        LEFT JOIN employees exec ON exec.id = cp.executor_id
        LEFT JOIN plans pl ON pl.id = cp.plan_id
        LEFT JOIN companies co ON co.id = cp.company_id
        WHERE (cp.responsible_id = %s OR cp.executor_id = %s)
    """,
        (employee_id, employee_id),
    )

    return cursor.fetchall()


def _fetch_company_projects(cursor, company_id: int):
    """Busca todos os projetos da empresa."""
    rows = _fetch_normalized_project_rows(cursor, None, [company_id])
    if rows:
        return rows

    cursor.execute(
        """
        SELECT 
            cp.id,
            cp.company_id,
            cp.plan_id,
            cp.title,
            cp.description,
            COALESCE(cp.status, 'planned') AS status,
            LOWER(COALESCE(cp.priority, 'normal')) AS priority,
            cp.responsible_id,
            cp.executor_id,
            resp.name AS responsible_name,
            exec.name AS executor_name,
            cp.start_date,
            cp.end_date AS deadline_date,
            cp.estimated_hours,
            cp.worked_hours,
            cp.created_at,
            cp.updated_at,
            pl.name AS plan_name,
            co.name AS company_name
        FROM company_projects cp
        LEFT JOIN employees resp ON resp.id = cp.responsible_id
        LEFT JOIN employees exec ON exec.id = cp.executor_id
        LEFT JOIN plans pl ON pl.id = cp.plan_id
        LEFT JOIN companies co ON co.id = cp.company_id
        WHERE cp.company_id = %s
    """,
        (company_id,),
    )

    return cursor.fetchall()


def _fetch_projects_for_members(cursor, member_ids: Sequence[int]):
    """Busca projetos atribuÃ­dos a membros de equipe."""
    if not member_ids:
        return []

    rows = _fetch_normalized_project_rows(cursor, member_ids)
    if rows:
        return rows

    member_tuple = tuple(member_ids)
    cursor.execute(
        """
        SELECT 
            cp.id,
            cp.company_id,
            cp.plan_id,
            cp.title,
            cp.description,
            COALESCE(cp.status, 'planned') AS status,
            LOWER(COALESCE(cp.priority, 'normal')) AS priority,
            cp.responsible_id,
            cp.executor_id,
            resp.name AS responsible_name,
            exec.name AS executor_name,
            cp.start_date,
            cp.end_date AS deadline_date,
            cp.estimated_hours,
            cp.worked_hours,
            cp.created_at,
            cp.updated_at,
            pl.name AS plan_name,
            co.name AS company_name
        FROM company_projects cp
        LEFT JOIN employees resp ON resp.id = cp.responsible_id
        LEFT JOIN employees exec ON exec.id = cp.executor_id
        LEFT JOIN plans pl ON pl.id = cp.plan_id
        LEFT JOIN companies co ON co.id = cp.company_id
        WHERE (cp.responsible_id = ANY(:members) OR cp.executor_id = ANY(:members))
    """,
        {"members": member_tuple},
    )

    return cursor.fetchall()


def _fetch_company_processes(cursor, company_id: int):
    """Busca instÃ¢ncias de processos da empresa."""
    rows = _fetch_normalized_process_rows(cursor, company_ids=[company_id])
    if rows:
        return rows

    cursor.execute(
        """
        SELECT 
            pi.id,
            pi.company_id,
            pi.process_id,
            pi.title,
            pi.description,
            COALESCE(pi.status, 'pending') AS status,
            LOWER(COALESCE(pi.priority, 'normal')) AS priority,
            pi.due_date AS deadline_date,
            pi.estimated_hours,
            COALESCE(pi.actual_hours, 0) AS worked_hours,
            pi.created_at,
            pi.updated_at,
            pi.assigned_collaborators,
            pi.instance_code,
            pi.trigger_type
        FROM process_instances pi
        WHERE pi.company_id = %s
    """,
        (company_id,),
    )

    return cursor.fetchall()


def _fetch_processes_for_employee(cursor, employee_id: int):
    """Busca processos onde o colaborador estÃ¡ designado."""
    rows = _fetch_normalized_process_rows(cursor, employee_ids=[employee_id])
    if rows:
        return rows

    company_id = _fetch_employee_company_id(cursor, employee_id)
    if company_id is None:
        return []

    legacy_rows = _fetch_company_processes(cursor, company_id)
    return [row for row in legacy_rows if _is_employee_in_process(row, {employee_id})]


def _fetch_processes_for_members(cursor, member_ids: Sequence[int]):
    """Busca processos associados aos membros de uma equipe."""
    if not member_ids:
        return []

    rows = _fetch_normalized_process_rows(cursor, employee_ids=member_ids)
    if rows:
        return rows

    company_ids = _fetch_companies_for_members(cursor, member_ids)
    if not company_ids:
        return []

    member_set = set(member_ids)
    processes = []
    for company_id in company_ids:
        rows = _fetch_company_processes(cursor, company_id)
        processes.extend(
            row for row in rows if _is_employee_in_process(row, member_set)
        )

    return processes


def _serialize_project_activity(
    row, employee_id: int, member_ids: Optional[Sequence[int]] = None
) -> Dict:
    """Serializa projeto."""
    data = dict(row)
    deadline = _coerce_date(data.get("deadline_date"))
    created_dt = _coerce_datetime(data.get("created_at"))
    updated_dt = _coerce_datetime(data.get("updated_at"))
    estimated_hours = _safe_float(data.get("estimated_hours"))
    worked_hours = _safe_float(data.get("worked_hours"))

    flags = _deadline_flags(deadline, data.get("status"))
    assignment = _resolve_assignment(
        employee_id, data.get("responsible_id"), data.get("executor_id"), member_ids
    )

    return {
        "id": data.get("id"),
        "type": "project",
        "project_id": data.get("project_id"),
        "activity_code": data.get("activity_code"),
        "project_code": data.get("project_code"),
        "project_title": data.get("project_title"),
        "title": data.get("title"),
        "description": data.get("description"),
        "status": (data.get("status") or "planned").lower(),
        "priority": (data.get("priority") or "normal").lower(),
        "priority_order": _priority_order((data.get("priority") or "normal").lower()),
        "status_order": _status_order((data.get("status") or "planned").lower()),
        "deadline": deadline.isoformat() if deadline else None,
        "deadline_label": _deadline_label(deadline, data.get("status")),
        "start_date": _date_to_iso(_coerce_date(data.get("start_date"))),
        "is_overdue": flags["is_overdue"],
        "is_today": flags["is_today"],
        "is_this_week": flags["is_this_week"],
        "filter_tags": _build_filter_tags(flags, data.get("status")),
        "estimated_hours": estimated_hours,
        "worked_hours": worked_hours,
        "progress_percent": _calc_progress(estimated_hours, worked_hours),
        "responsible_id": data.get("responsible_id"),
        "responsible_name": data.get("responsible_name"),
        "executor_id": data.get("executor_id"),
        "executor_name": data.get("executor_name"),
        "assignment": assignment,
        "company_id": data.get("company_id"),
        "company_name": data.get("company_name"),
        "plan_id": data.get("plan_id"),
        "plan_name": data.get("plan_name"),
        "created_at": _datetime_to_iso(created_dt),
        "updated_at": _datetime_to_iso(updated_dt),
        "deadline_sort_key": _deadline_sort_key(deadline),
        "created_sort_key": _datetime_sort_key(created_dt),
        "updated_sort_key": _datetime_sort_key(updated_dt),
    }


def _serialize_process_activity(
    row, employee_id: int, member_ids: Optional[Sequence[int]] = None
) -> Dict:
    """Serializa instÃ¢ncia de processo."""
    data = dict(row)
    deadline = _coerce_date(data.get("deadline_date"))
    created_dt = _coerce_datetime(data.get("created_at"))
    updated_dt = _coerce_datetime(data.get("updated_at"))
    estimated_hours = _safe_float(data.get("estimated_hours"))
    worked_hours = _safe_float(data.get("worked_hours"))

    flags = _deadline_flags(deadline, data.get("status"))
    collaborators = _parse_collaborators(data.get("assigned_collaborators"))
    assignment = _resolve_process_assignment(employee_id, collaborators, member_ids)

    return {
        "id": data.get("id"),
        "type": "process",
        "process_id": data.get("process_id"),
        "process_code": data.get("process_code"),
        "process_name": data.get("process_name"),
        "title": data.get("title"),
        "description": data.get("description"),
        "status": (data.get("status") or "pending").lower(),
        "priority": (data.get("priority") or "normal").lower(),
        "priority_order": _priority_order((data.get("priority") or "normal").lower()),
        "status_order": _status_order((data.get("status") or "pending").lower()),
        "deadline": deadline.isoformat() if deadline else None,
        "deadline_label": _deadline_label(deadline, data.get("status")),
        "is_overdue": flags["is_overdue"],
        "is_today": flags["is_today"],
        "is_this_week": flags["is_this_week"],
        "filter_tags": _build_filter_tags(flags, data.get("status")),
        "estimated_hours": estimated_hours,
        "worked_hours": worked_hours,
        "progress_percent": _calc_progress(estimated_hours, worked_hours),
        "assignment": assignment,
        "company_id": data.get("company_id"),
        "created_at": _datetime_to_iso(created_dt),
        "updated_at": _datetime_to_iso(updated_dt),
        "deadline_sort_key": _deadline_sort_key(deadline),
        "created_sort_key": _datetime_sort_key(created_dt),
        "updated_sort_key": _datetime_sort_key(updated_dt),
        "instance_code": data.get("instance_code"),
        "trigger_type": data.get("trigger_type"),
        "collaborators": collaborators,
    }


def _parse_deadline_value(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _activity_matches_roles(activity: Dict, roles: List[str]) -> bool:
    if not roles:
        return True
    assignment = activity.get("assignment") or {}
    assignment_type = (assignment.get("type") or "").lower()
    matches = set()
    if assignment_type == "responsible":
        matches.add("responsible")
    if assignment_type in ("executor", "assigned"):
        matches.add("executor")
    return any(role in matches for role in roles)


def _activity_within_due_date(
    activity: Dict, start_date: Optional[date], end_date: Optional[date]
) -> bool:
    if not start_date and not end_date:
        return True
    deadline_value = _parse_deadline_value(activity.get("deadline"))
    if deadline_value is None:
        return False
    if start_date and deadline_value < start_date:
        return False
    if end_date and deadline_value > end_date:
        return False
    return True


def _activity_matches_people(
    activity: Dict, target_ids: List[int], role: str
) -> bool:
    """Filter helper for responsible/executor selectors."""
    if not target_ids:
        return True

    if activity.get("type") == "project":
        if role == "responsible":
            return activity.get("responsible_id") in target_ids
        if role == "executor":
            return activity.get("executor_id") in target_ids
        return True

    if activity.get("type") == "process" and role == "executor":
        collaborators = activity.get("collaborators") or []
        collaborator_ids = {
            collab.get("id") for collab in collaborators if collab.get("id") is not None
        }
        return bool(collaborator_ids.intersection(target_ids))

    return True


def _apply_filters(activities: List[Dict], filters: Dict) -> List[Dict]:
    """Aplica filtros e busca."""
    if not activities:
        return []

    filter_type = (filters.get("filter") or "all").lower()
    search_term = (filters.get("search") or "").strip().lower()
    types_filter = filters.get("types") or []
    roles_filter = filters.get("roles") or []
    delivery_tags = filters.get("delivery_tags") or []
    # Converter strings de data para objetos date
    due_date_start_raw = filters.get("due_date_start")
    due_date_end_raw = filters.get("due_date_end")
    due_date_start = _parse_deadline_value(due_date_start_raw) if due_date_start_raw else None
    due_date_end = _parse_deadline_value(due_date_end_raw) if due_date_end_raw else None
    responsible_ids = filters.get("responsible_ids") or []
    executor_ids = filters.get("executor_ids") or []
    project_ids = filters.get("project_ids") or []
    process_ids = filters.get("process_ids") or []

    filtered = activities

    if filter_type != "all":
        filtered = [
            activity
            for activity in filtered
            if filter_type in activity.get("filter_tags", [])
        ]

    if types_filter:
        filtered = [
            activity
            for activity in filtered
            if activity.get("type") in types_filter
        ]

    if roles_filter:
        filtered = [
            activity
            for activity in filtered
            if _activity_matches_roles(activity, roles_filter)
        ]

    if delivery_tags:
        filtered = [
            activity
            for activity in filtered
            if _activity_matches_delivery_filter(activity, delivery_tags)
        ]

    if due_date_start or due_date_end:
        filtered = [
            activity
            for activity in filtered
            if _activity_within_due_date(activity, due_date_start, due_date_end)
        ]

    if responsible_ids:
        filtered = [
            activity
            for activity in filtered
            if _activity_matches_people(activity, responsible_ids, "responsible")
        ]

    if executor_ids:
        filtered = [
            activity
            for activity in filtered
            if _activity_matches_people(activity, executor_ids, "executor")
        ]

    if project_ids:
        filtered = [
            activity
            for activity in filtered
            if activity.get("type") != "project"
            or activity.get("project_id") in project_ids
            or activity.get("id") in project_ids
        ]

    if process_ids:
        filtered = [
            activity
            for activity in filtered
            if activity.get("type") != "process"
            or activity.get("process_id") in process_ids
            or activity.get("id") in process_ids
        ]

    if search_term:
        filtered = [
            activity
            for activity in filtered
            if search_term
            in " ".join(
                filter(
                    None,
                    [
                        activity.get("title", "").lower(),
                        activity.get("description", "").lower(),
                        activity.get("plan_name", "").lower(),
                        activity.get("company_name", "").lower(),
                    ],
                )
            )
        ]

    return filtered


def _apply_sort(activities: List[Dict], sort_by: str) -> List[Dict]:
    """Ordena atividades."""
    sort_by = (sort_by or "deadline").lower()

    if sort_by == "priority":
        key_fn = lambda activity: (
            -activity.get("priority_order", 0),
            activity.get("deadline_sort_key", 9999999),
        )
    elif sort_by == "status":
        key_fn = lambda activity: activity.get("status_order", 99)
    elif sort_by == "recent":
        key_fn = lambda activity: -activity.get(
            "updated_sort_key", activity.get("created_sort_key", 0)
        )
    else:
        key_fn = lambda activity: (
            activity.get("deadline_sort_key", 9999999),
            -activity.get("priority_order", 0),
        )

    return sorted(activities, key=key_fn)


def _calculate_stats_from_activities(activities: List[Dict]) -> Dict:
    """Gera contadores de status."""
    stats = {"pending": 0, "in_progress": 0, "overdue": 0, "completed": 0}

    for activity in activities:
        status = (activity.get("status") or "").lower()
        if status in ("completed", "done"):
            stats["completed"] += 1
        elif status in ("in_progress", "executing", "ongoing"):
            stats["in_progress"] += 1
        else:
            stats["pending"] += 1

        if activity.get("is_overdue") and status != "completed":
            stats["overdue"] += 1

    return stats


def _fetch_team_member_ids(cursor, employee_id: int) -> List[int]:
    """Retorna IDs dos membros da equipe."""
    cursor.execute(
        """
        SELECT team_id
        FROM team_members
        WHERE employee_id = %s
        LIMIT 1
    """,
        (employee_id,),
    )

    row = cursor.fetchone()
    if not row:
        return []

    team_id = row[0]

    cursor.execute(
        """
        SELECT employee_id
        FROM team_members
        WHERE team_id = %s
    """,
        (team_id,),
    )

    return [member_row[0] for member_row in cursor.fetchall()]


def _fetch_employee_company_id(cursor, employee_id: int) -> Optional[int]:
    """ObtÃ©m company_id do colaborador."""
    cursor.execute("SELECT company_id FROM employees WHERE id = %s", (employee_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def _fetch_companies_for_members(cursor, member_ids: Sequence[int]) -> List[int]:
    """ObtÃ©m empresas vinculadas aos membros."""
    cursor.execute(
        """
        SELECT DISTINCT company_id
        FROM employees
        WHERE id = ANY(:members)
        """,
        {"members": tuple(member_ids)},
    )

    return [row[0] for row in cursor.fetchall()]


def _is_employee_in_process(row, member_ids: set) -> bool:
    """Verifica se algum membro estÃ¡ associado a um processo."""
    collaborators = _parse_collaborators(row.get("assigned_collaborators"))
    collaborator_ids = {
        collab.get("id") for collab in collaborators if collab.get("id") is not None
    }
    return bool(member_ids & collaborator_ids)


def _parse_collaborators(raw_value) -> List[Dict]:
    """Converte campo de colaboradores em lista."""
    if not raw_value:
        return []

    if isinstance(raw_value, list):
        return raw_value

    if isinstance(raw_value, str):
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return []

    return []


def _resolve_assignment(
    employee_id: int,
    responsible_id: Optional[int],
    executor_id: Optional[int],
    member_ids: Optional[Sequence[int]],
) -> Dict:
    """Determina o papel do colaborador em um projeto."""
    assignment = {"type": None, "label": None}

    if employee_id and executor_id == employee_id:
        assignment.update({"type": "executor", "label": "âš™ï¸ Executor"})
    elif employee_id and responsible_id == employee_id:
        assignment.update({"type": "responsible", "label": "ðŸ‘¤ ResponsÃ¡vel"})
    elif member_ids and (responsible_id in member_ids or executor_id in member_ids):
        assignment.update({"type": "team", "label": "ðŸ‘¥ Equipe"})

    return assignment


def _resolve_process_assignment(
    employee_id: int, collaborators: List[Dict], member_ids: Optional[Sequence[int]]
) -> Dict:
    """Determina o papel do colaborador em um processo."""
    collaborator_ids = {
        collab.get("id") for collab in collaborators if collab.get("id") is not None
    }
    assignment = {"type": None, "label": None}

    if employee_id in collaborator_ids:
        assignment.update({"type": "assigned", "label": "âš™ï¸ Executor"})
    elif member_ids and collaborator_ids.intersection(member_ids):
        assignment.update({"type": "team", "label": "ðŸ‘¥ Equipe"})

    return assignment


def _deadline_flags(deadline: Optional[date], status: Optional[str]) -> Dict[str, bool]:
    """Calcula flags de prazo."""
    today = date.today()
    flags = {"is_today": False, "is_overdue": False, "is_this_week": False}

    if not deadline:
        return flags

    delta = (deadline - today).days
    status = (status or "").lower()

    flags["is_today"] = delta == 0
    flags["is_overdue"] = delta < 0 and status != "completed"
    flags["is_this_week"] = 0 <= delta <= 7

    return flags


def _build_filter_tags(flags: Dict[str, bool], status: Optional[str]) -> List[str]:
    """Lista tags de filtro."""
    tags = ["all"]
    if flags.get("is_today"):
        tags.append("today")
    if flags.get("is_this_week"):
        tags.append("week")
    if flags.get("is_overdue"):
        tags.append("overdue")

    status = (status or "").lower()
    if status and status not in tags:
        tags.append(status)

    return tags


def _deadline_label(deadline: Optional[date], status: Optional[str]) -> Optional[str]:
    """Texto amigÃ¡vel de prazo."""
    if not deadline:
        return None

    today = date.today()
    delta = (deadline - today).days

    if delta == 0:
        return "Hoje"
    if delta == 1:
        return "AmanhÃ£"
    if delta == -1:
        return "Ontem"
    if delta > 1:
        return f"Em {delta} dias"

    status = (status or "").lower()
    if status == "completed":
        return f"ConcluÃ­do hÃ¡ {-delta} dias"

    return f"Atrasado {abs(delta)} dias"


def _calc_progress(estimated: float, worked: float) -> int:
    """Calcula percentual de progresso."""
    if not estimated:
        return 0
    progress = (worked / estimated) * 100
    return max(0, min(int(round(progress)), 100))


def _safe_float(value: Any) -> float:
    """Converte valores em float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> Optional[int]:
    """Converte valores em int ou retorna None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        parsed = int(str(value).strip())
        return parsed
    except (TypeError, ValueError):
        return None


def _coerce_date(value: Any) -> Optional[date]:
    """Converte valor em date."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _coerce_datetime(value: Any) -> Optional[datetime]:
    """Converte valor em datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def _datetime_to_iso(value: Optional[datetime]) -> Optional[str]:
    """Formata datetime em ISO8601."""
    if not value:
        return None
    return value.isoformat()


def _date_to_iso(value: Optional[date]) -> Optional[str]:
    """Formata date em ISO."""
    if not value:
        return None
    return value.isoformat()


def _deadline_sort_key(deadline: Optional[date]) -> int:
    """Chave de ordenaÃ§Ã£o por prazo."""
    return deadline.toordinal() if deadline else 9999999


def _datetime_sort_key(value: Optional[datetime]) -> int:
    """Chave de ordenaÃ§Ã£o por data/hora."""
    if not value:
        return 0
    return int(value.timestamp())


def _get_user_role_from_employee(employee_id: int) -> Optional[str]:
    """
    Obtém o role do usuário a partir do employee_id
    
    Returns:
        str: 'admin', 'client', 'collaborator' ou None
    """
    from models.user import User
    from models.employee import Employee
    
    try:
        employee = Employee.query.get(employee_id)
        if not employee or not employee.user_id:
            return None
        
        user = User.query.get(employee.user_id)
        if not user:
            return None
        
        # Normalizar 'consultant' legado para 'collaborator'
        role = user.role
        if role == 'consultant':
            role = 'collaborator'
        
        return role
    except Exception as e:
        logger.warning(f"Erro ao obter role do usuário para employee {employee_id}: {e}")
        return None


def _can_view_company(cursor, employee_id: int) -> bool:
    """
    Verifica se employee tem permissÃ£o para ver atividades da empresa
    
    Regras:
    - admin: pode ver tudo
    - client: pode ver atividades das empresas vinculadas
    - collaborator: NÃO pode ver (apenas suas próprias atividades)
    """
    role = _get_user_role_from_employee(employee_id)
    
    # Admin pode ver tudo
    if role == 'admin':
        return True
    
    # Client pode ver atividades da empresa
    if role == 'client':
        return True
    
    # Collaborator não pode ver visão de empresa
    return False


def _priority_order(priority: str) -> int:
    """Ordem de prioridade para ordenaÃ§Ã£o"""
    order = {"urgent": 4, "high": 3, "normal": 2, "low": 1}
    return order.get(priority, 0)


def _status_order(status: str) -> int:
    """Ordem de status para ordenaÃ§Ã£o"""
    order = {
        "overdue": 1,
        "pending": 2,
        "planned": 3,
        "in_progress": 4,
        "executing": 5,
        "completed": 6,
    }
    return order.get(status, 99)


def get_occurrences_summary(
    employee_id: Optional[int],
    company_ids: Optional[List[int]] = None,
    employee_ids: Optional[List[int]] = None,
) -> Dict[str, Dict[str, int]]:
    """Retorna o resumo de ocorrências para o dashboard My Work."""

    company_ids = [int(value) for value in (company_ids or []) if value is not None]
    employee_ids = [int(value) for value in (employee_ids or []) if value is not None]
    if employee_id is not None and employee_id not in employee_ids:
        employee_ids.append(employee_id)

    filters = []
    params: List[int] = []
    if company_ids:
        placeholders = ", ".join(["%s"] * len(company_ids))
        filters.append(f"company_id IN ({placeholders})")
        params.extend(company_ids)

    if employee_ids:
        placeholders = ", ".join(["%s"] * len(employee_ids))
        filters.append(f"employee_id IN ({placeholders})")
        params.extend(employee_ids)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    query = f"""
        SELECT type,
               COUNT(*) AS count,
               COALESCE(SUM(score), 0) AS score
        FROM occurrences
        {where_clause}
        GROUP BY type
    """

    conn = pg_connect()
    cursor = conn.cursor()
    summary = {
        "positive": {"count": 0, "score": 0},
        "negative": {"count": 0, "score": 0},
    }
    try:
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            row_type = (row["type"] or "").lower()
            if row_type not in summary:
                continue
            summary[row_type]["count"] = int(row["count"] or 0)
            summary[row_type]["score"] = int(row["score"] or 0)
        return summary
    finally:
        conn.close()

# ============================================================================
# WORK HOURS
# ============================================================================


def add_work_hours(
    employee_id: int, activity_type: str, activity_id: int, work_data: Dict
) -> Dict:
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

        hours_value = _safe_float(work_data["hours"])
        if not hours_value:
            hours_value = 0

        # Inserir log
        cursor.execute(
            """
            INSERT INTO activity_work_logs 
            (activity_type, activity_id, employee_id, employee_name, work_date, hours_worked, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                activity_type,
                activity_id,
                employee_id,
                employee_name,
                work_data["work_date"],
                hours_value,
                work_data.get("description"),
            ),
        )

        log_id = cursor.fetchone()[0]
        # Aplicar horas em activity específica
        if activity_type == "project":
            if _project_activities_table_available(cursor):
                cursor.execute(
                    """
                    UPDATE project_activities
                    SET worked_hours = COALESCE(worked_hours, 0) + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (hours_value, activity_id),
                )
            else:
                logger.info(
                    "[my_work] project_activities ausente - horas registradas apenas no log."
                )
        elif activity_type == "process":
            cursor.execute(
                """
                UPDATE process_instances
                SET worked_hours = COALESCE(worked_hours, 0) + %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (hours_value, activity_id),
            )

        conn.commit()
        conn.close()

        return {
            "id": log_id,
            "success": True,
            "message": f'{work_data["hours"]}h registradas com sucesso',
        }

    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def add_comment(
    employee_id: int, activity_type: str, activity_id: int, comment_data: Dict
) -> Dict:
    """
    Adiciona comentÃ¡rio em atividade

    Args:
        employee_id: ID do colaborador
        activity_type: 'project' ou 'process'
        activity_id: ID da atividade
        comment_data: {comment_type, comment, is_private}

    Returns:
        Dict com comentÃ¡rio criado
    """
    conn = pg_connect()
    cursor = conn.cursor()

    try:
        # Buscar nome do employee
        cursor.execute("SELECT name FROM employees WHERE id = %s", (employee_id,))
        employee_row = cursor.fetchone()
        employee_name = employee_row[0] if employee_row else "Desconhecido"

        # Inserir comentÃ¡rio
        cursor.execute(
            """
            INSERT INTO activity_comments 
            (activity_type, activity_id, employee_id, employee_name, comment_type, comment_text, is_private)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                activity_type,
                activity_id,
                employee_id,
                employee_name,
                comment_data.get("comment_type", "note"),
                comment_data["comment"],
                comment_data.get("is_private", False),
            ),
        )

        comment_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return {
            "id": comment_id,
            "success": True,
            "message": "ComentÃ¡rio adicionado com sucesso",
        }

    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def complete_activity(
    employee_id: int, activity_type: str, activity_id: int, completion_data: Dict
) -> Dict:
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
        # Adicionar comentÃ¡rio final se fornecido
        if completion_data.get("completion_comment"):
            add_comment(
                employee_id,
                activity_type,
                activity_id,
                {
                    "comment_type": "note",
                    "comment": completion_data["completion_comment"],
                    "is_private": False,
                },
            )

        now_iso = datetime.utcnow().isoformat()

        # Atualizar status
        if activity_type == "project":
            cursor.execute(
                """
                UPDATE company_projects
                SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """,
                (activity_id,),
            )
            if _project_activities_table_available(cursor):
                cursor.execute(
                    """
                    UPDATE project_activities
                    SET status = 'completed',
                        stage = 'completed',
                        worked_hours = COALESCE(worked_hours, 0),
                        updated_at = CURRENT_TIMESTAMP,
                        metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{completion_comment}',
                            to_jsonb(%s::text),
                            true
                        )
                    WHERE project_id = %s
                """,
                    (
                        completion_data.get("completion_comment") or "",
                        activity_id,
                    ),
                )
            else:
                logger.info(
                    "[my_work] project_activities ausente - finalização registrada apenas no projeto."
                )
        elif activity_type == "process":
            cursor.execute(
                """
                UPDATE process_instances
                SET status = 'completed', 
                    completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """,
                (activity_id,),
            )

        conn.commit()
        conn.close()

        return {"success": True, "message": "Atividade finalizada com sucesso"}

    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


# ============================================================================
# CAPACIDADE E PERFORMANCE
# ============================================================================


def _resolve_employee_capacity(raw_value: Optional[Any]) -> float:
    """Resolve capacidade semanal configurada para o colaborador."""
    capacity = _safe_float(raw_value)
    if capacity <= 0:
        return TEAM_DEFAULT_WEEKLY_HOURS
    return capacity


def _empty_effort_bucket() -> Dict[str, float]:
    """Retorna estrutura padrão para métricas de esforço."""
    return {
        "project_estimated": 0.0,
        "project_worked": 0.0,
        "process_estimated": 0.0,
        "process_worked": 0.0,
        "open_activities": 0,
        "overdue_activities": 0,
        "total_activities": 0,
        "completed_total": 0,
        "completed_recent": 0,
        "recent_total": 0,
    }


def _collect_project_member_ids(row, target_ids: Set[int]) -> List[int]:
    """Retorna colaboradores da equipe vinculados à atividade de projeto."""
    assigned: List[int] = []
    for key in ("responsible_id", "executor_id"):
        member_id = _safe_int(row.get(key))
        if member_id and member_id in target_ids and member_id not in assigned:
            assigned.append(member_id)
    return assigned


def _collect_process_member_assignments(
    row, target_ids: Set[int]
) -> Tuple[List[int], Dict[int, float]]:
    """Retorna colaboradores do processo e a fatia estimada de horas."""
    collaborators = _parse_collaborators(row.get("assigned_collaborators"))
    assigned: List[int] = []
    hours_map: Dict[int, float] = {}
    unspecified: List[int] = []

    for entry in collaborators:
        member_id = _safe_int(entry.get("id") or entry.get("employee_id"))
        if not member_id or member_id not in target_ids:
            continue
        if member_id not in assigned:
            assigned.append(member_id)

        hours_value = entry.get("hours") or entry.get("estimated_hours")
        hours = _safe_float(hours_value)
        if hours > 0:
            hours_map[member_id] = hours_map.get(member_id, 0.0) + hours
        else:
            unspecified.append(member_id)

    total_estimated = _safe_float(row.get("estimated_hours") or row.get("actual_hours"))
    allocated = sum(hours_map.values())
    remaining = max(0.0, total_estimated - allocated)

    if unspecified and remaining > 0:
        share = remaining / len(unspecified)
        for member_id in unspecified:
            hours_map[member_id] = hours_map.get(member_id, 0.0) + share
    elif not hours_map and assigned and total_estimated > 0:
        share = total_estimated / len(assigned)
        for member_id in assigned:
            hours_map[member_id] = share

    return assigned, hours_map


def _load_employee_effort(
    cursor, employee_ids: Sequence[int], company_id: Optional[int]
) -> Dict[int, Dict[str, Any]]:
    """Agrega horas e contadores de atividades por colaborador."""
    normalized_ids = [
        value for value in (_safe_int(eid) for eid in employee_ids) if value is not None
    ]
    if not normalized_ids:
        return {}

    target_ids = set(normalized_ids)
    effort: Dict[int, Dict[str, Any]] = {eid: _empty_effort_bucket() for eid in target_ids}
    company_filter = [company_id] if company_id else None
    recent_cutoff = datetime.utcnow() - timedelta(days=RECENT_ACTIVITY_DAYS)
    today = date.today()

    project_rows = _fetch_normalized_project_rows(
        cursor, employee_ids=normalized_ids, company_ids=company_filter
    )

    for row in project_rows:
        assigned_ids = _collect_project_member_ids(row, target_ids)
        if not assigned_ids:
            continue

        member_count = len(assigned_ids)
        estimated = _safe_float(row.get("estimated_hours"))
        worked = _safe_float(row.get("worked_hours"))
        estimated_share = estimated / member_count if member_count else 0.0
        worked_share = worked / member_count if member_count else 0.0

        status = (row.get("status") or "planned").lower()
        deadline = _coerce_date(row.get("deadline_date"))
        updated_dt = _coerce_datetime(row.get("updated_at")) or _coerce_datetime(
            row.get("created_at")
        )
        is_completed = status in _CLOSED_STATUSES
        is_recent_completion = bool(updated_dt and updated_dt >= recent_cutoff)

        for member_id in assigned_ids:
            bucket = effort.setdefault(member_id, _empty_effort_bucket())
            bucket["project_estimated"] += estimated_share
            bucket["project_worked"] += worked_share
            bucket["total_activities"] += 1

            if is_completed:
                bucket["completed_total"] += 1
                if is_recent_completion:
                    bucket["completed_recent"] += 1
                    bucket["recent_total"] += 1
            else:
                bucket["open_activities"] += 1
                bucket["recent_total"] += 1
                if deadline and deadline < today:
                    bucket["overdue_activities"] += 1

    process_rows = _fetch_normalized_process_rows(
        cursor, employee_ids=normalized_ids, company_ids=company_filter
    )

    for row in process_rows:
        assigned_ids, hours_map = _collect_process_member_assignments(row, target_ids)
        if not assigned_ids:
            continue

        status = (row.get("status") or "pending").lower()
        deadline = _coerce_date(row.get("deadline_date") or row.get("due_date"))
        updated_dt = (
            _coerce_datetime(row.get("updated_at"))
            or _coerce_datetime(row.get("completed_at"))
            or _coerce_datetime(row.get("created_at"))
        )
        is_completed = status in _CLOSED_STATUSES
        is_recent_completion = bool(updated_dt and updated_dt >= recent_cutoff)

        worked_total = _safe_float(row.get("worked_hours") or row.get("actual_hours"))
        worked_share = worked_total / len(assigned_ids) if assigned_ids else 0.0

        for member_id in assigned_ids:
            bucket = effort.setdefault(member_id, _empty_effort_bucket())
            bucket["process_estimated"] += hours_map.get(member_id, 0.0)
            bucket["process_worked"] += worked_share
            bucket["total_activities"] += 1

            if is_completed:
                bucket["completed_total"] += 1
                if is_recent_completion:
                    bucket["completed_recent"] += 1
                    bucket["recent_total"] += 1
            else:
                bucket["open_activities"] += 1
                bucket["recent_total"] += 1
                if deadline and deadline < today:
                    bucket["overdue_activities"] += 1

    return effort


def _build_member_load(
    members: List[Dict[str, Any]],
    effort_map: Dict[int, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Monta payload de membros com métricas agregadas."""
    summary = {
        "open_total": 0,
        "overdue_total": 0,
        "completed_recent_total": 0,
        "recent_total": 0,
        "member_count": len(members),
        "utilization_sum": 0.0,
    }

    result: List[Dict[str, Any]] = []
    for member in members:
        member_id = member.get("employee_id")
        if member_id is None:
            continue
        bucket = effort_map.get(member_id, _empty_effort_bucket())
        capacity = _resolve_employee_capacity(member.get("weekly_hours"))
        allocated = bucket["project_estimated"] + bucket["process_estimated"]
        worked = bucket["project_worked"] + bucket["process_worked"]
        utilization = 0.0
        if capacity > 0:
            utilization = min((allocated / capacity) * 100, 200.0)
        utilization_percent = int(round(utilization))

        summary["open_total"] += bucket["open_activities"]
        summary["overdue_total"] += bucket["overdue_activities"]
        summary["completed_recent_total"] += bucket["completed_recent"]
        recent_scope = bucket["recent_total"] or (
            bucket["open_activities"] + bucket["completed_recent"]
        )
        summary["recent_total"] += recent_scope
        summary["utilization_sum"] += utilization_percent

        result.append(
            {
                "id": member_id,
                "name": member.get("name") or "Colaborador",
                "role": member.get("role"),
                "capacity": capacity,
                "allocated": round(allocated, 2),
                "worked": round(worked, 2),
                "utilization_percent": utilization_percent,
                "status": _get_load_status(utilization_percent),
                "open_activities": bucket["open_activities"],
                "overdue_activities": bucket["overdue_activities"],
            }
        )

    return result, summary


def _classify_utilization_status(value: float) -> str:
    """Classifica ocupação para o mapa de calor."""
    if value >= 95:
        return "critical"
    if value >= 85:
        return "high"
    if value >= 70:
        return "medium"
    if value >= 50:
        return "low"
    return "available"


# ============================================================================
# TEAM OVERVIEW
# ============================================================================


def _resolve_team_for_employee(
    cursor, employee_id: int, company_id: Optional[int]
) -> Optional[Dict[str, Any]]:
    """Seleciona a equipe mais relevante para o colaborador."""
    params: List[Any] = [employee_id]
    company_filter = ""
    if company_id:
        params.append(company_id)
        company_filter = " AND t.company_id = %s"

    cursor.execute(
        f"""
        SELECT t.id, t.name, t.company_id
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.id
        WHERE tm.employee_id = %s
          AND COALESCE(t.is_active, TRUE) = TRUE
          {company_filter}
        ORDER BY
            CASE WHEN tm.role = 'leader' THEN 0 ELSE 1 END,
            t.created_at DESC
        LIMIT 1
        """,
        tuple(params),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "company_id": row.get("company_id"),
    }


def _fetch_team_members(cursor, team_id: int) -> List[Dict[str, Any]]:
    """Retorna membros da equipe com dados de capacidade."""
    cursor.execute(
        """
        SELECT
            tm.employee_id,
            tm.role,
            e.name,
            e.weekly_hours,
            e.company_id
        FROM team_members tm
        JOIN employees e ON e.id = tm.employee_id
        WHERE tm.team_id = %s
        ORDER BY
            CASE WHEN tm.role = 'leader' THEN 0 ELSE 1 END,
            e.name
        """,
        (team_id,),
    )
    members = []
    for row in cursor.fetchall():
        members.append(
            {
                "employee_id": row.get("employee_id"),
                "role": row.get("role"),
                "name": row.get("name"),
                "weekly_hours": row.get("weekly_hours"),
                "company_id": row.get("company_id"),
            }
        )
    return members


def get_team_overview(employee_id: int, company_id: Optional[int] = None) -> Dict:
    """
    Retorna dados para o Team Overview

    Returns:
        Dict com distribuiÃ§Ã£o, alertas e performance
    """
    conn = pg_connect()
    cursor = conn.cursor()

    try:
        team_info = _resolve_team_for_employee(cursor, employee_id, company_id)
        if not team_info:
            conn.close()
            return {}

        team_id = team_info["id"]
        team_name = team_info.get("name") or "Equipe"
        team_company_id = _safe_int(team_info.get("company_id"))

        distribution, team_summary = _get_team_load_distribution(
            cursor, team_id, team_company_id
        )
        alerts = _generate_team_alerts(distribution)
        performance = _calculate_team_performance(team_summary)

        conn.close()

        return {
            "team_id": team_id,
            "team_name": team_name,
            "members": distribution,
            "alerts": alerts,
            "performance": performance,
        }

    except Exception as e:
        conn.close()
        raise e


def _get_team_load_distribution(
    cursor, team_id: int, company_id: Optional[int]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Calcula distribuição de carga entre membros da equipe."""
    members = _fetch_team_members(cursor, team_id)
    if not members:
        empty_summary = {
            "open_total": 0,
            "overdue_total": 0,
            "completed_recent_total": 0,
            "recent_total": 0,
            "member_count": 0,
            "utilization_sum": 0.0,
        }
        return [], empty_summary

    member_ids = [member["employee_id"] for member in members if member.get("employee_id")]
    effort_map = _load_employee_effort(cursor, member_ids, company_id)
    return _build_member_load(members, effort_map)


def _get_load_status(utilization: float) -> str:
    """Determina status baseado na utilizaÃ§Ã£o"""
    if utilization > 90:
        return "overload"
    elif utilization > 75:
        return "high"
    elif utilization < 50:
        return "available"
    else:
        return "normal"


def _generate_team_alerts(members: List[Dict]) -> List[Dict]:
    """Gera alertas baseado na distribuiÃ§Ã£o"""
    alerts = []

    for member in members:
        if member["status"] == "overload":
            alerts.append(
                {
                    "type": "overload",
                    "severity": "warning",
                    "employee_id": member["id"],
                    "employee_name": member["name"],
                    "message": f"{member['name']} sobrecarregado(a)",
                    "details": f"{member['allocated']}h alocadas ({member['utilization_percent']}% da capacidade)",
                }
            )
        elif member["status"] == "available":
            alerts.append(
                {
                    "type": "available",
                    "severity": "success",
                    "employee_id": member["id"],
                    "employee_name": member["name"],
                    "message": f"{member['name']} disponÃ­vel",
                    "details": f"{member['capacity'] - member['allocated']}h de capacidade livre",
                }
            )

    return alerts


def _calculate_team_performance(summary: Dict[str, Any]) -> Dict[str, int]:
    """Calcula métricas de performance a partir dos agregados."""
    member_count = summary.get("member_count") or 0
    utilization_sum = summary.get("utilization_sum", 0.0)
    capacity_utilization = (
        int(round(utilization_sum / member_count)) if member_count else 0
    )

    completed_recent = summary.get("completed_recent_total", 0)
    recent_total = summary.get("recent_total", 0)
    completion_rate = (
        int(round((completed_recent / recent_total) * 100)) if recent_total else 0
    )

    open_total = summary.get("open_total", 0)
    overdue_total = summary.get("overdue_total", 0)
    overdue_penalty = (
        min(overdue_total / open_total, 1.0) if open_total else 0.0
    )
    deadline_score = max(0, 100 - int(round(overdue_penalty * 100)))

    avg_score = int(
        round(
            (completion_rate * 0.5)
            + (deadline_score * 0.3)
            + (min(capacity_utilization, 100) * 0.2)
        )
    )
    avg_score = max(0, min(avg_score, 100))

    return {
        "avg_score": avg_score,
        "completion_rate": completion_rate,
        "capacity_utilization": max(0, min(capacity_utilization, 100)),
    }


def _fetch_company_teams(cursor, company_id: int) -> Dict[int, Dict[str, Any]]:
    """Carrega equipes da empresa e seus membros brutos."""
    cursor.execute(
        """
        SELECT
            t.id AS team_id,
            t.name AS team_name,
            tm.employee_id,
            tm.role,
            e.name AS employee_name,
            e.weekly_hours
        FROM teams t
        LEFT JOIN team_members tm ON tm.team_id = t.id
        LEFT JOIN employees e ON e.id = tm.employee_id
        WHERE t.company_id = %s
          AND COALESCE(t.is_active, TRUE) = TRUE
        ORDER BY t.name, e.name
        """,
        (company_id,),
    )

    teams: Dict[int, Dict[str, Any]] = {}
    for row in cursor.fetchall():
        team_id = row.get("team_id")
        if team_id is None:
            continue
        team_entry = teams.setdefault(
            team_id,
            {"team_name": row.get("team_name") or "Equipe", "members": []},
        )
        employee_id = row.get("employee_id")
        if employee_id is None:
            continue
        team_entry["members"].append(
            {
                "employee_id": employee_id,
                "role": row.get("role"),
                "name": row.get("employee_name"),
                "weekly_hours": row.get("weekly_hours"),
            }
        )
    return teams


def _build_company_team_metrics(cursor, company_id: int) -> Dict[str, Any]:
    """Retorna métricas agregadas por equipe para a empresa."""
    teams = _fetch_company_teams(cursor, company_id)
    all_member_ids: List[int] = []
    for team in teams.values():
        all_member_ids.extend(
            [
                member.get("employee_id")
                for member in team.get("members", [])
                if member.get("employee_id")
            ]
        )

    effort_map = _load_employee_effort(cursor, all_member_ids, company_id)
    metrics: Dict[int, Dict[str, Any]] = {}
    total_member_count = 0
    total_util_sum = 0.0

    for team_id, data in teams.items():
        distribution, summary = _build_member_load(data.get("members", []), effort_map)
        metrics[team_id] = {
            "team_name": data.get("team_name") or "Equipe",
            "members": distribution,
            "summary": summary,
        }
        total_member_count += summary.get("member_count", 0)
        total_util_sum += summary.get("utilization_sum", 0.0)

    return {
        "team_metrics": metrics,
        "member_count": total_member_count,
        "utilization_sum": total_util_sum,
    }


def _count_company_employees(cursor, company_id: int) -> int:
    """Conta colaboradores ativos da empresa."""
    active_filter = _build_employee_active_filter(cursor)
    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM employees e
        WHERE e.company_id = %s
          {active_filter}
        """,
        (company_id,),
    )
    row = cursor.fetchone()
    return int(row.get("total") or 0) if row else 0


def _count_open_project_activities(cursor, company_id: int) -> int:
    """Conta atividades abertas do PEV para a empresa."""
    if _project_activities_table_available(cursor):
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM project_activities pa
            JOIN company_projects cp ON cp.id = pa.project_id
            WHERE cp.company_id = :company_id
              AND COALESCE(pa.is_deleted, FALSE) = FALSE
              AND NOT (LOWER(COALESCE(pa.status, 'planned')) = ANY(:closed))
            """,
            {"closed": list(_CLOSED_STATUSES), "company_id": company_id},
        )
        row = cursor.fetchone()
        return int(row.get("total") or 0) if row else 0

    project_rows = _fetch_company_projects(cursor, company_id)
    total = 0
    for row in project_rows:
        activities = _parse_project_activities_payload(row.get("activities"))
        for activity in activities:
            status = (activity.get("status") or "").lower()
            if status in _CLOSED_STATUSES:
                continue
            total += 1
    return total


def _count_open_process_instances(cursor, company_id: int) -> int:
    """Conta instâncias de processos abertas (GRV)."""
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM process_instances
        WHERE company_id = :company_id
          AND NOT (LOWER(COALESCE(status, 'pending')) = ANY(:closed))
        """,
        {"company_id": company_id, "closed": list(_CLOSED_STATUSES)},
    )
    row = cursor.fetchone()
    return int(row.get("total") or 0) if row else 0


# ============================================================================
# COMPANY OVERVIEW
# ============================================================================


def get_company_overview(employee_id: int, company_id: Optional[int] = None) -> Dict:
    """
    Retorna dados executivos para Company Overview

    Returns:
        Dict com mÃ©tricas executivas
    """
    conn = pg_connect()
    cursor = conn.cursor()

    try:
        # Verificar permissÃ£o
        if not _can_view_company(cursor, employee_id):
            raise PermissionError("Sem permissÃ£o para visualizar dados da empresa")

        # Buscar company_id caso não tenha sido informado (fallback padrão)
        if company_id is None:
            cursor.execute("SELECT company_id FROM employees WHERE id = %s", (employee_id,))
            result = cursor.fetchone()
            if not result:
                raise ValueError("Colaborador não vinculado a uma empresa")
            company_id = result[0]

        team_stats = _build_company_team_metrics(cursor, company_id)
        summary = _get_company_summary(cursor, company_id, team_stats)
        heatmap = _get_company_heatmap(team_stats)
        ranking = _get_department_ranking(team_stats)

        conn.close()

        return {"summary": summary, "heatmap": heatmap, "ranking": ranking}

    except Exception as e:
        conn.close()
        raise e


def _get_company_summary(
    cursor, company_id: int, team_stats: Dict[str, Any]
) -> Dict[str, int]:
    """Retorna métricas gerais consolidadas da empresa."""
    active_teams = len(team_stats.get("team_metrics", {}))
    total_employees = _count_company_employees(cursor, company_id)
    total_activities = _count_open_project_activities(
        cursor, company_id
    ) + _count_open_process_instances(cursor, company_id)

    member_count = team_stats.get("member_count") or 0
    util_sum = team_stats.get("utilization_sum", 0.0)
    avg_capacity_utilization = (
        int(round(util_sum / member_count)) if member_count else 0
    )

    return {
        "active_teams": active_teams,
        "total_employees": total_employees,
        "avg_capacity_utilization": avg_capacity_utilization,
        "total_activities": total_activities,
    }


def _get_company_heatmap(team_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Mapa de calor por equipe/departamento baseado em métricas reais."""
    heatmap: List[Dict[str, Any]] = []
    for data in team_stats.get("team_metrics", {}).values():
        summary = data.get("summary") or {}
        member_count = summary.get("member_count", 0)
        activities_count = summary.get("open_total", 0)
        avg_utilization = (
            int(
                round(summary.get("utilization_sum", 0.0) / member_count)
            )
            if member_count
            else 0
        )
        heatmap.append(
            {
                "team_name": data.get("team_name") or "Equipe",
                "employee_count": member_count,
                "activities_count": activities_count,
                "utilization_percent": avg_utilization,
                "status": _classify_utilization_status(avg_utilization),
            }
        )
    return heatmap


def _get_department_ranking(team_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Ranking de performance por equipe baseado em score calculado."""
    ranking: List[Dict[str, Any]] = []
    for data in team_stats.get("team_metrics", {}).values():
        summary = data.get("summary") or {}
        performance = _calculate_team_performance(summary)
        ranking.append(
            {
                "team_name": data.get("team_name") or "Equipe",
                "score": performance["avg_score"],
                "completion_rate": performance["completion_rate"],
            }
        )

    ranking.sort(
        key=lambda item: (item["score"], item["completion_rate"]), reverse=True
    )
    for idx, entry in enumerate(ranking, start=1):
        entry["rank"] = idx
    return ranking[:5]


def process_my_work_filters(
    user_id: int,
    request_args: Dict[str, Any],
    SELECTION_MODE_NONE: str = "none",
) -> Dict[str, Any]:
    """
    Processa filtros do My Work exatamente como a API faz.
    
    Esta função centraliza toda a lógica de processamento de filtros,
    garantindo que a API e o relatório usem exatamente a mesma lógica.
    
    Args:
        user_id: ID do usuário logado
        request_args: Dicionário com os parâmetros da requisição (equivalente a request.args)
        SELECTION_MODE_NONE: Valor para modo de seleção "none" (padrão: "none")
    
    Returns:
        Dicionário com:
            - employee_id: ID do colaborador
            - scope: Escopo ajustado conforme role
            - company_ids: Lista de company_ids após validação de permissões
            - employee_ids: Lista de employee_ids vinculados ao usuário
            - filters: Dicionário com todos os filtros processados
            - has_no_companies: True se usuário não tem empresas disponíveis
    
    Raises:
        ValueError: Se usuário não estiver vinculado a um colaborador
    """
    from models.user import User
    from models.company import Company
    
    # Obter role do usuário (normalizar 'consultant' para 'collaborator')
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"Usuário {user_id} não encontrado")
    
    user_role = user.role
    if user_role == "consultant":
        user_role = "collaborator"

    def _fetch_all_company_ids() -> List[int]:
        """Retorna todos IDs de empresas cadastradas."""
        return [
            company_id
            for (company_id,) in Company.query.with_entities(Company.id).all()
        ]

    # Determinar allowed_company_ids conforme role
    allowed_company_ids: Optional[List[int]]
    if user_role == "admin":
        allowed_company_ids = None  # Admin pode ver todas
    else:
        base_companies = get_user_employees(user_id) or []
        allowed_company_ids = [
            comp.get("company_id")
            for comp in base_companies
            if comp.get("company_id") is not None
        ]
    
    # Mapear user para employee
    employee_id = get_employee_from_user(user_id)
    if employee_id is None:
        raise ValueError("Usuário não vinculado a um colaborador. Solicite ao administrador para concluir o cadastro.")

    # Coleção de todos os employee_ids vinculados ao usuário
    def _collect_employee_ids() -> List[int]:
        employee_ids_set = set()
        if employee_id:
            employee_ids_set.add(employee_id)

        try:
            companies = get_user_employees(user_id) or []
        except Exception as exc:
            logger.warning(
                "Falha ao buscar colaboradores vinculados ao usuário %s: %s",
                user_id,
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
    scope = request_args.get("scope", "me")
    company_id = request_args.get("company_id")
    if company_id is not None:
        try:
            company_id = int(company_id)
        except (ValueError, TypeError):
            company_id = None

    def _parse_int_csv(raw_value: Optional[str]) -> List[int]:
        if not raw_value:
            return []
        values = []
        for chunk in str(raw_value).split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                values.append(int(chunk))
            except ValueError:
                continue
        return values

    company_ids = _parse_int_csv(request_args.get("company_ids"))

    # Se company_id (legado) vier e company_ids não, adiciona
    if company_id and not company_ids:
        company_ids = [company_id]

    # Ajustar company_ids conforme permissões
    if allowed_company_ids is not None:
        if company_ids:
            company_ids = [cid for cid in company_ids if cid in allowed_company_ids]
        else:
            company_ids = allowed_company_ids[:]
    elif not company_ids:
        company_ids = _fetch_all_company_ids()

    # Caso usuário não tenha nenhuma empresa disponível após as validações
    if not company_ids:
        logger.info(
            f"🚫 Nenhuma empresa disponível para user_id={user_id} (role={user_role}). Retornando vazio."
        )
        return {
            "employee_id": employee_id,
            "scope": scope,
            "company_ids": [],
            "employee_ids": employee_ids,
            "filters": {},
            "has_no_companies": True,
        }

    # Forçar escopo conforme perfil
    if user_role == "admin":
        scope = "company"
    elif user_role == "client":
        scope = "company"
    elif user_role == "collaborator":
        scope = "me"
        employee_ids = [employee_id] if employee_id else []
        logger.info(
            f"👤 Collaborator - scope='me', employee_ids: {employee_ids}, companies: {company_ids}"
        )

    # Processar filtros
    filters = {
        "filter": request_args.get("filter", "all"),
        "search": request_args.get("search", ""),
        "sort": request_args.get("sort", "deadline"),
    }

    types_raw = request_args.get("types")
    if types_raw:
        filters["types"] = [
            t.strip()
            for t in str(types_raw).split(",")
            if t.strip() in ("project", "process")
        ]

    roles_raw = request_args.get("roles")
    if roles_raw:
        filters["roles"] = [
            r.strip()
            for r in str(roles_raw).split(",")
            if r.strip() in ("responsible", "executor")
        ]

    responsible_ids = _parse_int_csv(request_args.get("responsible_ids"))
    if responsible_ids:
        filters["responsible_ids"] = responsible_ids

    executor_ids = _parse_int_csv(request_args.get("executor_ids"))
    if executor_ids:
        filters["executor_ids"] = executor_ids

    project_selection = (request_args.get("project_selection") or "").lower()
    project_ids = _parse_int_csv(request_args.get("project_ids"))
    if project_ids:
        filters["project_ids"] = project_ids
    elif project_selection == SELECTION_MODE_NONE:
        filters["project_selection"] = SELECTION_MODE_NONE

    process_selection = (request_args.get("process_selection") or "").lower()
    process_ids = _parse_int_csv(request_args.get("process_ids"))
    if process_ids:
        filters["process_ids"] = process_ids
    elif process_selection == SELECTION_MODE_NONE:
        filters["process_selection"] = SELECTION_MODE_NONE

    delivery_raw = request_args.get("delivery_tags")
    if delivery_raw is not None:
        filters["delivery_tags"] = [
            tag.strip()
            for tag in str(delivery_raw).split(",")
            if tag.strip() in DELIVERY_TAGS
        ]

    def _parse_date(value: Any):
        if not value:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    due_date_start = _parse_date(request_args.get("due_date_start"))
    due_date_end = _parse_date(request_args.get("due_date_end"))
    if due_date_start:
        filters["due_date_start"] = due_date_start
    if due_date_end:
        filters["due_date_end"] = due_date_end

    # Adicionar company_ids e scope aos filtros
    filters["company_ids"] = company_ids
    filters["scope"] = scope

    return {
        "employee_id": employee_id,
        "scope": scope,
        "company_ids": company_ids,
        "employee_ids": employee_ids,
        "filters": filters,
        "has_no_companies": False,
    }

