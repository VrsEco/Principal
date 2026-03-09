from flask import jsonify, request
from flask_restful import Resource
from models import db, Employee, Project, ProjectTask, ProjectActivityCollaborator, ProcessInstance, Process, Occurrence, ActivityWorkLog
from datetime import datetime, date, timedelta
from sqlalchemy import func, text as sql_text
import json


class EfficiencyCollaborators(Resource):
    @staticmethod
    def _parse_period():
        start_raw = request.args.get("start_date")
        end_raw = request.args.get("end_date")

        def _parse(raw_value):
            if not raw_value:
                return None
            return datetime.strptime(raw_value, "%Y-%m-%d").date()

        today = date.today()
        start_date = _parse(start_raw)
        end_date = _parse(end_raw)

        if not start_date and not end_date:
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        elif start_date and not end_date:
            end_date = start_date
        elif end_date and not start_date:
            start_date = end_date

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        return start_date, end_date

    @staticmethod
    def _business_days_between(start_date, end_date):
        total = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                total += 1
            current += timedelta(days=1)
        return total

    def get(self, company_id):
        start_date, end_date = self._parse_period()
        business_days = self._business_days_between(start_date, end_date)
        # 1. Fetch Employees
        employees = Employee.query.filter_by(company_id=company_id).all()

        # Initialize results structure
        results = {}
        for employee in employees:
            emp_id = employee.id
            weekly_hours = float(employee.weekly_hours or 40.0)
            contracted_hours = round((weekly_hours / 5.0) * business_days, 2) if weekly_hours else 0.0
            results[emp_id] = {
                "employee_name": employee.name,
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
                "occurrence_records": {"positive": [], "negative": []},
                "period_hours": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "business_days": business_days,
                    "weekly_hours": round(weekly_hours, 2),
                    "contracted": contracted_hours,
                    "worked_project": 0.0,
                    "worked_process": 0.0,
                    "worked_total": 0.0,
                    "free_capacity": contracted_hours,
                    "utilization_percent": 0.0,
                    "details": {"project": [], "process": []},
                }
            }

        today = date.today()

        log_rows = (
            db.session.query(
                ActivityWorkLog.employee_id,
                ActivityWorkLog.activity_type,
                func.coalesce(func.sum(ActivityWorkLog.hours_worked), 0).label("total_hours"),
            )
            .join(Employee, Employee.id == ActivityWorkLog.employee_id)
            .filter(
                Employee.company_id == company_id,
                ActivityWorkLog.work_date >= start_date,
                ActivityWorkLog.work_date <= end_date,
            )
            .group_by(ActivityWorkLog.employee_id, ActivityWorkLog.activity_type)
            .all()
        )

        for row in log_rows:
            if row.employee_id not in results:
                continue
            hours = round(float(row.total_hours or 0), 2)
            if row.activity_type == "project":
                results[row.employee_id]["period_hours"]["worked_project"] += hours
            elif row.activity_type in ("process", "process_instance"):
                results[row.employee_id]["period_hours"]["worked_process"] += hours
            results[row.employee_id]["period_hours"]["worked_total"] += hours

        detailed_logs = (
            ActivityWorkLog.query
            .join(Employee, Employee.id == ActivityWorkLog.employee_id)
            .filter(
                Employee.company_id == company_id,
                ActivityWorkLog.work_date >= start_date,
                ActivityWorkLog.work_date <= end_date,
            )
            .order_by(ActivityWorkLog.work_date.desc(), ActivityWorkLog.created_at.desc())
            .all()
        )

        project_ids = sorted({int(log.activity_id) for log in detailed_logs if log.activity_type == "project"})
        process_instance_ids = sorted({int(log.activity_id) for log in detailed_logs if log.activity_type in ("process", "process_instance")})

        project_task_map = {}
        if project_ids:
            project_tasks = (
                ProjectTask.query
                .join(Project, Project.id == ProjectTask.project_id)
                .filter(Project.company_id == company_id, ProjectTask.id.in_(project_ids))
                .all()
            )
            project_task_map = {task.id: task for task in project_tasks}

        process_instance_map = {}
        if process_instance_ids:
            process_instances = (
                ProcessInstance.query
                .filter(ProcessInstance.company_id == company_id, ProcessInstance.id.in_(process_instance_ids))
                .all()
            )
            process_instance_map = {instance.id: instance for instance in process_instances}

        for log in detailed_logs:
            employee_data = results.get(log.employee_id)
            if not employee_data:
                continue

            hours = round(float(log.hours_worked or 0), 2)
            base_record = {
                "activity_id": log.activity_id,
                "hours_worked": hours,
                "work_date": log.work_date.isoformat() if hasattr(log.work_date, "isoformat") else log.work_date,
                "description": log.description or "",
                "created_at": log.created_at.isoformat() if hasattr(log.created_at, "isoformat") else log.created_at,
            }

            if log.activity_type == "project":
                task = project_task_map.get(int(log.activity_id))
                project = task.project if task else None
                employee_data["period_hours"]["details"]["project"].append({
                    **base_record,
                    "project_name": project.name if project else "Projeto",
                    "project_code": getattr(project, "code", None) if project else None,
                    "activity_title": getattr(task, "what", None) if task else None,
                })
            elif log.activity_type in ("process", "process_instance"):
                instance = process_instance_map.get(int(log.activity_id))
                process_rel = instance.process_rel if instance else None
                employee_data["period_hours"]["details"]["process"].append({
                    **base_record,
                    "process_name": process_rel.name if process_rel else "Processo",
                    "process_code": getattr(process_rel, "code", None) if process_rel else None,
                    "instance_title": getattr(instance, "title", None) if instance else None,
                })

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
        collaborators_column_exists = db.session.execute(
            sql_text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'occurrences'
                      AND column_name = 'collaborators_ids'
                )
            """)
        ).scalar()

        occurrences_sql = """
            SELECT id, company_id, employee_id, title, type, score, created_at,
                   {collaborators_field}
            FROM occurrences
            WHERE company_id = :company_id
        """.format(
            collaborators_field=(
                "collaborators_ids"
                if collaborators_column_exists
                else "NULL::text AS collaborators_ids"
            )
        )

        occurrences = db.session.execute(
            sql_text(occurrences_sql),
            {"company_id": company_id},
        ).mappings().all()

        for occ in occurrences:
            involved_ids = set()
            if occ.get("employee_id"):
                involved_ids.add(int(occ["employee_id"]))
            collaborators_ids = occ.get("collaborators_ids")
            if collaborators_ids:
                try:
                    c_ids = collaborators_ids if isinstance(collaborators_ids, list) else json.loads(collaborators_ids)
                    for cid in c_ids:
                        involved_ids.add(int(cid))
                except Exception:
                    pass
            for emp_id in involved_ids:
                if emp_id not in results:
                    continue
                score = occ.get("score") or 0
                occ_type = str(occ.get("type") or '').lower()
                created_at = occ.get("created_at")
                created_at_value = created_at.isoformat() if hasattr(created_at, 'isoformat') else created_at
                if 'positiv' in occ_type:
                    results[emp_id]["positive_occurrences"]["count"] += 1
                    results[emp_id]["positive_occurrences"]["score"] += score
                    results[emp_id]["occurrence_records"]["positive"].append({"type": occ.get("type"), "title": occ.get("title"), "score": score, "created_at": created_at_value})
                elif 'negativ' in occ_type:
                    results[emp_id]["negative_occurrences"]["count"] += 1
                    neg_val = -abs(score)
                    results[emp_id]["negative_occurrences"]["score"] += neg_val
                    results[emp_id]["occurrence_records"]["negative"].append({"type": occ.get("type"), "title": occ.get("title"), "score": neg_val, "created_at": created_at_value})
        
        # 5. Calculate Overall Totals
        for emp_id, data in results.items():
            ds = data["delivery_scores"]
            ds["overall"]["positive"] = ds["project"]["positive"] + ds["process"]["positive"]
            ds["overall"]["negative"] = ds["project"]["negative"] + ds["process"]["negative"]
            ds["overall"]["total"] = ds["project"]["total"] + ds["process"]["total"]
            ds["overall"]["count"] = ds["project"]["count"] + ds["process"]["count"]
            ds["overall"]["potential"] = ds["project"]["potential"] + ds["process"]["potential"]
            ds["overall"]["assigned"] = ds["project"]["assigned"] + ds["process"]["assigned"]

            period_hours = data["period_hours"]
            period_hours["worked_project"] = round(period_hours["worked_project"], 2)
            period_hours["worked_process"] = round(period_hours["worked_process"], 2)
            period_hours["worked_total"] = round(period_hours["worked_total"], 2)
            period_hours["free_capacity"] = round(period_hours["contracted"] - period_hours["worked_total"], 2)
            period_hours["utilization_percent"] = round((period_hours["worked_total"] / period_hours["contracted"] * 100) if period_hours["contracted"] > 0 else 0.0, 1)

        return list(results.values())




