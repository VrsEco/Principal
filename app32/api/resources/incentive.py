from flask_restful import Resource
from flask import request, session
from services.incentive_service import IncentiveService
from models import IncentiveIndicator, IncentiveRuleSet, IncentiveCalculation, db
from datetime import date

class IncentiveIndicatorListResource(Resource):
    def get(self):
        company_id = session.get('active_company_id')
        if not company_id: return {"error": "No company active"}, 400
        
        indicators = IncentiveIndicator.query.filter_by(company_id=company_id).all()
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
        IncentiveService.harvest_occurrence_facts(company_id, start_date, end_date)
        IncentiveService.harvest_project_facts(company_id, start_date, end_date)
        
        result = IncentiveService.calculate_incentive(company_id, rule_set_id, start_date, end_date)
        return result

class IncentiveSpiderWebResource(Resource):
    def get(self):
        company_id = session.get('active_company_id')
        if not company_id: return {"error": "No company active"}, 400
        
        # Get matrix and indicators for graph visualization
        matrix = IncentiveService.get_governability_report(company_id)
        
        # Transform into a graph structure for D3/Cytoscape
        nodes = []
        links = []
        
        # Roles and Indicators as nodes
        roles_seen = set()
        inds_seen = set()
        
        for entry in matrix:
            role_name = entry['role']
            ind_name = entry['indicator']
            
            if role_name not in roles_seen:
                nodes.append({"id": role_name, "type": "role", "label": role_name})
                roles_seen.add(role_name)
            
            if ind_name not in inds_seen:
                nodes.append({"id": ind_name, "type": "indicator", "label": ind_name})
                inds_seen.add(ind_name)
            
            links.append({
                "source": role_name,
                "target": ind_name,
                "level": entry['level']
            })
            
        return {"nodes": nodes, "links": links}
