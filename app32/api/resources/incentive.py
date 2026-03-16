from flask_restful import Resource
from flask import request, session
import logging
logger = logging.getLogger(__name__)
from services.incentive_service import IncentiveService
from models import Indicator, IncentiveRuleSet, IncentiveCalculation, db
from datetime import date

class IncentiveIndicatorListResource(Resource):
    def get(self):
        company_id = session.get('active_company_id')
        if not company_id: return {"error": "No company active"}, 400
        
        indicators = Indicator.query.filter_by(company_id=company_id).all()
        return [
            {
                "id": i.id,
                "code": i.code,
                "name": i.name,
                "type": i.indicator_type,
                "source": i.source_module
            } for i in indicators
        ]

class IncentiveCalculationResource(Resource):
    def post(self):
        company_id = int(session.get('active_company_id', 0))
        data = request.get_json()
        
        rule_set_id = int(data.get('rule_set_id'))
        
        logger.info(f"Triggering calculation for Company {company_id}, Plan {rule_set_id} ({data.get('start_date')} to {data.get('end_date')})")
        
        # date strings in ISO format YYYY-MM-DD
        start_date = date.fromisoformat(data.get('start_date'))
        end_date = date.fromisoformat(data.get('end_date'))
        
        # Trigger harvesting before calculation
        IncentiveService.harvest_all_modules(company_id, start_date, end_date)
        
        result = IncentiveService.calculate_incentive(company_id, rule_set_id, start_date, end_date)
        return result

class IncentiveSpiderWebResource(Resource):
    def get(self):
        from models import (
            IncentiveRule, IncentiveRuleSet, Indicator,
            Employee, Process, Project, ProcessInstance, 
            ProcessInstanceCollaborator, ProjectTask, ProjectActivityCollaborator
        )

        company_id = session.get('active_company_id')
        if not company_id:
            return {"error": "No company active"}, 400
        company_id = int(company_id)

        nodes = {}  # id -> node dict
        links = []
        link_counter = {}  # node_id -> int (degree/connection count)

        def add_node(nid, label, ntype, meta=None):
            if nid not in nodes:
                nodes[nid] = {"id": nid, "label": label, "type": ntype, "degree": 0, **(meta or {})}
            if nid not in link_counter:
                link_counter[nid] = 0

        def add_link(src, tgt, label="", strength="normal"):
            if not src or not tgt: return
            # Evitar links duplicados
            for l in links:
                if l["source"] == src and l["target"] == tgt:
                    return
            links.append({"source": src, "target": tgt, "label": label, "strength": strength})
            link_counter[src] = link_counter.get(src, 0) + 1
            link_counter[tgt] = link_counter.get(tgt, 0) + 1

        # ── LAYER 1: Collaborators (Employees) ────────────────────────────────
        employees = Employee.query.filter_by(company_id=company_id, status='active').all()
        for emp in employees:
            add_node(f"colab_{emp.id}", emp.name, "collaborator", {"department": emp.department})

        # ── LAYER 2: Processes ────────────────────────────────────────────────
        processes = Process.query.filter_by(company_id=company_id, is_active=True).all()
        for proc in processes:
            add_node(f"proc_{proc.id}", proc.name, "process", {"kanban_stage": proc.kanban_stage})
            
            # Link to owner/responsible
            if proc.owner_employee_id:
                add_link(f"colab_{proc.owner_employee_id}", f"proc_{proc.id}", "dono", "direct")
            elif proc.responsible_id: # Fallback
                add_link(f"colab_{proc.responsible_id}", f"proc_{proc.id}", "responsável", "direct")

        # ── LAYER 3: Projects ─────────────────────────────────────────────────
        projects = Project.query.filter_by(company_id=company_id).all()
        for proj in projects:
            status_meta = {"status": proj.status, "progress": proj.progress}
            add_node(f"proj_{proj.id}", proj.name, "project", status_meta)
            
            # Link to owner (if we have a way to match string owner to employee)
            # For now, let's use ProjectActivityCollaborator for more precise links

        # ── LAYER 4: Indicators ───────────────────────────────────────────────
        indicators = Indicator.query.filter_by(company_id=company_id, is_active=True).all()
        ind_map_by_name = {ind.name.lower(): ind.id for ind in indicators}
        
        for ind in indicators:
            ind_node_id = f"ind_{ind.id}"
            add_node(ind_node_id, ind.name, "indicator", {"subtype": ind.indicator_type})
            
            # Connect to Responsible
            if ind.responsible_id:
                add_link(f"colab_{ind.responsible_id}", ind_node_id, "responsável", "direct")
            
            # Connect to Extra Collaborators (JSON list)
            if ind.collaborators and isinstance(ind.collaborators, list):
                for c_id in ind.collaborators:
                    try:
                        add_link(f"colab_{int(c_id)}", ind_node_id, "colaborador", "indirect")
                    except (ValueError, TypeError): continue

            # Connect to Process
            if ind.process_id:
                add_link(ind_node_id, f"proc_{ind.process_id}", "mede processo", "direct")
            elif ind.source_module == 'process' and ind.source_id:
                add_link(ind_node_id, f"proc_{ind.source_id}", "fonte processo", "direct")
            
            # Connect to Project
            if ind.project_id:
                add_link(ind_node_id, f"proj_{ind.project_id}", "mede projeto", "direct")
            elif ind.source_module == 'project' and ind.source_id:
                add_link(ind_node_id, f"proj_{ind.source_id}", "fonte projeto", "direct")

        # ── EXTRA: Match Project.kpis (JSON list of names) ───────────────────
        for proj in projects:
            if proj.kpis and isinstance(proj.kpis, list):
                for kpi_name in proj.kpis:
                    target_ind_id = ind_map_by_name.get(kpi_name.lower())
                    if target_ind_id:
                        add_link(f"ind_{target_ind_id}", f"proj_{proj.id}", "kpi projeto", "indirect")

        # ── EXTRA CONNECTIONS: Execution Links ───────────────────────────────
        # Process Execution Links
        proc_execs = db.session.query(ProcessInstanceCollaborator).join(
            Employee, Employee.id == ProcessInstanceCollaborator.employee_id
        ).filter(Employee.company_id == company_id).all()
        
        added_exec_links = set()
        for exec_link in proc_execs:
            # We want to link Collaborator to Process via the Instance
            # But the web shows Process nodes, not Instance nodes.
            # So we link Collaborator -> Process
            inst = ProcessInstance.query.get(exec_link.process_instance_id)
            if inst:
                link_key = f"c{exec_link.employee_id}_p{inst.process_id}"
                if link_key not in added_exec_links:
                    add_link(f"colab_{exec_link.employee_id}", f"proc_{inst.process_id}", "executor", "indirect")
                    added_exec_links.add(link_key)

        # Project Execution Links
        proj_execs = db.session.query(ProjectActivityCollaborator).join(
            Employee, Employee.id == ProjectActivityCollaborator.employee_id
        ).filter(Employee.company_id == company_id).all()

        added_proj_links = set()
        for exec_link in proj_execs:
            task = ProjectTask.query.get(exec_link.activity_id)
            if task:
                link_key = f"c{exec_link.employee_id}_p{task.project_id}"
                if link_key not in added_proj_links:
                    add_link(f"colab_{exec_link.employee_id}", f"proj_{task.project_id}", "membro", "indirect")
                    added_proj_links.add(link_key)

        # ── HEALTH ANALYSIS ─────────────────────────
        nodes_list = list(nodes.values())
        for node in nodes_list:
            degree = link_counter.get(node["id"], 0)
            node["degree"] = degree
            if degree == 0:
                node["health"] = "orphan"
            elif degree == 1:
                node["health"] = "fragile"
            else:
                node["health"] = "connected"

        return {
            "nodes": nodes_list,
            "links": links,
            "summary": {
                "total": len(nodes_list),
                "orphans": sum(1 for n in nodes_list if n["health"] == "orphan"),
                "fragile": sum(1 for n in nodes_list if n["health"] == "fragile"),
                "connected": sum(1 for n in nodes_list if n["health"] == "connected"),
            }
        }


