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
    if user_role == 'admin':
        all_comps = Company.query.order_by(Company.name).all()
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
        # Admin and Client: all collaborators for target companies
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
            company_ids = [c.id for c in Company.query.all()]
            logger.info(f"👔 Admin Global Search: Found {len(company_ids)} companies.")
        else:
            company_ids = [c["company_id"] for c in associated if c.get("company_id")]
            logger.info(f"👤 Regular Search: Linked to {len(company_ids)} companies.")
    else:
        # If company_ids provided, ensure they are within user access (skip for admin)
        if user_role != 'admin':
            my_cids = set([c["company_id"] for c in associated if c.get("company_id")])
            company_ids = [cid for cid in company_ids if cid in my_cids]

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
        
        # Determine if it's in active company
        is_in_active_company = (act.get("company_id") == active_company_id)
        
        # C. Update Counters (Only for items that matched A)
        if is_mine and is_in_active_company:
            me_count += 1
            
        if is_in_active_company:
            company_scope_count += 1
            
        general_count += 1

        # D. Determine if it enters the final list based on requested scope
        include = False
        if scope == "me":
            if is_mine and is_in_active_company:
                include = True
        elif scope == "company":
            if is_in_active_company:
                include = True
        elif scope == "general":
            # Geral scope respects sidebar company filter
            if not company_ids or act.get("company_id") in company_ids:
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
