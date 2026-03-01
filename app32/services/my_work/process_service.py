from typing import List, Dict, Any, Optional, Sequence, Set
import logging
from models import db
from models.process import Process, ProcessInstance
from models.company import Company
from .utils import (
    safe_int,
    match_employee_from_lookup,
    parse_activities_payload
)

logger = logging.getLogger(__name__)

def fetch_process_directory(company_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Fetch process directory for a list of companies.
    """
    if not company_ids:
        return []

    try:
        results = db.session.query(
            Process.id,
            Process.name,
            Process.code,
            Process.company_id,
            Company.name.label("company_name"),
            Company.client_code.label("company_code")
        ).join(Company, Company.id == Process.company_id, isouter=True)\
         .filter(Process.company_id.in_(company_ids))\
         .order_by(Company.name, Process.code.nullslast(), Process.name).all()

        processes = []
        for r in results:
            if r.id is None:
                continue
            
            processes.append({
                "id": r.id,
                "name": r.name or "Processo sem nome",
                "code": r.code.strip() if r.code else None,
                "company_id": r.company_id,
                "company_name": r.company_name or "Empresa",
                "company_code": r.company_code,
            })
        return processes
    except Exception as e:
        logger.error(f"Error fetching process directory: {e}")
        return []

def fetch_normalized_process_rows(
    employee_ids: Optional[Sequence[int]] = None,
    company_ids: Optional[Sequence[int]] = None,
    process_ids: Optional[Sequence[int]] = None,
    employee_lookup: Optional[Dict[str, Set[int]]] = None,
    employee_directory: Optional[Dict[int, Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Fetch and normalize process instances activities.
    """
    query = db.session.query(
        ProcessInstance,
        Company.name.label("company_name"),
        Company.client_code.label("company_code"),
        Process.name.label("process_name"),
        Process.code.label("process_code")
    ).join(Company, Company.id == ProcessInstance.company_id, isouter=True)\
     .join(Process, Process.id == ProcessInstance.process_id, isouter=True)

    if company_ids:
        query = query.filter(ProcessInstance.company_id.in_(company_ids))
    if process_ids:
        query = query.filter(ProcessInstance.process_id.in_(process_ids))

    query = query.order_by(ProcessInstance.due_date.nullslast(), ProcessInstance.updated_at.desc())
    
    rows = query.all()
    results = []
    
    target_employee_ids = set(safe_int(eid) for eid in (employee_ids or []) if safe_int(eid))

    for r in rows:
        pi = r.ProcessInstance
        collaborators = parse_activities_payload(pi.collaborators_json)
        
        if employee_lookup:
            for collab in collaborators:
                collab_id = safe_int(collab.get("id") or collab.get("employee_id"))
                if not collab_id:
                    match = match_employee_from_lookup(
                        collab.get("name") or collab.get("email"), employee_lookup
                    )
                    if match:
                        collab["id"] = match
                        collab["employee_id"] = match
        
        if target_employee_ids:
            collab_ids = {
                safe_int(c.get("id") or c.get("employee_id")) 
                for c in collaborators
            }
            if not ({cid for cid in collab_ids if cid} & target_employee_ids):
                continue

        data = {
            "instance_id": pi.id,
            "company_id": pi.company_id,
            "company_name": r.company_name,
            "company_code": r.company_code,
            "process_id": pi.process_id,
            "process_name": r.process_name,
            "process_code": r.process_code,
            "title": pi.title,
            "description": pi.description,
            "status": pi.status or 'pending',
            "priority": (pi.priority or 'normal').lower(),
            "deadline_date": pi.due_date,
            "estimated_hours": pi.estimated_hours,
            "worked_hours": pi.actual_hours or 0,
            "collaborators_json": collaborators
        }
        results.append(_process_row_from_normalized(data))

    return results

def _process_row_from_normalized(data: Dict[str, Any]) -> Dict[str, Any]:
    """Converts normalized process data to legacy structure."""
    return {
        "id": data.get("instance_id"),
        "company_id": data.get("company_id"),
        "company_name": data.get("company_name"),
        "company_code": data.get("company_code"),
        "process_id": data.get("process_id"),
        "process_name": data.get("process_name"),
        "process_code": data.get("process_code"),
        "title": data.get("title"),
        "description": data.get("description"),
        "status": data.get("status"),
        "priority": data.get("priority"),
        "deadline_date": data.get("deadline_date"),
        "deadline": data.get("deadline_date").isoformat() if hasattr(data.get("deadline_date"), 'isoformat') else data.get("deadline_date"),
        "estimated_hours": data.get("estimated_hours"),
        "worked_hours": data.get("worked_hours"),
        "collaborators_json": data.get("collaborators_json"),
        "type": "process"
    }
