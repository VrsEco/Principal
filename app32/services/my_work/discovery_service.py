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
    employee_ids: Optional[List[int]] = None
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
        return []

    # 2. Setup resolution based on scope
    target_employee_ids = []
    if scope == "me":
        if my_employee_ids:
            target_employee_ids = my_employee_ids
        else:
            logger.warning(f"⚠️ Scale 'me' requested but no employee records for user {user_id}")
            return []
    elif scope == "team":
        target_employee_ids = employee_ids or []
    elif scope == "company":
        target_employee_ids = [] # Empty means no filter by employee
    
    # 3. Build lookup for identity resolution
    directory, lookup = build_employee_lookup_v2(company_ids)
    
    # 4. Fetch project activities
    project_rows = fetch_normalized_project_rows(
        employee_ids=target_employee_ids or filters.get("employee_ids"),
        company_ids=company_ids,
        project_ids=filters.get("project_ids"),
        employee_lookup=lookup,
        employee_directory=directory
    )
    logger.info(f"📋 Found {len(project_rows)} project activities for companies {company_ids}")
    
    # 5. Fetch process activities
    process_rows = fetch_normalized_process_rows(
        employee_ids=target_employee_ids or filters.get("employee_ids"),
        company_ids=company_ids,
        process_ids=filters.get("process_ids"),
        employee_lookup=lookup,
        employee_directory=directory
    )
    logger.info(f"⚙️ Found {len(process_rows)} process activities for companies {company_ids}")
    
    # 6. Combine and Enrich
    all_activities = project_rows + process_rows
    logger.info(f"✅ Total activities found: {len(all_activities)}")
    
    today = date.today()
    for act in all_activities:
        # 6.1 Calculate Overdue
        deadline_val = act.get("deadline")
        status = (act.get("status") or "").lower()
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
                    act["is_overdue"] = d_dt < today and status not in ("completed", "done")
                else:
                    act["is_overdue"] = False
            except Exception as e:
                logger.warning(f"Error parsing date {deadline_val}: {e}")
                act["is_overdue"] = False
        else:
            act["is_overdue"] = False

        # 6.2 Calculate Assignment info (Crucial for Frontend V2)
        if scope == 'me':
            act["viewer_is_directly_assigned"] = True
            if act.get("type") == "project":
                if act.get("executor_id") in my_employee_ids:
                     act["assignment"] = {"type": "executor", "label": "⚙️ Executor"}
                else:
                     act["assignment"] = {"type": "responsible", "label": "👤 Responsável"}
            else:
                act["assignment"] = {"type": "assigned", "label": "⚙️ Executor"}
        else:
            # Check if user is among collaborators for 'team' or 'company' scope
            is_assigned = False
            if act.get("type") == "project":
                is_assigned = act.get("responsible_id") in my_employee_ids or act.get("executor_id") in my_employee_ids
            else:
                collabs = act.get("collaborators_json") or []
                is_assigned = any((c.get("id") or c.get("employee_id")) in my_employee_ids for c in collabs)
            
            act["viewer_is_directly_assigned"] = is_assigned
            if is_assigned:
                 act["assignment"] = {"type": "assigned", "label": "⚙️ Atribuído"}
            else:
                 act["assignment"] = {"type": "none", "label": ""}

    # 7. Sort
    # Sorting logic - safer approach to handle mix of date/datetime/None
    def get_sort_key(x):
        d_val = x.get("deadline_date")
        d_obj = None
        if isinstance(d_val, str):
            try:
                d_obj = date.fromisoformat(d_val[:10])
            except:
                pass
        elif hasattr(d_val, 'date'):
            d_obj = d_val.date()
        elif isinstance(d_val, date):
            d_obj = d_val
        
        return (d_obj or date(9999, 12, 31), safe_int(x.get("id")) or 0)

    all_activities.sort(key=get_sort_key)

    return all_activities
