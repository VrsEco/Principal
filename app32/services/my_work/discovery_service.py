from typing import List, Dict, Any, Optional
import logging
from datetime import date
from sqlalchemy import func, or_
from models.user import User
from models.company import Company
from models.employee import Employee
from .project_service import fetch_project_directory, fetch_normalized_project_rows
from .process_service import fetch_process_directory, fetch_normalized_process_rows
from .employee_service import (
    get_user_associated_companies,
    get_employee_id_from_user,
    fetch_collaborator_directory,
    build_employee_lookup_v2
)
from .utils import safe_int
from utils.permissions import _normalize_role_title, can_access_company, has_permission, is_client_user

logger = logging.getLogger(__name__)


def _normalize_user_role(user: Optional[User], company_ids: Optional[List[int]] = None) -> str:
    role = (user.role if user else 'collaborator') or 'collaborator'
    if role == 'consultant':
        role = 'collaborator'

    if role == 'admin':
        return 'admin'
    if role == 'client':
        return 'client'

    if not user:
        return 'collaborator'

    query = Employee.query.filter(Employee.user_id == user.id)
    if company_ids:
        query = query.filter(Employee.company_id.in_(company_ids))
    query = query.filter(
        or_(Employee.status.is_(None), func.lower(Employee.status) == 'active')
    )

    for employee in query.all():
        role_title = _normalize_role_title(employee.role.title if employee and employee.role else None)
        if role_title in {'superuser', 'administrador', 'administrator', 'admin'}:
            return 'admin'

    return 'collaborator'


def _get_active_associated_companies(user_id: int) -> List[Dict[str, Any]]:
    associated = get_user_associated_companies(user_id)
    return [
        company for company in associated
        if company.get('company_id') and company.get('is_active') is not False
    ]


def _dedupe_company_ids(companies: List[Dict[str, Any]]) -> List[int]:
    seen = set()
    ordered = []
    for company in companies:
        cid = company.get('company_id')
        if cid and cid not in seen:
            seen.add(cid)
            ordered.append(cid)
    return ordered


