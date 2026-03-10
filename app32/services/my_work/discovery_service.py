from typing import List, Dict, Any, Optional
import logging
from datetime import date
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

logger = logging.getLogger(__name__)

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
    
    user_role = user.role
    if user_role == 'consultant':
        user_role = 'collaborator'

    # 1. Resolve Companies based on Role
    if user_role in ('admin', 'client'):
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
        # Client and Collaborator: only linked companies
        base_companies = get_user_associated_companies(user_id)
        unique_companies = []
        seen_ids = set()
        for c in base_companies:
            cid = c.get("company_id")
            # Filter inactive companies from associations
            is_active = c.get("is_active")
            if is_active is False: # Explicitly inactive
                continue

            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                unique_companies.append({
                    "company_id": cid,
                    "company_name": c.get("company_name") or "Empresa",
                    "company_code": c.get("company_code"),
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

    # 2. Resolve Collaborators based on Role
    if user_role == 'collaborator':
        employee_id = get_employee_id_from_user(user_id)
        if employee_id:
            employee = Employee.query.get(employee_id)
            if employee:
                result["collaborators"] = [{
                    "id": employee.id,
                    "name": employee.name,
                    "email": employee.email,
                    "company_id": employee.company_id,
                    "company_name": employee.company.name if employee.company else "Empresa",
                }]
    else:
        # Admin e Client: todos os colaboradores das empresas alvo
        result["collaborators"] = fetch_collaborator_directory(company_ids)

        # 3. Resolve Projects and Processes
    projects = fetch_project_directory(company_ids)
    processes = fetch_process_directory(company_ids)
    
    # 3.1 Fetch process owners directory
    process_owners = [] # Optional: fetch specifically if needed
    
    result.update({
        "projects": projects,
        "processes": processes,
        "process_owners": process_owners
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
    
    # 1. Resolve basic parameters
    user = User.query.get(user_id)
    user_role = user.role if user else 'collaborator'
    
    associated = get_user_associated_companies(user_id)
    my_employee_ids = [c["employee_id"] for c in associated if c.get("employee_id")]
    
    # Target companies resolution
    if not company_ids:
        if user_role == 'admin':
            company_ids = [c.id for c in Company.query.filter(Company.is_active == True).all()]
            logger.info(f"👔 Admin Global Search: Found {len(company_ids)} active companies.")
        else:
            # Re-fetch associations with is_active filter or rely on the previous logic
            company_ids = [c["company_id"] for c in associated if c.get("company_id") and c.get("is_active") is not False]
            logger.info(f"👤 Regular Search: Linked to {len(company_ids)} active companies.")
    else:
        # Se company_ids fornecidos, valida que estão dentro do acesso do user (exceto admin e client)
        if user_role not in ('admin', 'client'):
            my_cids = set([c["company_id"] for c in associated if c.get("company_id") and c.get("is_active") is not False])
            company_ids = [cid for cid in company_ids if cid in my_cids]
        else:
            # Even for admin, if explicitids provided, should we filter out inactive ones globally?
            # Usually yes if the rule is strict.
            active_ids = set([c.id for c in Company.query.filter(Company.is_active == True).all()])
            company_ids = [cid for cid in company_ids if cid in active_ids]

    logger.info(f"🔍 Discovery [scope={scope}]: user={user_id}, role={user_role}, target_companies={company_ids}")

    if not company_ids:
        logger.warning(f"⚠️ No company_ids found for user {user_id}")
        return [], {"me": 0, "company": 0, "general": 0}

    # 2. Scope resolution
    # Always fetch everything in target company_ids to calculate counts correctly
    allowed_company_ids = company_ids if company_ids else [c["company_id"] for c in associated if c.get("company_id")]
    
    # Identify the "active" company for specific filtering
    # If not provided, try to use the first available one
    if not active_company_id and allowed_company_ids:
        active_company_id = allowed_company_ids[0]

    from utils.permissions import has_permission
    can_view_by_cid = {}
    for cid in allowed_company_ids:
        if user_role in ('admin', 'client'):
            can_view_by_cid[cid] = True
        else:
            can_view_by_cid[cid] = has_permission(cid, 'companies', 'view')

    # 3. Build lookup for identity resolution
    directory, lookup = build_employee_lookup_v2(allowed_company_ids)
    
    # 4 & 5. Fetch ALL activities for allowed companies (without employee filter to get counts)
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
    logger.info(f"📊 Raw Discovery: Found {len(all_raw)} total activities across all allowed companies.")

    today = date.today()
    me_count = 0
    company_scope_count = 0
    general_count = 0
    
    # Search and sidebar filter parameters
    search_term = (filters.get("search") or "").lower().strip()
    # filters.get("employee_ids") are the specific employees selected in the sidebar
    sidebar_emp_ids = set(filters.get("employee_ids") or [])
    
    final_activities = []
    
    # Filter and Enrich
    for act in all_raw:
        # A. Basic Sidebar Filtering (Applies to all scopes counters)
        
        # 1. Search filter
        if search_term:
            title = (act.get("title") or "").lower()
            desc = (act.get("description") or "").lower()
            p_title = (act.get("project_title") or "").lower()
            if search_term not in title and search_term not in desc and search_term not in p_title:
                continue

        # 2. Employee filter (sidebar selection)
        if sidebar_emp_ids:
            act_emp_ids = set()
            if act.get("type") == "project":
                if act.get("responsible_id"): act_emp_ids.add(act.get("responsible_id"))
                if act.get("executor_id"): act_emp_ids.add(act.get("executor_id"))
            else:
                collabs = act.get("collaborators_json") or []
                for c in collabs:
                    cid = c.get("id") or c.get("employee_id")
                    if cid: act_emp_ids.add(cid)
            
            if not (act_emp_ids & sidebar_emp_ids):
                continue

        # 3. Status filter (delivery_tags)
        # DELIVERY_FILTER_VALUES = ['open', 'completed']
        status_filter = filters.get("delivery_tags")
        if status_filter is not None:
            closed_statuses = ['completed', 'done', 'cancelado', 'canceled', 'archived']
            act_status = (act.get("status") or "").lower()
            is_closed = act_status in closed_statuses
            
            match_open = 'open' in status_filter and not is_closed
            match_completed = 'completed' in status_filter and is_closed
            
            if not (match_open or match_completed):
                continue

        # 4. Period filter (due_date)
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
                except: pass

            if start_filter:
                try:
                    start_dt = date.fromisoformat(start_filter)
                    if not act_date or act_date < start_dt:
                        continue
                except: pass
            
            if end_filter:
                try:
                    end_dt = date.fromisoformat(end_filter)
                    if not act_date or act_date > end_dt:
                        continue
                except: pass

        # B. Calculate Overdue and metadata
        deadline_val = act.get("deadline")
        act_status = (act.get("status") or "").lower()
        is_overdue = False
        if deadline_val:
            try:
                d_dt = None
                if isinstance(deadline_val, str):
                    try: d_dt = date.fromisoformat(deadline_val[:10])
                    except ValueError: pass
                elif hasattr(deadline_val, 'date'): d_dt = deadline_val.date()
                elif isinstance(deadline_val, date): d_dt = deadline_val
                if d_dt:
                    is_overdue = d_dt < today and act_status not in ("completed", "done", "cancelado")
            except: pass
        act["is_overdue"] = is_overdue

        # Determine if it's "Mine" (globally)
        is_mine = False
        if act.get("type") == "project":
            is_mine = act.get("responsible_id") in my_employee_ids or act.get("executor_id") in my_employee_ids
        else:
            collabs = act.get("collaborators_json") or []
            is_mine = any((c.get("id") or c.get("employee_id")) in my_employee_ids for c in collabs)
        
        # Determine if it's in active company context
        is_in_active_company = (active_company_id and act.get("company_id") == active_company_id)
        
        can_view_all = can_view_by_cid.get(act.get("company_id"), False)
        
        # C. Update Counters (Only for items that matched A)
        if is_mine:
            me_count += 1
            
        if is_in_active_company:
            if can_view_all or is_mine:
                company_scope_count += 1
            
        if can_view_all or is_mine:
            general_count += 1

        # D. Determine if it enters the final list based on requested scope
        include = False
        if scope == "me":
            # "Me" can be global across all allowed companies, or restricted if needed.
            # Usually, people want to see their tasks across all their contexts.
            if is_mine:
                include = True
        elif scope == "company":
            if is_in_active_company and (can_view_all or is_mine):
                include = True
        elif scope == "general":
            # Geral scope respects sidebar company filter
            if (not company_ids or act.get("company_id") in company_ids) and (can_view_all or is_mine):
                include = True
            
        if include:
            # Enrich Assignment for UI
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

    # 7. Sort final list
    def get_sort_key(x):
        d_val = x.get("deadline_date")
        d_obj = None
        if isinstance(d_val, str):
            try: d_obj = date.fromisoformat(d_val[:10])
            except: pass
        elif hasattr(d_val, 'date'): d_obj = d_val.date()
        elif isinstance(d_val, date): d_obj = d_val
        return (d_obj or date(9999, 12, 31), x.get("id") or 0)

    final_activities.sort(key=get_sort_key)
    
    scope_counts = {
        "me": me_count,
        "company": company_scope_count,
        "general": general_count
    }
    
    return final_activities, scope_counts
