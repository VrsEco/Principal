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
                    "process": {"total": 0, "positive": 0, "negative": 0, "count": 0},
                    "project": {"total": 0, "positive": 0, "negative": 0, "count": 0},
                    "overall": {"total": 0, "positive": 0, "negative": 0, "count": 0}
                },
                "delivery_records": {"project": [], "process": []},
                "occurrence_records": {"positive": [], "negative": []}
            }

        # 2. Fetch Project Data
        # Join ProjectTask -> Project to filter by company
        # Join ProjectActivityCollaborator to filter by employee
        
        # We need tasks that have collaborators
        # Using db.session.query for better control
        p_tasks = db.session.query(
            ProjectTask, 
            Project, 
            ProjectActivityCollaborator
        ).join(
            Project, ProjectTask.project_id == Project.id
        ).join(
            ProjectActivityCollaborator, ProjectTask.id == ProjectActivityCollaborator.activity_id
        ).filter(
            Project.company_id == company_id,
            ProjectActivityCollaborator.is_deleted == False
        ).all()

        today = date.today()

        for task, project, collab in p_tasks:
            emp_id = collab.employee_id
            if emp_id not in results:
                continue
            
            # Determine status
            is_completed = task.stage in ['completed', 'archived'] or task.status == 'completed'
            
            # Determine lateness
            # Logic: if completed, check completion_date vs due_date
            # if not completed, check today vs due_date
            
            due_date = task.due_date
            # Ensure due_date is date
            if isinstance(due_date, datetime):
                due_date = due_date.date()
                
            completion_date = task.completion_date
            
            is_late = False
            if due_date:
                if is_completed:
                    if completion_date:
                        # Convert to date if datetime
                         comp_d = completion_date.date() if isinstance(completion_date, datetime) else completion_date
                         is_late = comp_d > due_date
                else:
                    is_late = today > due_date

            # Points calculation (using score_weight)
            points = float(task.score_weight or 1.0)
            
            # Update Stats
            if is_completed:
                results[emp_id]["completed"]["total"] += 1
                if is_late:
                    results[emp_id]["completed"]["late"] += 1
                else:
                    results[emp_id]["completed"]["on_time"] += 1
                
                # Update Scores (only for completed items usually, but let's include all or check logic.
                # Usually efficiency score is based on DELIVERIES.
                
                results[emp_id]["delivery_scores"]["project"]["count"] += 1
                
                cat = 'on_time'
                if is_late:
                    cat = 'late_completed' # or late_pending if not completed
                    points = -points # Negative score for late? Or partial?
                    # Let's assume late = negative score for simplicity or 0.
                    # App31 template implies positive/negative scores.
                    # Usually: OnTime = +Points, Late = -Points
                    results[emp_id]["delivery_scores"]["project"]["negative"] += abs(points)
                    results[emp_id]["delivery_scores"]["project"]["total"] -= abs(points)
                else:
                    results[emp_id]["delivery_scores"]["project"]["positive"] += points
                    results[emp_id]["delivery_scores"]["project"]["total"] += points
                
                # Add Record
                results[emp_id]["delivery_records"]["project"].append({
                    "project_code": f"PROJ-{project.id}",
                    "project_name": project.name,
                    "activity_title": task.what,
                    "category": cat,
                    "due_date": due_date.isoformat() if due_date else None,
                    "completion_date": completion_date.isoformat() if completion_date else None,
                    "points": points,
                    "weight": float(task.score_weight or 1)
                })

            else:
                results[emp_id]["in_progress"]["total"] += 1
                if is_late:
                    results[emp_id]["in_progress"]["late"] += 1
                else:
                    results[emp_id]["in_progress"]["on_time"] += 1

        # 3. Fetch Process Instances
        # ProcessInstance has executor_id and collaborators_json
        instances = ProcessInstance.query.filter_by(company_id=company_id).all()
        
        for inst in instances:
            # Identify employees involved
            involved_ids = set()
            if inst.executor_id:
                involved_ids.add(inst.executor_id)
            if inst.responsible_id:
                involved_ids.add(inst.responsible_id)
            # Parse JSON if needed, though usually executor is main
            if inst.collaborators_json:
                try:
                    collabs = inst.collaborators_json if isinstance(inst.collaborators_json, list) else json.loads(inst.collaborators_json)
                    for c_id in collabs:
                        involved_ids.add(int(c_id))
                except:
                    pass
            
            for emp_id in involved_ids:
                if emp_id not in results:
                    continue
                
                is_completed = inst.status in ['completed', 'finished', 'stable']
                due_date = inst.due_date
                # Ensure due_date is date
                if isinstance(due_date, datetime):
                    due_date = due_date.date()

                completion_date = inst.completed_at # DateTime
                
                # Convert completion_date to date
                comp_d = None
                if completion_date:
                    comp_d = completion_date.date() if isinstance(completion_date, datetime) else completion_date

                is_late = False
                if due_date:
                    if is_completed:
                        if comp_d:
                            is_late = comp_d > due_date
                    else:
                        is_late = today > due_date

                points = float(inst.score_weight or 1.0)

                if is_completed:
                    results[emp_id]["completed"]["total"] += 1
                    if is_late:
                        results[emp_id]["completed"]["late"] += 1
                    else:
                        results[emp_id]["completed"]["on_time"] += 1
                    
                    results[emp_id]["delivery_scores"]["process"]["count"] += 1
                    
                    cat = 'on_time'
                    if is_late:
                        cat = 'late_completed'
                        points = -points
                        results[emp_id]["delivery_scores"]["process"]["negative"] += abs(points)
                        results[emp_id]["delivery_scores"]["process"]["total"] -= abs(points)
                    else:
                        results[emp_id]["delivery_scores"]["process"]["positive"] += points
                        results[emp_id]["delivery_scores"]["process"]["total"] += points

                    # Add Record
                    process_name = inst.process_rel.name if inst.process_rel else "Processo"
                    results[emp_id]["delivery_records"]["process"].append({
                        "process_name": process_name,
                        "instance_title": inst.title,
                        "category": cat,
                        "due_date": due_date.isoformat() if due_date else None,
                        "completion_date": completion_date.isoformat() if completion_date else None,
                        "points": points,
                        "weight": float(inst.score_weight or 1)
                    })

                else:
                    results[emp_id]["in_progress"]["total"] += 1
                    if is_late:
                        results[emp_id]["in_progress"]["late"] += 1
                    else:
                        results[emp_id]["in_progress"]["on_time"] += 1

        # 4. Fetch Occurrences
        occurrences = Occurrence.query.filter_by(company_id=company_id).all()
        for occ in occurrences:
             # Identify employees involved
            involved_ids = set()
            if occ.employee_id:
                involved_ids.add(occ.employee_id)
            if occ.collaborators_ids:
                try:
                    c_ids = occ.collaborators_ids if isinstance(occ.collaborators_ids, list) else json.loads(occ.collaborators_ids)
                    for c_id in c_ids:
                        involved_ids.add(int(c_id))
                except:
                    pass
            
            for emp_id in involved_ids:
                if emp_id not in results:
                    continue
                
                score = occ.score or 0
                occ_type = (occ.type or '').lower() # positive, negative
                
                if 'positiv' in occ_type:
                    results[emp_id]["positive_occurrences"]["count"] += 1
                    results[emp_id]["positive_occurrences"]["score"] += score
                    results[emp_id]["occurrence_records"]["positive"].append({
                        "type": occ.type,
                        "title": occ.title,
                        "score": score,
                        "created_at": occ.created_at.isoformat() if hasattr(occ.created_at, 'isoformat') else occ.created_at
                    })
                elif 'negativ' in occ_type:
                    results[emp_id]["negative_occurrences"]["count"] += 1
                    results[emp_id]["negative_occurrences"]["score"] += score # Usually negative occurrences score is subtracted, but stored as positive int?
                    # If score is stored as negative in DB, add it. If positive, subtract it.
                    # Assuming stored as absolute value, and type defines sign.
                    # The template expects 'score' to be displayed.
                    # Logic above: total = pos + neg.
                    # If neg score is positive integer, then total = pos + neg (where neg should be negative number).
                    # Let's assume we store it as NEGATIVE number calculation for TOTAL.
                    
                    neg_val = -abs(score)
                    results[emp_id]["negative_occurrences"]["score"] += neg_val
                    
                    results[emp_id]["occurrence_records"]["negative"].append({
                        "type": occ.type,
                        "title": occ.title,
                        "score": neg_val,
                        "created_at": occ.created_at.isoformat() if hasattr(occ.created_at, 'isoformat') else occ.created_at
                    })
        
        # Calculate Overall Totals
        for emp_id, data in results.items():
            data["delivery_scores"]["overall"]["positive"] = (
                data["delivery_scores"]["project"]["positive"] + 
                data["delivery_scores"]["process"]["positive"]
            )
            data["delivery_scores"]["overall"]["negative"] = (
                data["delivery_scores"]["project"]["negative"] + 
                data["delivery_scores"]["process"]["negative"]
            )
            data["delivery_scores"]["overall"]["total"] = (
                data["delivery_scores"]["project"]["total"] + 
                data["delivery_scores"]["process"]["total"]
            )
            data["delivery_scores"]["overall"]["count"] = (
                data["delivery_scores"]["project"]["count"] + 
                data["delivery_scores"]["process"]["count"]
            )

        return list(results.values())
