from flask_restful import Resource
from flask import request, session
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
        company_id = session.get('active_company_id')
        data = request.get_json()
        
        rule_set_id = data.get('rule_set_id')
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
            Role, Process, Project
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
            links.append({"source": src, "target": tgt, "label": label, "strength": strength})
            link_counter[src] = link_counter.get(src, 0) + 1
            link_counter[tgt] = link_counter.get(tgt, 0) + 1

        # ── LAYER 1: Roles ──────────────────────────────────────────────────
        roles = Role.query.filter_by(company_id=company_id).all()
        for role in roles:
            add_node(f"role_{role.id}", role.title, "role")

        # ── LAYER 2: Indicators via IncentiveRules ───────────────────────────
        rules = db.session.query(
            IncentiveRule, Indicator
        ).join(
            IncentiveRuleSet, IncentiveRuleSet.id == IncentiveRule.rule_set_id
        ).join(
            Indicator, Indicator.id == IncentiveRule.indicator_id
        ).filter(
            IncentiveRuleSet.company_id == company_id
        ).all()

        ind_source_map = {}  # indicator_id -> (source_module, source_id)

        for rule, ind in rules:
            ind_id = f"ind_{ind.id}"
            add_node(ind_id, ind.name, "indicator", {"subtype": ind.indicator_type, "source_module": ind.source_module})
            ind_source_map[ind.id] = (ind.source_module, ind.source_id)

            # Connect all roles to all indicators (governance web)
            for role in roles:
                strength = "direct" if ind.indicator_type == "individual" else "indirect"
                add_link(f"role_{role.id}", ind_id, ind.indicator_type, strength)

        # ── LAYER 3: Processes linked via indicator source ────────────────────
        processes = Process.query.filter_by(company_id=company_id, is_active=True).all()
        proc_map = {p.id: p for p in processes}

        for proc in processes:
            add_node(f"proc_{proc.id}", proc.name, "process", {"kanban_stage": p.kanban_stage if hasattr(p, 'kanban_stage') else None}) # Added safety

        # Connect Indicators → Processes (via source_module='process' + source_id)
        for ind_id_int, (source_module, source_id) in ind_source_map.items():
            if source_module == "process" and source_id and source_id in proc_map:
                add_link(f"ind_{ind_id_int}", f"proc_{source_id}", "gera fato", "direct")

        # Also: connect all processes to indicators of type 'financeiro'/'processos' heuristically
        for ind_id_int, (source_module, source_id) in ind_source_map.items():
            if source_module == "process" and not source_id:
                for proc in processes:
                    add_link(f"ind_{ind_id_int}", f"proc_{proc.id}", "gen. coletivo", "indirect")

        # ── LAYER 4: Projects ─────────────────────────────────────────────────
        projects = Project.query.filter_by(company_id=company_id).all()
        proj_map = {p.id: p for p in projects}

        for proj in projects:
            status_meta = {"status": proj.status, "progress": proj.progress}
            add_node(f"proj_{proj.id}", proj.name, "project", status_meta)

        # Connect Indicators → Projects
        for ind_id_int, (source_module, source_id) in ind_source_map.items():
            if source_module == "project":
                if source_id and int(source_id) in proj_map:
                    add_link(f"ind_{ind_id_int}", f"proj_{source_id}", "projeto específico", "direct")
                else:
                    for proj in projects:
                        add_link(f"ind_{ind_id_int}", f"proj_{proj.id}", "impacto portfólio", "indirect")
            elif source_module == "financeiro":
                for proj in projects:
                    add_link(f"ind_{ind_id_int}", f"proj_{proj.id}", "resultado financeiro", "indirect")

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
