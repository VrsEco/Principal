from flask import jsonify, request
from flask_restful import Resource
from models import db, Employee, Project, ProjectTask, ProjectActivityCollaborator, ProcessInstance, Process, Occurrence
from datetime import datetime, date
import json

class EfficiencyCollaborators(Resource):
    def get(self, company_id):
        # 1. Fetch Employees
        employees = Employee.query.filter_by(company_id=company_id).all()
        emp_map = {e.id: e.name for e in employees}
        
        # Initialize results structure
        results = {}
        for emp_id, name in emp_map.items():
            results[emp_id] = {
                "employee_name": name,
                "in_progress": {"total": 0, "on_time": 0, "late": 0},
                "completed": {"total": 0, "on_time": 0, "late": 0},
                "positive_occurrences": {"count": 0, "score": 0},
                "negative_occurrences": {"count": 0, "score": 0},
                "delivery_scores": {
                    "process": {"total": 0, "positive": 0, "negative": 0, "count": 0, "potential": 0, "assigned": 0},
                    "project": {"total": 0, "positive": 0, "negative": 0, "count": 0, "potential": 0, "assigned": 0},
                    "overall": {"total": 0, "positive": 0, "negative": 0, "count": 0, "potential": 0, "assigned": 0}
                },
                "delivery_records": {"project": [], "process": []},
                "occurrence_records": {"positive": [], "negative": []}
            }

        today = date.today()

        # 1.1 Fetch Performance Settings
        from models import CompanyPerformanceSettings
        settings = CompanyPerformanceSettings.query.filter_by(company_id=company_id).first()
        
        # Default settings if none configured
        ON_TIME_BASE = float(settings.on_time_score) if settings else 5.0
        LATE_FIXED_BASE = float(settings.late_score) if settings else -5.0
        DAILY_PENALTY_BASE = float(settings.daily_delay_penalty) if settings else -1.0

        # 2. Fetch Project Data (Inclusive)
        from models import ProjectTask, ProjectActivityCollaborator
        tasks = ProjectTask.query.join(Project).filter(Project.company_id == company_id).all()
        
        task_ids = [t.id for t in tasks]
        collabs = ProjectActivityCollaborator.query.filter(
            ProjectActivityCollaborator.activity_id.in_(task_ids) if task_ids else db.false(),
            ProjectActivityCollaborator.is_deleted == False
        ).all()
        
        task_collab_map = {}
        for c in collabs:
            if c.activity_id not in task_collab_map:
                task_collab_map[c.activity_id] = []
            task_collab_map[c.activity_id].append(c.employee_id)

        for task in tasks:
            project = task.project
            involved_ids = set()
            if task.employee_id: involved_ids.add(task.employee_id)
            if task.id in task_collab_map:
                for eid in task_collab_map[task.id]: involved_ids.add(eid)
            
            is_completed = task.stage in ['completed', 'archived'] or task.status == 'completed'
            due_date = task.due_date
            if isinstance(due_date, datetime): due_date = due_date.date()
            completion_date = task.completion_date

            is_late = False
            days_late = 0
            if due_date:
                if is_completed:
                    comp_d = completion_date.date() if isinstance(completion_date, datetime) else completion_date
                    if comp_d and comp_d > due_date:
                        is_late = True
                        days_late = (comp_d - due_date).days
                else:
                    if today > due_date:
                        is_late = True
                        days_late = (today - due_date).days

            multiplier = float(task.score_weight or 1.0)
            
            for emp_id in involved_ids:
                if emp_id not in results: continue
                
                # Assigned (Workload) ALWAYS sums at on-time potential
                results[emp_id]["delivery_scores"]["project"]["assigned"] += (ON_TIME_BASE * multiplier)
                
                if is_completed:
                    results[emp_id]["delivery_scores"]["project"]["potential"] += (ON_TIME_BASE * multiplier)
                    results[emp_id]["completed"]["total"] += 1
                    
                    if is_late:
                        results[emp_id]["completed"]["late"] += 1
                        # Dynamic Penalty: (Fixed + (Daily * Days)) * Importance
                        points = (LATE_FIXED_BASE + (DAILY_PENALTY_BASE * days_late)) * multiplier
                        cat = 'late_completed'
                        results[emp_id]["delivery_scores"]["project"]["negative"] += abs(points)
                    else:
                        results[emp_id]["completed"]["on_time"] += 1
                        points = ON_TIME_BASE * multiplier
                        cat = 'on_time'
                        results[emp_id]["delivery_scores"]["project"]["positive"] += points
                    
                    results[emp_id]["delivery_scores"]["project"]["total"] += points
                    results[emp_id]["delivery_scores"]["project"]["count"] += 1
                    results[emp_id]["delivery_records"]["project"].append({
                        "project_code": f"{project.code if hasattr(project, 'code') else 'PROJ-'+str(project.id)}",
                        "project_name": project.name,
                        "activity_title": task.what,
                        "category": cat,
                        "due_date": due_date.isoformat() if due_date else None,
                        "completion_date": completion_date.isoformat() if completion_date else None,
                        "points": points,
                        "weight": multiplier
                    })
                else:
                    results[emp_id]["in_progress"]["total"] += 1
                    if is_late:
                        results[emp_id]["in_progress"]["late"] += 1
                        # User requested to count in-progress late items penalties
                        points = (LATE_FIXED_BASE + (DAILY_PENALTY_BASE * days_late)) * multiplier
                        results[emp_id]["delivery_scores"]["project"]["total"] += points
                        results[emp_id]["delivery_scores"]["project"]["negative"] += abs(points)
                        # Potential must include it to keep consistency
                        results[emp_id]["delivery_scores"]["project"]["potential"] += (ON_TIME_BASE * multiplier)
                    else:
                        results[emp_id]["in_progress"]["on_time"] += 1

        # 3. Fetch Process Instances (Inclusive)
        from models import ProcessInstance, ProcessInstanceCollaborator
        instances = ProcessInstance.query.filter_by(company_id=company_id).all()
        
        inst_ids = [i.id for i in instances]
        p_collabs = ProcessInstanceCollaborator.query.filter(
            ProcessInstanceCollaborator.process_instance_id.in_(inst_ids) if inst_ids else db.false(),
            ProcessInstanceCollaborator.is_deleted == False
        ).all()
        
        inst_collab_map = {}
        for pc in p_collabs:
            if pc.process_instance_id not in inst_collab_map:
                inst_collab_map[pc.process_instance_id] = []
            inst_collab_map[pc.process_instance_id].append(pc.employee_id)

        for inst in instances:
            involved_ids = set()
            if inst.executor_id: involved_ids.add(inst.executor_id)
            if inst.responsible_id: involved_ids.add(inst.responsible_id)
            if inst.owner_employee_id: involved_ids.add(inst.owner_employee_id)
            if inst.collaborators_json:
                try:
                    c_ids = inst.collaborators_json if isinstance(inst.collaborators_json, list) else json.loads(inst.collaborators_json)
                    for cid in c_ids: 
                        try: involved_ids.add(int(cid))
                        except: pass
                except: pass
            if inst.id in inst_collab_map:
                for eid in inst_collab_map[inst.id]: involved_ids.add(eid)
            
            is_completed = inst.status in ['completed', 'finished', 'stable']
            due_date = inst.due_date
            if isinstance(due_date, datetime): due_date = due_date.date()
            completion_date = inst.completed_at
            comp_d = completion_date.date() if isinstance(completion_date, datetime) else completion_date

            is_late = False
            days_late = 0
            if due_date:
                if is_completed:
                    if comp_d and comp_d > due_date:
                        is_late = True
                        days_late = (comp_d - due_date).days
                else:
                    if today > due_date:
                        is_late = True
                        days_late = (today - due_date).days

            multiplier = float(inst.score_weight or 1.0)

            for emp_id in involved_ids:
                if emp_id not in results: continue
                
                results[emp_id]["delivery_scores"]["process"]["assigned"] += (ON_TIME_BASE * multiplier)
                
                if is_completed:
                    results[emp_id]["delivery_scores"]["process"]["potential"] += (ON_TIME_BASE * multiplier)
                    results[emp_id]["completed"]["total"] += 1
                    if is_late:
                        results[emp_id]["completed"]["late"] += 1
                        points = (LATE_FIXED_BASE + (DAILY_PENALTY_BASE * days_late)) * multiplier
                        cat = 'late_completed'
                        results[emp_id]["delivery_scores"]["process"]["negative"] += abs(points)
                    else:
                        results[emp_id]["completed"]["on_time"] += 1
                        points = ON_TIME_BASE * multiplier
                        cat = 'on_time'
                        results[emp_id]["delivery_scores"]["process"]["positive"] += points
                    
                    results[emp_id]["delivery_scores"]["process"]["total"] += points
                    results[emp_id]["delivery_scores"]["process"]["count"] += 1
                    process_name = inst.process_rel.name if inst.process_rel else "Processo"
                    results[emp_id]["delivery_records"]["process"].append({
                        "process_name": process_name,
                        "instance_title": inst.title,
                        "category": cat,
                        "due_date": due_date.isoformat() if due_date else None,
                        "completion_date": completion_date.isoformat() if completion_date else None,
                        "points": points,
                        "weight": multiplier
                    })
                else:
                    results[emp_id]["in_progress"]["total"] += 1
                    if is_late:
                        results[emp_id]["in_progress"]["late"] += 1
                        points = (LATE_FIXED_BASE + (DAILY_PENALTY_BASE * days_late)) * multiplier
                        results[emp_id]["delivery_scores"]["process"]["total"] += points
                        results[emp_id]["delivery_scores"]["process"]["negative"] += abs(points)
                        results[emp_id]["delivery_scores"]["process"]["potential"] += (ON_TIME_BASE * multiplier)
                    else:
                        results[emp_id]["in_progress"]["on_time"] += 1

        # 4. Fetch Occurrences
        occurrences = Occurrence.query.filter_by(company_id=company_id).all()
        for occ in occurrences:
            involved_ids = set()
            if occ.employee_id: involved_ids.add(occ.employee_id)
            if occ.collaborators_ids:
                try:
                    c_ids = occ.collaborators_ids if isinstance(occ.collaborators_ids, list) else json.loads(occ.collaborators_ids)
                    for cid in c_ids: involved_ids.add(int(cid))
                except: pass
            for emp_id in involved_ids:
                if emp_id not in results: continue
                score = occ.score or 0
                occ_type = (occ.type or '').lower()
                if 'positiv' in occ_type:
                    results[emp_id]["positive_occurrences"]["count"] += 1
                    results[emp_id]["positive_occurrences"]["score"] += score
                    results[emp_id]["occurrence_records"]["positive"].append({"type": occ.type, "title": occ.title, "score": score, "created_at": occ.created_at.isoformat() if hasattr(occ.created_at, 'isoformat') else occ.created_at})
                elif 'negativ' in occ_type:
                    results[emp_id]["negative_occurrences"]["count"] += 1
                    neg_val = -abs(score)
                    results[emp_id]["negative_occurrences"]["score"] += neg_val
                    results[emp_id]["occurrence_records"]["negative"].append({"type": occ.type, "title": occ.title, "score": neg_val, "created_at": occ.created_at.isoformat() if hasattr(occ.created_at, 'isoformat') else occ.created_at})
        
        # 5. Calculate Overall Totals
        for emp_id, data in results.items():
            ds = data["delivery_scores"]
            ds["overall"]["positive"] = ds["project"]["positive"] + ds["process"]["positive"]
            ds["overall"]["negative"] = ds["project"]["negative"] + ds["process"]["negative"]
            ds["overall"]["total"] = ds["project"]["total"] + ds["process"]["total"]
            ds["overall"]["count"] = ds["project"]["count"] + ds["process"]["count"]
            ds["overall"]["potential"] = ds["project"]["potential"] + ds["process"]["potential"]
            ds["overall"]["assigned"] = ds["project"]["assigned"] + ds["process"]["assigned"]

        return list(results.values())