def get_filter_options_v2(user_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Main entry point for filter options, following Architecture v2.0.
    """
    user = User.query.get(user_id)
    if not user:
        return {
            "companies": [],
            "collaborators": [],
            "projects": [],
            "processes": [],
        }

    associated = _get_active_associated_companies(user_id)
    associated_company_ids = _dedupe_company_ids(associated)
    user_role = _normalize_user_role(user, associated_company_ids)

    if user_role == 'admin':
        all_comps = Company.query.filter(Company.is_active == True).order_by(Company.name).all()
        unique_companies = [
            {
                "company_id": c.id,
                "company_name": c.name,
                "company_code": getattr(c, "client_code", None),
            }
            for c in all_comps
        ]
        company_ids = [c.id for c in all_comps]
    else:
        unique_companies = []
        seen_ids = set()
        for company in associated:
            cid = company.get("company_id")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                unique_companies.append({
                    "company_id": cid,
                    "company_name": company.get("company_name") or "Empresa",
                    "company_code": company.get("company_code"),
                })
        company_ids = list(seen_ids)

    result = {
        "success": True,
        "user_role": user_role,
        "companies": unique_companies,
        "collaborators": [],
        "projects": [],
        "processes": [],
    }

    if not company_ids:
        return result

    if user_role == 'collaborator':
        collaborator_rows = []
        seen_employee_ids = set()
        for company in associated:
            employee_id = company.get('employee_id')
            if not employee_id or employee_id in seen_employee_ids:
                continue
            seen_employee_ids.add(employee_id)
            collaborator_rows.append({
                "id": employee_id,
                "name": company.get('employee_name') or 'Colaborador',
                "email": company.get('employee_email'),
                "company_id": company.get('company_id'),
                "company_name": company.get('company_name') or 'Empresa',
            })
        result["collaborators"] = collaborator_rows
    else:
        result["collaborators"] = fetch_collaborator_directory(company_ids)

    result.update({
        "projects": fetch_project_directory(company_ids),
        "processes": fetch_process_directory(company_ids),
        "process_owners": []
    })

    return result


def get_user_activities_v2(
    user_id: int,
    scope: str = "me",
    filters: Optional[Dict] = None,
    company_ids: Optional[List[int]] = None,
    employee_ids: Optional[List[int]] = None,
    active_company_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Unified entry point for user activities list.
    Architecture v2.0 - Modular and using SQLAlchemy.
    """
    filters = filters or {}

    user = User.query.get(user_id)
    associated = _get_active_associated_companies(user_id)
    associated_company_ids = _dedupe_company_ids(associated)
    user_role = _normalize_user_role(user, associated_company_ids)
    associated_company_ids = _dedupe_company_ids(associated)
    my_employee_ids = [c["employee_id"] for c in associated if c.get("employee_id")]

    if user_role == 'admin':
        active_company_ids = [c.id for c in Company.query.filter(Company.is_active == True).all()]
    else:
        active_company_ids = associated_company_ids[:]

    requested_company_ids = [safe_int(cid) for cid in (company_ids or []) if safe_int(cid)]
    if requested_company_ids:
        if user_role == 'admin':
            allowed_company_ids = [cid for cid in requested_company_ids if cid in active_company_ids]
        else:
            allowed_company_ids = [cid for cid in requested_company_ids if cid in associated_company_ids]
    else:
        allowed_company_ids = active_company_ids[:]

    if active_company_id and active_company_id not in allowed_company_ids:
        active_company_id = None

    if not active_company_id and allowed_company_ids:
        active_company_id = allowed_company_ids[0]

    if user_role == 'client':
        scope = 'company'
        if active_company_id:
            allowed_company_ids = [active_company_id]
    elif user_role == 'collaborator':
        scope = 'me'
        if active_company_id:
            allowed_company_ids = [active_company_id]

    logger.info(
        f"🔍 Discovery [scope={scope}]: user={user_id}, role={user_role}, active_company={active_company_id}, target_companies={allowed_company_ids}"
    )

    if not allowed_company_ids:
        logger.warning(f"⚠️ No company_ids found for user {user_id}")
        return [], {"me": 0, "company": 0, "general": 0}

    can_view_by_cid = {}
    for cid in allowed_company_ids:
        if user_role in ('admin', 'client'):
            can_view_by_cid[cid] = can_access_company(cid)
        else:
            can_view_by_cid[cid] = has_permission(cid, 'companies', 'view')

    directory, lookup = build_employee_lookup_v2(allowed_company_ids)

    project_rows = fetch_normalized_project_rows(
        employee_ids=None,
        company_ids=allowed_company_ids,
        project_ids=filters.get("project_ids"),
        employee_lookup=lookup,
        employee_directory=directory
    )
    process_rows = fetch_normalized_process_rows(
        employee_ids=None,
        company_ids=allowed_company_ids,
        process_ids=filters.get("process_ids"),
        employee_lookup=lookup,
        employee_directory=directory
    )

    all_raw = project_rows + process_rows
    logger.info(f"📊 Raw Discovery: Found {len(all_raw)} total activities across allowed companies.")

    today = date.today()
    me_count = 0
    company_scope_count = 0
    general_count = 0

    search_term = (filters.get("search") or "").lower().strip()
    sidebar_emp_ids = set(filters.get("employee_ids") or [])

    final_activities = []

    for act in all_raw:
        if search_term:
            title = (act.get("title") or "").lower()
            desc = (act.get("description") or "").lower()
            p_title = (act.get("project_title") or "").lower()
            if search_term not in title and search_term not in desc and search_term not in p_title:
                continue

        if sidebar_emp_ids:
            act_emp_ids = set()
            if act.get("type") == "project":
                if act.get("responsible_id"):
                    act_emp_ids.add(act.get("responsible_id"))
                if act.get("executor_id"):
                    act_emp_ids.add(act.get("executor_id"))
            else:
                collabs = act.get("collaborators_json") or []
                for collaborator in collabs:
                    cid = collaborator.get("id") or collaborator.get("employee_id")
                    if cid:
                        act_emp_ids.add(cid)

            if not (act_emp_ids & sidebar_emp_ids):
                continue

        status_filter = filters.get("delivery_tags")
        if status_filter is not None:
            closed_statuses = ['completed', 'done', 'cancelado', 'canceled', 'archived']
            act_status = (act.get("status") or "").lower()
            is_closed = act_status in closed_statuses

            match_open = 'open' in status_filter and not is_closed
            match_completed = 'completed' in status_filter and is_closed
            if not (match_open or match_completed):
                continue

        start_filter = filters.get("due_date_start")
        end_filter = filters.get("due_date_end")
        if start_filter or end_filter:
            raw_deadline = act.get("deadline_date") or act.get("due_date") or act.get("deadline")
            act_date = None
            if raw_deadline:
                try:
                    if isinstance(raw_deadline, str):
                        act_date = date.fromisoformat(raw_deadline[:10])
                    elif hasattr(raw_deadline, 'date'):
                        act_date = raw_deadline.date()
                    elif isinstance(raw_deadline, date):
                        act_date = raw_deadline
                except Exception:
                    pass

            if start_filter:
                try:
                    start_dt = date.fromisoformat(start_filter)
                    if not act_date or act_date < start_dt:
                        continue
                except Exception:
                    pass

            if end_filter:
                try:
                    end_dt = date.fromisoformat(end_filter)
                    if not act_date or act_date > end_dt:
                        continue
                except Exception:
                    pass

        deadline_val = act.get("deadline")
        act_status = (act.get("status") or "").lower()
        is_overdue = False
        if deadline_val:
            try:
                d_dt = None
                if isinstance(deadline_val, str):
                    try:
                        d_dt = date.fromisoformat(deadline_val[:10])
                    except ValueError:
                        pass
                elif hasattr(deadline_val, 'date'):
                    d_dt = deadline_val.date()
                elif isinstance(deadline_val, date):
                    d_dt = deadline_val
                if d_dt:
                    is_overdue = d_dt < today and act_status not in ("completed", "done", "cancelado")
            except Exception:
                pass
        act["is_overdue"] = is_overdue

        if act.get("type") == "project":
            is_mine = act.get("responsible_id") in my_employee_ids or act.get("executor_id") in my_employee_ids
        else:
            collabs = act.get("collaborators_json") or []
            is_mine = any((c.get("id") or c.get("employee_id")) in my_employee_ids for c in collabs)

        is_in_active_company = bool(active_company_id and act.get("company_id") == active_company_id)
        can_view_all = can_view_by_cid.get(act.get("company_id"), False)

        if is_mine:
            me_count += 1
        if is_in_active_company and (can_view_all or is_mine):
            company_scope_count += 1
        if can_view_all or is_mine:
            general_count += 1

        include = False
        if scope == "me":
            include = is_mine
        elif scope == "company":
            include = is_in_active_company and (can_view_all or is_mine)
        elif scope == "general":
            include = (act.get("company_id") in allowed_company_ids) and (can_view_all or is_mine)

        if include:
            if is_mine:
                act["viewer_is_directly_assigned"] = True
                if act.get("type") == "project":
                    if act.get("executor_id") in my_employee_ids:
                        act["assignment"] = {"type": "executor", "label": "⚙️ Executor"}
                    else:
                        act["assignment"] = {"type": "responsible", "label": "👤 Responsável"}
                else:
                    act["assignment"] = {"type": "assigned", "label": "⚙️ Executor"}
            else:
                act["viewer_is_directly_assigned"] = False
                act["assignment"] = {"type": "none", "label": ""}
            final_activities.append(act)

    def get_sort_key(item):
        d_val = item.get("deadline_date")
        d_obj = None
        if isinstance(d_val, str):
            try:
                d_obj = date.fromisoformat(d_val[:10])
            except Exception:
                pass
        elif hasattr(d_val, 'date'):
            d_obj = d_val.date()
        elif isinstance(d_val, date):
            d_obj = d_val
        return (d_obj or date(9999, 12, 31), item.get("id") or 0)

    final_activities.sort(key=get_sort_key)

    scope_counts = {
        "me": me_count,
        "company": company_scope_count,
        "general": general_count
    }

    return final_activities, scope_counts