class IncentiveRuleResource(Resource):
    def get(self, rule_set_id):
        company_id = session.get('active_company_id')
        from models import IncentiveRule, Indicator
        
        rules = db.session.query(
            IncentiveRule, Indicator.name
        ).join(
            Indicator, Indicator.id == IncentiveRule.indicator_id
        ).filter(
            IncentiveRule.rule_set_id == rule_set_id
        ).order_by(IncentiveRule.order_index).all()
        
        return [
            {
                "id": r.IncentiveRule.id,
                "indicator_id": r.IncentiveRule.indicator_id,
                "indicator_name": r.name,
                "weight": float(r.IncentiveRule.weight or 0),
                "target": float(r.IncentiveRule.target_value or 0),
                "cap": float(r.IncentiveRule.max_cap or 0),
                "impact_type": r.IncentiveRule.impact_type
            } for r in rules
        ]

    def post(self, rule_set_id):
        company_id = session.get('active_company_id')
        data = request.get_json()
        rules_data = data.get('rules', [])
        
        from models import IncentiveRule, IncentiveRuleSet
        
        # Verify ownership
        rs = IncentiveRuleSet.query.get(rule_set_id)
        if not rs or rs.company_id != company_id:
            return {"error": "Unauthorized"}, 403
            
        IncentiveRule.query.filter_by(rule_set_id=rule_set_id).delete()
        
        for idx, r_data in enumerate(rules_data):
            rule = IncentiveRule(
                rule_set_id=rule_set_id,
                indicator_id=r_data['indicator_id'],
                weight=r_data.get('weight', 1.0),
                target_value=r_data.get('target'),
                max_cap=r_data.get('cap'),
                impact_type=r_data.get('impact_type', 'multiplier'),
                order_index=idx,
                company_id=company_id # Added explicitly
            )
            db.session.add(rule)
            
        db.session.commit()
        return {"success": True, "count": len(rules_data)}
