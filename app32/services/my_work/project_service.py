from typing import List, Dict, Any, Optional, Sequence, Set, Tuple
import logging
import json
from models import db
from models.project import Project
from models.company import Company
from models.plan import Plan
from .utils import (
    safe_int, 
    parse_activities_payload, 
    enrich_activity_assignments, 
    extract_activity_employee_ids
)
from utils.project_activity_utils import normalize_project_activities

logger = logging.getLogger(__name__)

def fetch_project_directory(company_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Fetch project directory for a list of companies.
    Uses unified 'company_projects' table through Project model.
    """
    if not company_ids:
        return []

    try:
        results = db.session.query(
            Project.id,
            Project.name.label("title"),
            Project.company_id,
            Company.name.label("company_name"),
            Company.client_code.label("company_code")
        ).join(Company, Company.id == Project.company_id, isouter=True)\
         .filter(Project.company_id.in_(company_ids))\
         .order_by(Company.name, Project.name).all()

        projects = []
        for r in results:
            if r.id is None:
                continue
            
            project_code = f"{r.company_code or (r.company_name[:2].upper() if r.company_name else 'CP')}.J.{r.id}"

            projects.append({
                "id": r.id,
                "title": r.title or "Projeto sem título",
                "code": project_code,
                "company_id": r.company_id,
                "company_name": r.company_name or "Empresa",
                "company_code": r.company_code,
            })
        return projects
    except Exception as e:
        logger.error(f"Error fetching project directory: {e}")
        return []

def fetch_normalized_project_rows(
    employee_ids: Optional[Sequence[int]] = None,
    company_ids: Optional[Sequence[int]] = None,
    project_ids: Optional[Sequence[int]] = None,
    employee_lookup: Optional[Dict[str, Set[int]]] = None,
    employee_directory: Optional[Dict[int, Dict[str, Any]]] = None,
    include_inactive: bool = False
) -> List[Dict[str, Any]]:
    """
    Fetch and normalize project activities from both table activities and legacy JSON.
    """
    # 1. Fetch from normalized tables (project_tasks)
    table_activities = []
    
    from models.project import ProjectTask, Project
    from models.employee import Employee
    query = db.session.query(
        ProjectTask, Project, Plan.title.label("plan_name"), Plan.mode.label("plan_mode"),
        Company.name.label("company_name"), Company.client_code.label("company_code"),
        Employee.name.label("employee_name_joined")
    ).join(Project, Project.id == ProjectTask.project_id)\
     .outerjoin(Plan, Plan.id == Project.plan_id)\
     .outerjoin(Company, Company.id == Project.company_id)\
     .outerjoin(Employee, Employee.id == ProjectTask.employee_id)
     
    if company_ids:
        query = query.filter(Project.company_id.in_(company_ids))
    if project_ids:
        query = query.filter(ProjectTask.project_id.in_(project_ids))
    
    if not include_inactive:
        # Hide completed, cancelled and archived projects globally
        query = query.filter(Project.status.not_in(['completed', 'cancelled', 'archived']))
        
    target_employee_ids = set(safe_int(eid) for eid in (employee_ids or []) if safe_int(eid))
    if target_employee_ids:
        # Include tasks assigned to these employees OR tasks with no employee assigned (NULL)
        # NULL tasks belong to the company scope and should be visible to responsible managers
        from sqlalchemy import or_
        query = query.filter(
            or_(
                ProjectTask.employee_id.in_(target_employee_ids),
                ProjectTask.employee_id == None
            )
        )

    for pt, prj, plan_name, plan_mode, company_name, company_code, employee_name_joined in query.all():
        # Anti-N+1: Prevent pt.code and prj.code from querying the database
        c_code = company_code or (company_name[:2].upper() if company_name else 'CP')
        prj_code = f"{c_code}.J.{prj.id}"
        pt_code = f"{c_code}.J.{prj.id}.{pt.id}"
        emp_name = employee_name_joined or pt.who or "Sem responsável"
        
        table_activities.append({
            "id": pt.id,
            "company_id": prj.company_id,
            "plan_id": prj.plan_id,
            "title": pt.what or prj.name,
            "description": pt.how,
            "status": pt.status,
            "priority": pt.priority,
            "responsible_id": pt.employee_id,
            "responsible_name": emp_name,
            "executor_id": pt.employee_id,
            "executor_name": emp_name,
            "start_date": prj.created_at.isoformat() if hasattr(prj.created_at, 'isoformat') else prj.created_at,
            "end_date": prj.deadline.isoformat() if hasattr(prj.deadline, 'isoformat') else prj.deadline,
            "deadline_date": pt.due_date,
            "deadline": pt.due_date.isoformat() if hasattr(pt.due_date, 'isoformat') else pt.due_date,
            "estimated_hours": float(pt.estimated_hours or 0),
            "worked_hours": float(pt.worked_hours or 0),
            "company_name": company_name,
            "company_code": company_code,
            "plan_name": plan_name,
            "plan_mode": plan_mode,
            "project_id": prj.id,
            "project_code": prj_code,
            "project_title": prj.name,
            "activity_code": pt_code,
            "metadata": None,
            "type": "project"
        })
    
    # 2. Fetch from legacy JSON activities
    legacy_activities = fetch_project_rows_from_json(
        employee_ids=employee_ids,
        company_ids=company_ids,
        project_ids=project_ids,
        employee_lookup=employee_lookup,
        employee_directory=employee_directory,
        include_inactive=include_inactive
    )
    
    return table_activities + legacy_activities

def fetch_project_rows_from_json(
    employee_ids: Optional[Sequence[int]] = None,
    company_ids: Optional[Sequence[int]] = None,
    project_ids: Optional[Sequence[int]] = None,
    employee_lookup: Optional[Dict[str, Set[int]]] = None,
    employee_directory: Optional[Dict[int, Dict[str, Any]]] = None,
    include_inactive: bool = False
) -> List[Dict[str, Any]]:
    """
    Fetch project activities serialized in the 'activities' JSON column.
    """
    query = db.session.query(
        Project,
        Plan.title.label("plan_name"),
        Plan.mode.label("plan_mode"),
        Company.name.label("company_name"),
        Company.client_code.label("company_code")
    ).join(Plan, Plan.id == Project.plan_id, isouter=True)\
     .join(Company, Company.id == Project.company_id, isouter=True)
    
    if company_ids:
        query = query.filter(Project.company_id.in_(company_ids))
    if project_ids:
        query = query.filter(Project.id.in_(project_ids))
    
    if not include_inactive:
        query = query.filter(Project.status.not_in(['completed', 'cancelled', 'archived']))
    
    rows = query.all()
    results = []
    
    target_employee_ids = set(safe_int(eid) for eid in (employee_ids or []) if safe_int(eid))

    for r in rows:
        project = r.Project
        activities_raw = getattr(project, "activities", None)
        activities = parse_activities_payload(activities_raw)
        
        normalized, _, _ = normalize_project_activities(
            activities, project.code, r.company_code
        )
        
        for activity in normalized:
            if employee_lookup and employee_directory:
                enrich_activity_assignments(activity, employee_lookup, employee_directory)
            
            # Filter by employee if applicable
            if target_employee_ids:
                if not (extract_activity_employee_ids(activity) & target_employee_ids):
                    continue
            
            payload = _build_activity_row_from_json(project, r, activity)
            results.append(_project_activity_row_from_normalized(payload))
            
    return results

def _build_activity_row_from_json(project: Project, r: Any, activity: Dict[str, Any]) -> Dict[str, Any]:
    """Mount structure compatible with legacy serializers."""
    deadline = activity.get("deadline") or activity.get("when") or activity.get("due_date") or activity.get("completion_date")
    title = activity.get("title") or activity.get("name") or activity.get("what") or project.name
    description = activity.get("description") or activity.get("notes") or activity.get("how") or activity.get("observations")
    
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
        "project_id": project.id,
        "responsible_id": safe_int(activity.get("responsible_id")),
        "responsible_name": activity.get("responsible_name") or activity.get("responsible") or activity.get("who") or activity.get("owner"),
        "executor_id": safe_int(activity.get("executor_id")),
        "executor_name": activity.get("executor_name") or activity.get("executor") or activity.get("assigned_to") or activity.get("assigned") or activity.get("executor_responsible"),
        "company_id": project.company_id,
        "plan_id": project.plan_id,
        "project_title": project.name,
        "project_description": getattr(project, "notes", None),
        "project_status": project.status,
        "project_priority": project.priority,
        "start_date": getattr(project, "created_at", None),
        "end_date": getattr(project, "deadline", None),
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "project_code": project.code,
        "plan_name": r.plan_name,
        "plan_mode": r.plan_mode,
        "company_name": r.company_name,
    }

def _project_activity_row_from_normalized(row: Dict[str, Any]) -> Dict[str, Any]:
    """Converts normalized row into expected legacy structure."""
    return {
        "id": row.get("activity_id"),
        "company_id": row.get("company_id"),
        "plan_id": row.get("plan_id"),
        "title": row.get("activity_title") or row.get("project_title"),
        "description": row.get("activity_description") or row.get("project_description"),
        "status": row.get("activity_status") or row.get("project_status"),
        "priority": row.get("activity_priority") or row.get("project_priority"),
        "responsible_id": row.get("responsible_id"),
        "responsible_name": row.get("responsible_name"),
        "executor_id": row.get("executor_id"),
        "executor_name": row.get("executor_name"),
        "start_date": row.get("start_date"),
        "end_date": row.get("end_date"),
        "deadline_date": row.get("activity_deadline") or row.get("end_date"),
        "deadline": row.get("activity_deadline") or row.get("end_date"),
        "estimated_hours": row.get("estimated_hours"),
        "worked_hours": row.get("worked_hours"),
        "company_name": row.get("company_name"),
        "company_code": row.get("company_code"),
        "plan_name": row.get("plan_name"),
        "plan_mode": row.get("plan_mode"),
        "project_id": row.get("project_id"),
        "project_code": row.get("project_code"),
        "project_title": row.get("project_title"),
        "activity_code": row.get("activity_code"),
        "metadata": row.get("metadata"),
        "type": "project",
    }
