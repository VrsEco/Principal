from models import db, Plan, PlanParticipant, PlanSectionStatus, PlanDriver, PlanImplantationData
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class PlanService:
    @staticmethod
    def _normalize_period(value: Optional[str]) -> str:
        """Normaliza datas YYYY-MM, YYYY.MM e YYYY-MM-DD para YYYY-MM."""
        if not value:
            return ""

        normalized = str(value).strip().replace('.', '-').replace('/', '-')
        if len(normalized) >= 7:
            parts = normalized.split('-')
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                return f"{int(parts[0]):04d}-{int(parts[1]):02d}"
        return ""

    @staticmethod
    def _expand_execution_item_payments(item: Dict[str, Any], normalized_periods: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Expande o planejamento financeiro do item em fluxos mensais."""
        payments = item.get('payments') or []
        classification = item.get('classification') or 'aquisição'
        payment_plan = item.get('payment_plan') or {}
        plan_mode = payment_plan.get('mode') or 'multiple'

        if classification == 'contratação' and plan_mode == 'monthly_contract':
            start_period = PlanService._normalize_period(
                payment_plan.get('start_date')
                or item.get('acquisition_date')
                or item.get('availability_date')
            )
            end_period = PlanService._normalize_period(payment_plan.get('end_date'))
            monthly_amount = float(payment_plan.get('monthly_amount') or 0)

            if not normalized_periods or not start_period or monthly_amount <= 0:
                return []

            return [
                {"date": period, "amount": monthly_amount}
                for period in normalized_periods
                if period >= start_period and (not end_period or period <= end_period)
            ]

        expanded = []
        if payments:
            for pay in payments:
                period = PlanService._normalize_period(pay.get('date'))
                if period:
                    expanded.append({
                        "date": period,
                        "amount": float(pay.get('amount') or 0),
                    })
            return expanded

        fallback_period = PlanService._normalize_period(
            item.get('acquisition_date') or item.get('availability_date')
        )
        fallback_amount = float(item.get('value') or 0)
        if fallback_period and fallback_amount > 0:
            return [{"date": fallback_period, "amount": fallback_amount}]
        return []

    @staticmethod
    def _collect_execution_item_dates(item: Dict[str, Any]) -> List[str]:
        """Retorna datas relevantes do item para definir o início da análise."""
        relevant_dates = []
        payment_plan = item.get('payment_plan') or {}

        for pay in item.get('payments', []):
            period = PlanService._normalize_period(pay.get('date'))
            if period:
                relevant_dates.append(period)

        for key in ('acquisition_date', 'availability_date'):
            period = PlanService._normalize_period(item.get(key))
            if period:
                relevant_dates.append(period)

        if item.get('classification') == 'contratação' and payment_plan.get('mode') == 'monthly_contract':
            start_period = PlanService._normalize_period(payment_plan.get('start_date'))
            end_period = PlanService._normalize_period(payment_plan.get('end_date'))
            if start_period:
                relevant_dates.append(start_period)
            if end_period:
                relevant_dates.append(end_period)

        return relevant_dates

    @staticmethod
    def get_sections_config(mode: str) -> List[Dict[str, Any]]:
        """Returns the centralized configuration for plan sections."""
        if mode == 'growth':
            return [
                {"key": "dashboard", "title": "Dashboard", "icon": "layout-dashboard", "completable": False},
                {"key": "participants", "title": "Participantes", "icon": "users", "completable": True},
                {"key": "drivers", "title": "Direcionadores", "icon": "compass", "completable": True},
                {"key": "okrs_global", "title": "OKRs Globais", "icon": "target", "completable": True},
                {"key": "okrs_area", "title": "OKRs Área", "icon": "layers", "completable": True},
                {"key": "projects", "title": "Projetos", "icon": "briefcase", "completable": False},
                {"key": "final_report", "title": "Relatório Final", "icon": "file-text", "completable": False},
            ]
        else:  # implantation
            return [
                {"key": "dashboard", "title": "Dashboard", "icon": "layout-dashboard", "completable": False},
                {"key": "participants", "title": "Participantes", "icon": "users", "completable": True},
                {"key": "alignment", "title": "Alinhamento", "icon": "handshake", "completable": True},
                {"key": "model", "title": "Modelo & Mercado", "icon": "shop", "completable": True},
                {"key": "execution", "title": "Execução", "icon": "bolt", "completable": True},
                {"key": "finance", "title": "Financeiro", "icon": "money-bill-trend-up", "completable": True},
                {"key": "projects", "title": "Projetos", "icon": "briefcase", "completable": False},
                {"key": "final_report", "title": "Relatório Final", "icon": "file-pdf", "completable": False},
            ]

    @staticmethod
    def get_plan_dashboard_data(plan_id: int, company_id: int) -> Dict[str, Any]:
        """Consolidates all metrics and status for a plan dashboard."""
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan:
            return {}

        sections = PlanService.get_sections_config(plan.mode)
        
        # Get status for each section
        statuses = {s.section_key: s.status for s in plan.section_statuses.all()}
        for section in sections:
            section['status'] = statuses.get(section['key'], 'pending')

        # Generic counts
        from models import PlanDriver, OKRGlobal, PlanParticipant
        drivers_count = PlanDriver.query.filter_by(plan_id=plan_id).count()
        okrs_count = OKRGlobal.query.filter_by(plan_id=plan_id).count()
        participants_count = PlanParticipant.query.filter_by(plan_id=plan_id).count()

        # Progression
        completable_keys = [s["key"] for s in sections if s.get("completable")]
        completed_sections = PlanSectionStatus.query.filter(
            PlanSectionStatus.plan_id == plan_id,
            PlanSectionStatus.section_key.in_(completable_keys),
            PlanSectionStatus.status == 'completed'
        ).count()

        # Base Stats
        data = {
            "plan": plan.to_dict(),
            "sections": sections,
            "stats": {
                "drivers_count": drivers_count,
                "okrs_count": okrs_count,
                "participants_count": participants_count,
                "completed_sections": completed_sections,
                "total_completable": len(completable_keys),
                "progress_pct": plan.progress
            }
        }

        # Mode specific extra data
        if plan.mode == 'implantation':
            finance_info = PlanService.get_consolidated_finance(plan_id, company_id)
            summary = finance_info.get('summary', {})
            metrics = finance_info.get('metrics', {})
            data['finance'] = {
                "total_investment": summary.get('total_investment', 0),
                "payback": metrics.get('payback', 0)
            }

        return data


    @staticmethod
    def create_plan(company_id: int, data: Dict[str, Any]) -> Plan:
        """Create a new plan ensures multi-tenancy."""
        try:
            plan = Plan(
                company_id=company_id,
                title=data['title'],
                description=data.get('description'),
                mode=data.get('mode', 'growth'),
                status=data.get('status', 'draft'),
                meta_data=data.get('meta_data', {})
            )
            db.session.add(plan)
            
            # Initialize default sections based on mode
            # Growth sections as requested
            sections = []
            if plan.mode == 'growth':
                sections = [
                    'dashboard', 'participants', 'drivers', 
                    'okrs_global', 'okrs_area', 'projects', 'final_report'
                ]
            else: # implantation
                sections = [
                    'dashboard', 'participants', 'alignment', 'model', 
                    'execution', 'finance', 'projects', 'final_report'
                ]
            
            for section in sections:
                status = PlanSectionStatus(plan=plan, section_key=section, status='pending')
                db.session.add(status)
                
            db.session.commit()
            return plan
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error creating plan: {e}")
            raise

    @staticmethod
    def get_plan(plan_id: int, company_id: int) -> Optional[Plan]:
        """Get a plan with strict multi-tenancy check."""
        return Plan.query.filter_by(id=plan_id, company_id=company_id).first()

    @staticmethod
    def list_plans(company_id: int, mode: Optional[str] = None) -> List[Plan]:
        """List plans for a company."""
        query = Plan.query.filter_by(company_id=company_id)
        if mode:
            query = query.filter_by(mode=mode)
        return query.order_by(Plan.created_at.desc()).all()

    @staticmethod
    def update_plan(plan_id: int, company_id: int, data: Dict[str, Any]) -> Optional[Plan]:
        """Update a plan's basic information."""
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan:
            return None
        
        if 'title' in data:
            plan.title = data['title']
        if 'description' in data:
            plan.description = data['description']
        
        db.session.commit()
        return plan

    @staticmethod
    def delete_plan(plan_id: int, company_id: int) -> bool:
        """Delete a plan and its related data."""
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan:
            return False
            
        try:
            # Related data will be handled by cascades if defined in models, 
            # otherwise we need to clean up manually.
            # Base models for PEV v2.0 usually have many relationships.
            
            # Manual cleanup for critical related tables if cascades are not set
            PlanSectionStatus.query.filter_by(plan_id=plan_id).delete()
            PlanParticipant.query.filter_by(plan_id=plan_id).delete()
            PlanDriver.query.filter_by(plan_id=plan_id).delete()
            PlanImplantationData.query.filter_by(plan_id=plan_id).delete()
            
            db.session.delete(plan)
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error deleting plan {plan_id}: {e}")
            return False

    @staticmethod
    def add_driver(plan_id: int, company_id: int, data: Dict[str, Any]) -> PlanDriver:
        """Add a strategic driver to a growth plan."""
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan or plan.mode != 'growth':
            raise ValueError("Growth Plan not found or invalid mode.")
            
        driver = PlanDriver(
            plan_id=plan_id,
            type=data['type'],
            description=data['description'],
            priority=data.get('priority', 'medium'),
            meta_data=data.get('meta_data', {})
        )
        db.session.add(driver)
        db.session.commit()
        
        # Update section status to in_progress if it was pending
        PlanService.update_section_status(plan_id, 'drivers', 'in_progress')
        
        return driver

    @staticmethod
    def update_section_status(plan_id: int, section_key: str, status: str):
        """Update status of a specific plan section."""
        section = PlanSectionStatus.query.filter_by(plan_id=plan_id, section_key=section_key).first()
        if not section:
            # Create if missing (helps with legacy plans)
            section = PlanSectionStatus(plan_id=plan_id, section_key=section_key, status=status)
            db.session.add(section)
        else:
            section.status = status
            
        db.session.commit()
        PlanService._recalculate_progress(plan_id)

    @staticmethod
    def _recalculate_progress(plan_id: int):
        """Calculate overall plan progress based on completed sections."""
        plan = Plan.query.get(plan_id)
        if not plan:
            return
            
        # Define sections that count towards progress
        if plan.mode == 'growth':
            completable_keys = ['participants', 'drivers', 'okrs_global', 'okrs_area']
        else: # implantation
            completable_keys = ['participants', 'alignment', 'model', 'execution', 'finance']

        sections = PlanSectionStatus.query.filter(
            PlanSectionStatus.plan_id == plan_id,
            PlanSectionStatus.section_key.in_(completable_keys)
        ).all()
        
        if not sections:
            return
            
        completed = len([s for s in sections if s.status == 'completed'])
        total = len(sections)
        
        plan.progress = int((completed / total) * 100) if total > 0 else 0
        db.session.commit()

    @staticmethod
    def get_implantation_data(plan_id: int, company_id: int, section_key: str) -> Optional[PlanImplantationData]:
        """Get section data for an implantation plan."""
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan or plan.mode != 'implantation':
            return None
            
        return PlanImplantationData.query.filter_by(plan_id=plan_id, section_key=section_key).first()

    @staticmethod
    def save_implantation_data(plan_id: int, company_id: int, section_key: str, content: Dict[str, Any]) -> PlanImplantationData:
        """Save/Update section data for an implantation plan."""
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan or plan.mode != 'implantation':
            raise ValueError("Implantation Plan not found or invalid mode.")
            
        data = PlanImplantationData.query.filter_by(plan_id=plan_id, section_key=section_key).first()
        if not data:
            data = PlanImplantationData(plan_id=plan_id, section_key=section_key, content=content)
            db.session.add(data)
        else:
            data.content = content
            
        db.session.commit()
        
        # Update section status
        if section_key != 'dashboard':
            PlanService.update_section_status(plan_id, section_key, 'completed')
            
        return data

    @staticmethod
    def add_participant(plan_id: int, company_id: int, data: Dict[str, Any]) -> PlanParticipant:
        """Add a participant to the plan."""
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan:
            raise ValueError("Plan not found.")
            
        # Check if already added
        existing = PlanParticipant.query.filter_by(
            plan_id=plan_id, 
            employee_id=data.get('employee_id'),
            user_id=data.get('user_id')
        ).first()
        
        if existing:
            # Update role if already exists
            existing.role = data.get('role', 'viewer')
            db.session.commit()
            return existing
            
        participant = PlanParticipant(
            plan_id=plan_id,
            user_id=data.get('user_id'),
            employee_id=data.get('employee_id'),
            role=data.get('role', 'viewer'),
            meta_data=data.get('meta_data', {})
        )
        db.session.add(participant)
        db.session.commit()
        
        # Update section status
        PlanService.update_section_status(plan_id, 'participants', 'completed')
        
        return participant

    @staticmethod
    def remove_participant(plan_id: int, company_id: int, participant_id: int):
        """Remove a participant from the plan."""
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan:
            raise ValueError("Plan not found.")
            
        participant = PlanParticipant.query.filter_by(id=participant_id, plan_id=plan_id).first()
        if participant:
            db.session.delete(participant)
            db.session.commit()
            
    @staticmethod
    def list_participants(plan_id: int, company_id: int) -> List[PlanParticipant]:
        """List participants for a plan."""
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan:
            return []
        
        return PlanParticipant.query.filter_by(plan_id=plan_id).all()

    @staticmethod
    def get_consolidated_finance(plan_id: int, company_id: int) -> Dict[str, Any]:
        """
        Consolidates data from 'model', 'execution' and 'finance' sections
        to generate a complete financial feasibility study.
        """
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan or plan.mode != 'implantation':
            return {}

        # 1. Gather data from sections
        model_data = PlanService.get_implantation_data(plan_id, company_id, 'model')
        execution_data = PlanService.get_implantation_data(plan_id, company_id, 'execution')
        finance_data = PlanService.get_implantation_data(plan_id, company_id, 'finance')

        model_content = model_data.content if model_data else {}
        exec_content = execution_data.content if execution_data else {}
        fin_content = finance_data.content if finance_data else {}

        # 2. Extract Base Data
        products = model_content.get('products', [])
        areas = exec_content.get('areas', {})
        
        # 3. Parameters
        params = fin_content.get('analysis_params', {})
        period_months = params.get('period_months', 60)
        opp_cost = params.get('opportunity_cost_annual', 12.0)
        
        # 4. Extract Items from Execution
        investment_items = []
        fixed_cost_items = [] # area_id == 'operacional'
        fixed_expense_items = [] # area_id in ['admin', 'comercial']
        for area_id, area_data in areas.items():
            for item in area_data.get('items', []):
                if item.get('classification') == 'aquisição':
                    investment_items.append(item)
                elif area_id == 'operacional':
                    fixed_cost_items.append(item)
                else: 
                    fixed_expense_items.append(item)

        # 5. Determine Start Date & Ramp-up Scope
        ramp_up_dates = []
        for p in products:
            for r in p.get('ramp_up_entries', []):
                val = r.get('month_period')
                if val:
                    ramp_up_dates.append(val.replace('.','-'))

        wc_data = fin_content.get('working_capital', {})
        working_capital_lines = []
        for cat in ['cash_items', 'receivables_items', 'inventory_items']:
            for item in wc_data.get(cat, []):
                working_capital_lines.append({
                    "category": cat,
                    "description": item.get('description') or "",
                    "value": float(item.get('value') or 0),
                    "contribution_date": item.get('contribution_date') or "",
                    "availability_date": item.get('availability_date') or "",
                })

        working_capital_total = sum(item["value"] for item in working_capital_lines)

        fixed_asset_rows = []
        fixed_assets_total = 0.0
        for item in investment_items:
            payments = PlanService._expand_execution_item_payments(item)
            if payments:
                for pay in payments:
                    amount = float(pay.get('amount') or 0)
                    fixed_asset_rows.append({
                        "description": item.get('description') or "Investimento",
                        "item_type": item.get('item_type') or "",
                        "date": pay.get('date') or PlanService._normalize_period(item.get('acquisition_date')) or PlanService._normalize_period(item.get('availability_date')) or "",
                        "amount": amount,
                    })
                    fixed_assets_total += amount
            else:
                amount = float(item.get('value') or 0)
                fixed_asset_rows.append({
                    "description": item.get('description') or "Investimento",
                    "item_type": item.get('item_type') or "",
                    "date": PlanService._normalize_period(item.get('acquisition_date')) or PlanService._normalize_period(item.get('availability_date')) or "",
                    "amount": amount,
                })
                fixed_assets_total += amount

        params_start_date = params.get('start_date')
        if params_start_date:
            start_date_str = params_start_date.replace('.', '-')
            if len(start_date_str.split('-')) < 2:
                start_date_str = datetime.now().strftime('%Y-%m')
        else:
            all_dates = list(ramp_up_dates) # Start with ramp-up dates
            for item in investment_items + fixed_cost_items + fixed_expense_items:
                all_dates.extend(PlanService._collect_execution_item_dates(item))
            
            for cat in ['cash_items', 'receivables_items', 'inventory_items']:
                for item in wc_data.get(cat, []):
                    if item.get('contribution_date'):
                        all_dates.append(item.get('contribution_date'))
            
            valid_dates = [d for d in all_dates if d]
            if not valid_dates:
                start_date_str = datetime.now().strftime('%Y-%m')
            else:
                start_date_str = sorted([d.replace('.','-') for d in valid_dates])[0]

        start_year, start_month = map(int, start_date_str.split('-')[:2])

        # 6. Generate Timeline (normalized YYYY-MM)
        timeline = []
        normalized_periods = []
        curr_y, curr_m = start_year, start_month
        for _ in range(period_months):
            normalized_periods.append(f"{curr_y}-{curr_m:02d}")
            curr_m += 1
            if curr_m > 12:
                curr_m = 1
                curr_y += 1

        investment_payment_flows = [
            PlanService._expand_execution_item_payments(item, normalized_periods)
            for item in investment_items
        ]
        fixed_cost_payment_flows = [
            PlanService._expand_execution_item_payments(item, normalized_periods)
            for item in fixed_cost_items
        ]
        fixed_expense_payment_flows = [
            PlanService._expand_execution_item_payments(item, normalized_periods)
            for item in fixed_expense_items
        ]
        
        # Identify last month of ramp-up
        ramp_up_end_index = period_months - 1
        if ramp_up_dates:
            last_ramp_date = max(ramp_up_dates)
            for i, p_str in enumerate(normalized_periods):
                if p_str == last_ramp_date:
                    ramp_up_end_index = i
                    break
        
        # 7. Distributions
        profit_rules = fin_content.get('profit_distribution', [])
        
        # 8. Accumulators
        cumulative_business_flow = 0
        cumulative_investor_flow = 0
        cumulative_investment_flow = 0
        cumulative_net_operating_result = 0
        total_investment_capex = 0
        
        sources_data = fin_content.get('sources_v2', [])
        # Fallback to legacy sources if v2 not present
        if not sources_data:
            legacy_sources = fin_content.get('sources', {})
            legacy_dates = fin_content.get('source_dates', {})
            if isinstance(legacy_sources, dict):
                for name, val in legacy_sources.items():
                    sources_data.append({
                        "name": name,
                        "amount": float(val or 0),
                        "date": legacy_dates.get(name, ""),
                        "type": "propria" # Assume equity for legacy
                    })
            elif isinstance(legacy_sources, list):
                for item in legacy_sources:
                    if isinstance(item, dict):
                        sources_data.append({
                            "name": item.get('description') or item.get('category') or "Fonte",
                            "amount": float(item.get('amount') or 0),
                            "date": item.get('availability') or "",
                            "type": "propria"
                        })

        for period in normalized_periods:
            period_revenue = 0
            period_variable_costs = 0
            period_variable_expenses = 0
            period_fixed_costs = 0
            period_fixed_expenses = 0
            period_investment = 0
            period_sources_equity = 0
            period_loans = 0 # Match sources of type 'financiamento'
            
            # Match Revenue/VarCosts
            term = period.replace('-','.')
            for p in products:
                ramp = next((r for r in p.get('ramp_up_entries', []) if r.get('month_period') == term), None)
                if ramp:
                    units = p.get('market_share_goal_monthly_units', 0) * (ramp.get('percentage', 0) / 100)
                    period_revenue += units * p.get('sale_price', 0)
                    period_variable_costs += units * p.get('variable_costs_value', 0)
                    period_variable_expenses += units * p.get('variable_expenses_value', 0)
            
            # Match Fixed Costs
            for item_payments in fixed_cost_payment_flows:
                for pay in item_payments:
                    if pay.get('date', '').replace('.','-').startswith(period):
                        period_fixed_costs += float(pay.get('amount') or 0)
            
            # Match Fixed Expenses
            for item_payments in fixed_expense_payment_flows:
                for pay in item_payments:
                    if pay.get('date', '').replace('.','-').startswith(period):
                        period_fixed_expenses += float(pay.get('amount') or 0)

            # Match Investments
            for item_payments in investment_payment_flows:
                for pay in item_payments:
                    if pay.get('date', '').replace('.','-').startswith(period):
                        period_investment += float(pay.get('amount') or 0)
            
            # Match Working Capital Items
            for cat in ['cash_items', 'receivables_items', 'inventory_items']:
                for item in wc_data.get(cat, []):
                    c_date = item.get('contribution_date', '')
                    if c_date and c_date.replace('.','-').startswith(period):
                        period_investment += float(item.get('value') or 0)
            
            # Match Sources by Type
            for s in sources_data:
                s_date = s.get('date', '')
                if s_date.replace('.','-').startswith(period):
                    if s.get('type') == 'financiamento':
                        period_loans += float(s.get('amount') or 0)
                    elif s.get('type') == 'propria':
                        period_sources_equity += float(s.get('amount') or 0)
                    else: 
                        period_loans += float(s.get('amount') or 0)

            # Business Results
            gmc = period_revenue - period_variable_costs - period_variable_expenses
            operating_result = gmc - period_fixed_costs - period_fixed_expenses
            
            period_distributions_partners = 0
            period_destinations_others = 0
            
            if operating_result > 0:
                for rule in profit_rules:
                    # Check start date
                    start_date = rule.get('start_date', '')
                    if start_date:
                        if period < start_date.replace('.','-'):
                            continue
                            
                    pct = float(rule.get('percentage') or 0) / 100
                    amount = operating_result * pct
                    
                    if rule.get('type') == 'outras':
                        period_destinations_others += amount
                    else: # Default is partner distribution
                        period_distributions_partners += amount
            
            # Total destinations for business flow
            total_period_destinations = period_distributions_partners + period_destinations_others

            # Investor Flow = Partner Distributions (pos) - Equity Contributions (neg)
            # Only Partner Distributions impact the Investor ROI
            investor_net_flow = period_distributions_partners - period_sources_equity
            cumulative_investor_flow += investor_net_flow
            total_investment_capex += period_investment
            
            # Net Operating (Business View) = Operating Result - Total Destinations (All rules)
            period_net_operating = operating_result - total_period_destinations
            cumulative_net_operating_result += period_net_operating

            # Investment/CAPEX Flow = Sources (Equity + Loans) - Investments
            period_investment_flow = period_sources_equity + period_loans - period_investment
            cumulative_investment_flow += period_investment_flow

            # Business Net Flow = Result - Capex + Loans - All destinations (Geral)
            business_net_flow = operating_result - period_investment + period_loans - total_period_destinations
            cumulative_business_flow += business_net_flow

            timeline.append({
                "period": period,
                "revenue": period_revenue,
                "variable_costs": period_variable_costs,
                "variable_expenses": period_variable_expenses,
                "gmc": gmc,
                "fixed_costs": period_fixed_costs,
                "fixed_expenses": period_fixed_expenses,
                "investment": period_investment,
                "operating_result": operating_result,
                "sources_equity": period_sources_equity,
                "loans": period_loans,
                "distributions": period_distributions_partners, # Only Socio type
                "destinations_others": period_destinations_others,
                "total_destinations": total_period_destinations, # All types
                "investor_net_flow": investor_net_flow,
                "investment_flow": period_investment_flow,
                "business_net_flow": business_net_flow,
                "cumulative_business": cumulative_business_flow,
                "cumulative_investor": cumulative_investor_flow,
                "cumulative_investment": cumulative_investment_flow,
                "cumulative_net_operating": cumulative_net_operating_result
            })

        # 9. Metrics (based on Investor Flow)
        investor_cash_flows = [t['investor_net_flow'] for t in timeline]
        
        vpl = PlanService._calculate_vpl(investor_cash_flows, opp_cost)
        tir = PlanService._calculate_tir(investor_cash_flows)
        
        total_equity = sum([t['sources_equity'] for t in timeline])
        total_dist = sum([t['distributions'] for t in timeline])
        roi = (total_dist - total_equity) / total_equity if total_equity > 0 else 0
        
        payback = 0
        for i, t in enumerate(timeline):
            if t['cumulative_investor'] >= 0:
                payback = i + 1
                break

        total_investment = working_capital_total + fixed_assets_total

        return {
            "metrics": {
                "payback": payback,
                "roi": roi * 100,
                "tir": tir,
                "vpl": vpl
            },
            "summary": {
                "total_investment": total_investment,
                "total_working_capital": working_capital_total,
                "total_fixed_assets": fixed_assets_total,
                "total_equity": total_equity,
                "total_loans": sum(t['loans'] for t in timeline),
                "total_revenue": sum(t['revenue'] for t in timeline),
                "total_operating_result": sum(t['operating_result'] for t in timeline)
            },
            "investments": {
                "working_capital_lines": working_capital_lines,
                "fixed_asset_rows": fixed_asset_rows,
                "timeline_total_investment": total_investment_capex,
            },
            "timeline": timeline,
            "params": params,
            "ramp_up_end_index": ramp_up_end_index
        }

    @staticmethod
    def _calculate_vpl(cash_flows: List[float], annual_rate: float) -> float:
        """Calculates NPV (VPL)"""
        if not cash_flows: return 0
        monthly_rate = (1 + (annual_rate / 100)) ** (1/12) - 1
        vpl = 0
        for i, cf in enumerate(cash_flows):
            vpl += cf / ((1 + monthly_rate) ** (i + 1))
        return vpl

    @staticmethod
    def _calculate_tir(cash_flows: List[float]) -> float:
        """Calculates IRR (TIR) using Newton-Raphson"""
        if not cash_flows: return 0
        
        pos = any(cf > 0 for cf in cash_flows)
        neg = any(cf < 0 for cf in cash_flows)
        if not (pos and neg): return 0

        try:
            rate = 0.1
            for _ in range(100):
                vpl = 0
                deriv = 0
                for i, cf in enumerate(cash_flows):
                    vpl += cf / ((1 + rate) ** (i + 1))
                    deriv -= ((i + 1) * cf) / ((1 + rate) ** (i + 2))
                
                if abs(vpl) < 0.01: break
                if abs(deriv) < 0.000001: break
                
                rate = rate - vpl / deriv
            
            result = ((1 + rate) ** 12 - 1) * 100
            # Sanity check: TIRs above 10,000% are usually due to inconsistent input data
            if result > 10000 or result < -100:
                return None
            return result
        except Exception:
            return None

def _get_empty_finance():
    return {
        "metrics": {"payback": 0, "roi": 0, "tir": 0, "vpl": 0},
        "summary": {"total_investment": 0, "total_revenue": 0},
        "timeline": [],
        "params": {}
    }
