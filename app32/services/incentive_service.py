import logging
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional
import sqlalchemy as sa
from sqlalchemy import func
from models import (
    db, IncentiveIndicator, IncentiveRuleSet, IncentiveRule,
    IncentiveGovernabilityMatrix, IncentiveFact, IncentiveCalculation,
    Project, ProcessInstance, Occurrence, Employee, Role
)

logger = logging.getLogger(__name__)

class IncentiveService:
    """
    Core Service for the Incentive System (Onda 1B)
    Handles Fact Harvesting, Calculation Pipeline and Governance.
    """

    @staticmethod
    def harvest_project_facts(company_id: int, period_start: date, period_end: date):
        """
        Scans projects completed or active in the period and generates Facts.
        Logic: Calculate % of tasks delivery or project completion.
        """
        # This harvesting logic looks for indicators classified as 'project' source
        indicators = IncentiveIndicator.query.filter_by(
            company_id=company_id, 
            source_module='project',
            is_active=True
        ).all()
        
        for indicator in indicators:
            # Simple logic: count active or completed projects in the period
            # In future: calculate % delivery of tasks
            projects = Project.query.filter_by(company_id=company_id).all()
            
            # For now, let's aggregate at company level (employee_id=None)
            fact = IncentiveFact.query.filter_by(
                company_id=company_id,
                indicator_id=indicator.id,
                employee_id=None, 
                period_start=period_start,
                period_end=period_end
            ).first()
            
            if not fact:
                fact = IncentiveFact(
                    company_id=company_id,
                    indicator_id=indicator.id,
                    period_start=period_start,
                    period_end=period_end
                )
                db.session.add(fact)
            
            fact.value = Decimal(str(len(projects)))
            fact.status = 'verified'
        
        db.session.commit()

    @staticmethod
    def harvest_process_facts(company_id: int, period_start: date, period_end: date):
        """
        Scans Process Instances and generates facts for employees.
        Calculates based on completed instances and their weights.
        """
        indicators = IncentiveIndicator.query.filter_by(
            company_id=company_id,
            source_module='process',
            is_active=True
        ).all()

        for indicator in indicators:
            # Query instances in the period
            # Filter by specific process if source_id is defined
            query = db.session.query(
                ProcessInstance.executor_id,
                func.count(ProcessInstance.id).label('count'),
                func.sum(ProcessInstance.score_weight).label('total_weight')
            ).filter(
                ProcessInstance.company_id == company_id,
                ProcessInstance.status == 'completed',
                func.cast(ProcessInstance.completed_at, sa.Date) >= period_start,
                func.cast(ProcessInstance.completed_at, sa.Date) <= period_end
            )

            if indicator.source_id:
                query = query.filter(ProcessInstance.process_id == indicator.source_id)

            results = query.group_by(ProcessInstance.executor_id).all()

            for emp_id, count, total_weight in results:
                if not emp_id: continue
                
                fact = IncentiveFact.query.filter_by(
                    company_id=company_id,
                    indicator_id=indicator.id,
                    employee_id=emp_id,
                    period_start=period_start,
                    period_end=period_end
                ).first()

                if not fact:
                    fact = IncentiveFact(
                        company_id=company_id,
                        indicator_id=indicator.id,
                        employee_id=emp_id,
                        period_start=period_start,
                        period_end=period_end
                    )
                    db.session.add(fact)

                # Value can be count or weighted sum based on indicator config (defaulting to weight sum)
                fact.value = Decimal(str(total_weight or count))
                fact.status = 'verified'
                
                # Attach evidence payload
                fact.evidence_payload = {
                    "instances_count": count,
                    "target_process_id": indicator.source_id,
                    "module": "process"
                }

        db.session.commit()

    @staticmethod
    def harvest_occurrence_facts(company_id: int, period_start: date, period_end: date):
        """
        Scans Occurrences (Risk/Deductions) and creates facts.
        """
        indicators = IncentiveIndicator.query.filter_by(
            company_id=company_id,
            source_module='occurrence',
            is_active=True
        ).all()
        
        for indicator in indicators:
            # Group by employee
            # Filter by specific source_id if applicable (e.g. type of occurrence)
            query = db.session.query(
                Occurrence.employee_id,
                func.count(Occurrence.id).label('count'),
                func.sum(Occurrence.score).label('total_score')
            ).filter(
                Occurrence.company_id == company_id,
                Occurrence.created_at >= period_start,
                Occurrence.created_at <= period_end
            )
            
            results = query.group_by(Occurrence.employee_id).all()
            
            for emp_id, count, total_score in results:
                if not emp_id: continue

                fact = IncentiveFact.query.filter_by(
                    company_id=company_id,
                    indicator_id=indicator.id,
                    employee_id=emp_id,
                    period_start=period_start,
                    period_end=period_end
                ).first()
                
                if not fact:
                    fact = IncentiveFact(
                        company_id=company_id,
                        indicator_id=indicator.id,
                        employee_id=emp_id,
                        period_start=period_start,
                        period_end=period_end
                    )
                    db.session.add(fact)
                
                fact.value = Decimal(str(total_score or count))
                fact.status = 'verified'
                fact.evidence_payload = {"count": count, "module": "occurrence"}
        
        db.session.commit()

    @classmethod
    def harvest_all_modules(cls, company_id: int, period_start: date, period_end: date):
        """Unified entry point for harvesting all sources."""
        logger.info(f"Starting Harvesting for company {company_id} period {period_start} to {period_end}")
        cls.harvest_project_facts(company_id, period_start, period_end)
        cls.harvest_occurrence_facts(company_id, period_start, period_end)
        cls.harvest_process_facts(company_id, period_start, period_end)
        logger.info(f"Harvesting completed for company {company_id}")

    @staticmethod
    def calculate_incentive(company_id: int, rule_set_id: int, period_start: date, period_end: date):
        """
        The Main Calculation Pipeline.
        Final Bonus = Base x Factor_Eligibility x Factor_Individual x Factor_Unit x Factor_Company x Factor_Risk
        """
        rule_set = IncentiveRuleSet.query.get(rule_set_id)
        if not rule_set or rule_set.company_id != company_id:
            return {"error": "Invalid RuleSet"}

        rules = IncentiveRule.query.filter_by(rule_set_id=rule_set_id).order_by(IncentiveRule.order_index).all()
        
        # 1. Initialize Calculation Header
        calc = IncentiveCalculation(
            company_id=company_id,
            rule_set_id=rule_set_id,
            period_start=period_start,
            period_end=period_end,
            status='preview'
        )
        db.session.add(calc)
        db.session.flush() # Get ID
        
        # 2. Identify Participants (Employees in the company and active)
        employees = Employee.query.filter_by(company_id=company_id, status='active').all()
        
        results = []
        total_distributed = Decimal('0.00')

        for emp in employees:
            # Base logic (In real app, pull from 'salario_base' or similar)
            base_value = Decimal('1000.00') # Placeholder
            accumulated_payout = base_value
            steps = []
            
            for rule in rules:
                # Find the Fact for this Employee/Indicator
                # If rule is 'collective', search for employee_id=None
                emp_filter = emp.id if rule.impact_type in ('individual', 'trigger') else None
                
                fact = IncentiveFact.query.filter_by(
                    indicator_id=rule.indicator_id,
                    employee_id=emp_filter,
                    period_start=period_start,
                    period_end=period_end
                ).first()
                
                realized = fact.value if fact else Decimal('0.00')
                target = rule.target_value or Decimal('1.00')
                
                # Basic Achievement
                achievement = (realized / target) if target > 0 else Decimal('0.00')
                
                # Apply Thresholds
                if rule.min_threshold and achievement < rule.min_threshold:
                    achievement = Decimal('0.00')
                if rule.max_cap and achievement > rule.max_cap:
                    achievement = rule.max_cap
                
                impact_factor = Decimal('1.00')
                
                if rule.impact_type == 'individual':
                    # Individual Score = Weight * Achievement
                    impact_factor = (rule.weight or Decimal('1.00')) * achievement
                    accumulated_payout *= impact_factor
                elif rule.impact_type == 'multiplier':
                    # Multiplier Factor (e.g. Company Achievement)
                    impact_factor = achievement # Or complex meta-rule
                    accumulated_payout *= impact_factor
                elif rule.impact_type == 'reducer':
                    # Reducer (Risk/Occurrences) - subtract or divide
                    impact_factor = Decimal('1.00') - (achievement * (rule.weight or Decimal('0.1')))
                    accumulated_payout *= max(Decimal('0.00'), impact_factor)

                steps.append({
                    "rule_id": rule.id,
                    "indicator": rule.indicator_id,
                    "type": rule.impact_type,
                    "realized": str(realized),
                    "target": str(target),
                    "factor": str(impact_factor)
                })

            final_bonus = max(Decimal('0.00'), accumulated_payout - base_value)
            
            participant_result = {
                "employee_id": emp.id,
                "name": emp.name,
                "base": str(base_value),
                "bonus": str(final_bonus),
                "steps": steps
            }
            results.append(participant_result)
            total_distributed += final_bonus

        calc.total_distributed = total_distributed
        calc.participants_count = len(results)
        calc.status = 'calculated'
        
        db.session.commit()
        return {
            "calculation_id": calc.id,
            "total_payout": str(total_distributed),
            "participants": results
        }

    @staticmethod
    def get_governability_report(company_id: int):
        """
        Returns a map of which Roles are connected to which Indicators.
        Helps visualize the "Spider Web".
        """
        matrix = db.session.query(
            IncentiveGovernabilityMatrix, Role.title, IncentiveIndicator.name
        ).join(Role, Role.id == IncentiveGovernabilityMatrix.role_id
        ).join(IncentiveIndicator, IncentiveIndicator.id == IncentiveGovernabilityMatrix.indicator_id
        ).filter(IncentiveGovernabilityMatrix.company_id == company_id).all()
        
        report = []
        for entry, role_title, indicator_name in matrix:
            report.append({
                "role": role_title,
                "indicator": indicator_name,
                "level": entry.governability_level
            })
        return report
