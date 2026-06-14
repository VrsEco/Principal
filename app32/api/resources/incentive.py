from flask_restful import Resource
from flask import request, session
import logging
from datetime import datetime
from sqlalchemy import or_
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
        company_id = session.get('active_company_id')
        if not company_id:
            return {"error": "No company active"}, 400

        from services.incentive_spider_web_service import IncentiveSpiderWebService

        return IncentiveSpiderWebService.build_graph(int(company_id))


class IncentiveRuleResource(Resource):
    def get(self, rule_set_id):
        company_id = session.get('active_company_id')
        from models import IncentiveRule, Indicator
        
        rules = db.session.query(
            IncentiveRule, Indicator.name
        ).join(
            Indicator, Indicator.id == IncentiveRule.indicator_id
        ).filter(
            IncentiveRule.rule_set_id == rule_set_id,
            IncentiveRule.deleted_at.is_(None),
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
        rs = IncentiveRuleSet.query.filter(
            IncentiveRuleSet.id == rule_set_id,
            IncentiveRuleSet.company_id == company_id,
            IncentiveRuleSet.deleted_at.is_(None),
        ).first()
        if not rs:
            return {"error": "Unauthorized"}, 403
            
        IncentiveRule.query.filter(
            IncentiveRule.rule_set_id == rule_set_id,
            or_(
                IncentiveRule.company_id == company_id,
                IncentiveRule.company_id.is_(None),
            ),
            IncentiveRule.deleted_at.is_(None),
        ).update({"deleted_at": datetime.utcnow()}, synchronize_session=False)
        
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
