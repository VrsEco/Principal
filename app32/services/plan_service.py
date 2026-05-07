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
            parts = [part for part in normalized.split('-') if part]
            if len(parts) >= 2 and all(part.isdigit() for part in parts[:3]):
                if len(parts[0]) == 4:
                    year, month = int(parts[0]), int(parts[1])
                elif len(parts) >= 3 and len(parts[2]) == 4:
                    year, month = int(parts[2]), int(parts[1])
                else:
                    year, month = int(parts[0]), int(parts[1])

                if 1 <= month <= 12:
                    return f"{year:04d}-{month:02d}"
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
    def _resolve_ramp_percentage(product: Dict[str, Any], period: str) -> float:
        """
        Resolve o percentual de ramp-up válido para o período.
        Mantém o último percentual conhecido para meses posteriores ao último marco,
        evitando zerar a operação após o fim do ramp-up cadastrado.
        """
        ramp_entries = product.get('ramp_up_entries') or []
        normalized_entries: List[Tuple[str, float]] = []

        for entry in ramp_entries:
            if not isinstance(entry, dict):
                continue
            entry_period = PlanService._normalize_period(entry.get('month_period'))
            if not entry_period:
                continue
            normalized_entries.append((entry_period, float(entry.get('percentage') or 0)))

        if not normalized_entries:
            return 0.0

        normalized_entries.sort(key=lambda item: item[0])
        current_percentage = 0.0
        for entry_period, percentage in normalized_entries:
            if entry_period > period:
                break
            current_percentage = percentage

        return current_percentage

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
    def _normalize_finance_tax_rules(fin_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normaliza regras de impostos em uma estrutura estável."""
        normalized_rules: List[Dict[str, Any]] = []
        for rule in fin_content.get('taxes', []) if isinstance(fin_content, dict) else []:
            if not isinstance(rule, dict):
                continue
            description = (rule.get('description') or "").strip()
            if not description:
                continue
            normalized_rules.append({
                "description": description,
                "percentage": float(rule.get('percentage') or 0),
                "base": (rule.get('base') or 'operating_result').strip(),
                "base_label": PlanService._tax_base_label(rule.get('base') or 'operating_result'),
            })
        return normalized_rules

    @staticmethod
    def _tax_base_label(base_key: str) -> str:
        return {
            "revenue": "Faturamento",
            "gross_margin": "Lucro Bruto",
            "operating_result": "Lucro Operacional",
            "operating_result_additional_ir": "Lucro Operacional p/ Adicional IR",
        }.get(base_key, base_key or "Base")

    @staticmethod
    def _build_tax_base_snapshot(period_revenue: float, period_variable_costs: float, period_variable_expenses: float,
                                 period_fixed_costs: float, period_fixed_expenses: float) -> Dict[str, float]:
        """Calcula as bases fiscais do período."""
        gross_margin = period_revenue - period_variable_costs - period_variable_expenses
        operating_result_before_taxes = gross_margin - period_fixed_costs - period_fixed_expenses
        additional_ir_base = max(operating_result_before_taxes - 20000.0, 0.0)
        return {
            "revenue": period_revenue,
            "gross_margin": gross_margin,
            "operating_result": operating_result_before_taxes,
            "operating_result_additional_ir": additional_ir_base,
        }

    @staticmethod
    def _calculate_tax_lines(tax_rules: List[Dict[str, Any]], base_snapshot: Dict[str, float]) -> Tuple[List[Dict[str, Any]], float]:
        """Calcula os impostos do período a partir das regras configuradas."""
        tax_lines: List[Dict[str, Any]] = []
        taxes_total = 0.0

        for rule in tax_rules:
            base_key = rule.get('base') or 'operating_result'
            base_value = float(base_snapshot.get(base_key) or 0)
            taxable_base = max(base_value, 0.0)
            amount = taxable_base * (float(rule.get('percentage') or 0) / 100.0)
            taxes_total += amount
            tax_lines.append({
                "description": rule.get('description') or "Imposto",
                "percentage": float(rule.get('percentage') or 0),
                "base": base_key,
                "base_label": PlanService._tax_base_label(base_key),
                "base_value": taxable_base,
                "amount": amount,
            })

        return tax_lines, taxes_total

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
        period_months = int(params.get('period_months') or 60)
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
        normalized_params_start_date = PlanService._normalize_period(params_start_date)
        if normalized_params_start_date:
            start_date_str = normalized_params_start_date
        else:
            candidate_dates = list(ramp_up_dates)

            for source in PlanService._normalize_finance_sources(fin_content):
                if source.get('type') == 'propria':
                    candidate_dates.append(source.get('date'))

            for item in investment_items + fixed_cost_items + fixed_expense_items:
                candidate_dates.extend(PlanService._collect_execution_item_dates(item))

            valid_dates = sorted(date for date in candidate_dates if PlanService._normalize_period(date))
            if not valid_dates:
                start_date_str = datetime.now().strftime('%Y-%m')
            else:
                start_date_str = PlanService._normalize_period(valid_dates[0])

        start_year, start_month = map(int, start_date_str.split('-')[:2])
        params = {**params, 'start_date': start_date_str}

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
        
        # 7. Taxes & Distributions
        tax_rules = PlanService._normalize_finance_tax_rules(fin_content)
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
                ramp_percentage = PlanService._resolve_ramp_percentage(p, period)
                if ramp_percentage > 0:
                    units = p.get('market_share_goal_monthly_units', 0) * (ramp_percentage / 100)
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
            base_snapshot = PlanService._build_tax_base_snapshot(
                period_revenue,
                period_variable_costs,
                period_variable_expenses,
                period_fixed_costs,
                period_fixed_expenses,
            )
            gmc = base_snapshot["gross_margin"]
            operating_result_before_taxes = base_snapshot["operating_result"]
            tax_lines, taxes_total = PlanService._calculate_tax_lines(tax_rules, base_snapshot)
            operating_result = operating_result_before_taxes - taxes_total
            
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

            # Business Net Flow = Net Operating Result + Full Funding Flow (Equity + Loans - Capex)
            # Mantém a visão completa do caixa do negócio no período, incluindo aportes próprios
            # e financiamentos, sem perder a separação analítica do fluxo do investidor.
            business_net_flow = period_net_operating + period_investment_flow
            cumulative_business_flow += business_net_flow

            timeline.append({
                "period": period,
                "revenue": period_revenue,
                "variable_costs": period_variable_costs,
                "variable_expenses": period_variable_expenses,
                "gmc": gmc,
                "fixed_costs": period_fixed_costs,
                "fixed_expenses": period_fixed_expenses,
                "operating_result_before_taxes": operating_result_before_taxes,
                "tax_lines": tax_lines,
                "taxes_total": taxes_total,
                "tax_base_values": base_snapshot,
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
        tax_preview_index = min(ramp_up_end_index, len(timeline) - 1) if timeline else -1
        tax_preview = timeline[tax_preview_index] if tax_preview_index >= 0 else {}

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
                "total_operating_result": sum(t['operating_result'] for t in timeline),
                "total_taxes": sum(t.get('taxes_total') or 0 for t in timeline),
            },
            "investments": {
                "working_capital_lines": working_capital_lines,
                "fixed_asset_rows": fixed_asset_rows,
                "timeline_total_investment": total_investment_capex,
            },
            "taxes": {
                "rules": tax_rules,
                "preview_period": tax_preview.get('period') or "",
                "preview_tax_lines": tax_preview.get('tax_lines', []) if isinstance(tax_preview, dict) else [],
                "preview_base_values": tax_preview.get('tax_base_values', {}) if isinstance(tax_preview, dict) else {},
            },
            "timeline": timeline,
            "params": params,
            "ramp_up_end_index": ramp_up_end_index
        }

    @staticmethod
    def _normalize_finance_sources(fin_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normaliza fontes financeiras legadas e v2 em uma única estrutura."""
        sources_data = fin_content.get('sources_v2', [])
        normalized_sources: List[Dict[str, Any]] = []

        if sources_data:
            for source in sources_data:
                if not isinstance(source, dict):
                    continue
                normalized_sources.append({
                    "name": source.get('name') or "Fonte",
                    "type": source.get('type') or "propria",
                    "date": PlanService._normalize_period(source.get('date')),
                    "amount": float(source.get('amount') or 0),
                })
            return normalized_sources

        legacy_sources = fin_content.get('sources', {})
        legacy_dates = fin_content.get('source_dates', {})
        if isinstance(legacy_sources, dict):
            for name, value in legacy_sources.items():
                normalized_sources.append({
                    "name": name or "Fonte",
                    "type": "propria",
                    "date": PlanService._normalize_period(legacy_dates.get(name)),
                    "amount": float(value or 0),
                })
        elif isinstance(legacy_sources, list):
            for item in legacy_sources:
                if not isinstance(item, dict):
                    continue
                normalized_sources.append({
                    "name": item.get('description') or item.get('category') or "Fonte",
                    "type": item.get('type') or "propria",
                    "date": PlanService._normalize_period(item.get('availability') or item.get('date')),
                    "amount": float(item.get('amount') or 0),
                })

        return normalized_sources

    @staticmethod
    def _build_implantation_execution_area_report(execution_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Consolida áreas de execução para exibição no relatório."""
        area_catalog = {
            "comercial": "Estruturação Comercial",
            "operacional": "Estruturação Operacional",
            "admin": "Estruturação Adm/Fin",
        }
        execution_areas = []
        raw_areas = execution_content.get('areas', {}) if isinstance(execution_content, dict) else {}

        for area_id, area_title in area_catalog.items():
            raw_area = raw_areas.get(area_id, {}) if isinstance(raw_areas, dict) else {}
            raw_items = raw_area.get('items', []) if isinstance(raw_area, dict) else []
            normalized_items = []

            total_value = 0.0
            total_capacity = 0.0
            acquisition_total = 0.0
            hiring_total = 0.0

            for item in raw_items:
                if not isinstance(item, dict):
                    continue

                planned_value = float(item.get('value') or 0)
                capacity_value = float(item.get('operational_capacity_revenue') or 0)
                payment_entries = PlanService._expand_execution_item_payments(item)
                payment_plan = item.get('payment_plan') or {}
                payment_mode = payment_plan.get('mode') or ('multiple' if item.get('classification') == 'aquisição' else 'single')

                normalized_items.append({
                    "description": item.get('description') or "Item sem descrição",
                    "item_type": item.get('item_type') or "-",
                    "classification": item.get('classification') or "-",
                    "acquisition_date": PlanService._normalize_period(item.get('acquisition_date')),
                    "availability_date": PlanService._normalize_period(item.get('availability_date')),
                    "capacity_revenue": capacity_value,
                    "planned_value": planned_value,
                    "payment_count": len(payment_entries),
                    "payment_mode": payment_mode,
                    "payments": payment_entries,
                })

                total_value += planned_value
                total_capacity += capacity_value
                if item.get('classification') == 'aquisição':
                    acquisition_total += planned_value
                else:
                    hiring_total += planned_value

            execution_areas.append({
                "id": area_id,
                "title": area_title,
                "items": normalized_items,
                "item_count": len(normalized_items),
                "total_value": total_value,
                "total_capacity": total_capacity,
                "acquisition_total": acquisition_total,
                "hiring_total": hiring_total,
            })

        return execution_areas

    @staticmethod
    def get_implantation_report_context(plan_id: int, company_id: int) -> Dict[str, Any]:
        """Monta um contexto detalhado e estável para o relatório final de implantação."""
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan or plan.mode != 'implantation':
            return {}

        alignment_data = PlanService.get_implantation_data(plan_id, company_id, 'alignment')
        model_data = PlanService.get_implantation_data(plan_id, company_id, 'model')
        execution_data = PlanService.get_implantation_data(plan_id, company_id, 'execution')
        finance_data = PlanService.get_implantation_data(plan_id, company_id, 'finance')

        alignment = alignment_data.content if alignment_data else {}
        model = model_data.content if model_data else {}
        execution = execution_data.content if execution_data else {}
        finance = finance_data.content if finance_data else {}
        consolidated = PlanService.get_consolidated_finance(plan_id, company_id)

        participants = PlanParticipant.query.filter_by(plan_id=plan_id).all()
        participant_rows = []
        for participant in participants:
            display_name = None
            if getattr(participant, 'employee', None):
                display_name = getattr(participant.employee, 'name', None)
            if not display_name and getattr(participant, 'user', None):
                display_name = getattr(participant.user, 'name', None) or getattr(participant.user, 'email', None)

            participant_rows.append({
                "name": display_name or f"Participante #{participant.id}",
                "role": participant.role or "viewer",
            })

        products = []
        for product in model.get('products', []) if isinstance(model, dict) else []:
            if not isinstance(product, dict):
                continue
            sale_price = float(product.get('sale_price') or 0)
            variable_costs = float(product.get('variable_costs_value') or 0)
            variable_expenses = float(product.get('variable_expenses_value') or 0)
            contribution_value = sale_price - variable_costs - variable_expenses
            ramp_entries = product.get('ramp_up_entries') or []
            normalized_ramp = [
                {
                    "period": PlanService._normalize_period(entry.get('month_period')),
                    "percentage": float(entry.get('percentage') or 0),
                }
                for entry in ramp_entries
                if isinstance(entry, dict)
            ]
            ramp_periods = [entry["period"] for entry in normalized_ramp if entry.get("period")]

            products.append({
                **product,
                "sale_price": sale_price,
                "variable_costs_value": variable_costs,
                "variable_expenses_value": variable_expenses,
                "contribution_margin_value": contribution_value,
                "contribution_margin_percent": ((contribution_value / sale_price) * 100) if sale_price > 0 else 0,
                "expected_monthly_revenue": sale_price * float(product.get('market_share_goal_monthly_units') or 0),
                "ramp_up_entries": normalized_ramp,
                "ramp_up_start": ramp_periods[0] if ramp_periods else "",
                "ramp_up_end": ramp_periods[-1] if ramp_periods else "",
                "ramp_up_months": len(ramp_periods),
            })

        segments = []
        for segment in model.get('segments', []) if isinstance(model, dict) else []:
            if not isinstance(segment, dict):
                continue
            personas = segment.get('personas') or []
            differentials = segment.get('differential_matrix') or []
            segments.append({
                **segment,
                "persona_count": len(personas),
                "audience_count": len(segment.get('audiences') or []),
                "problem_count": len(segment.get('problems') or []),
                "differential_count": len(differentials),
            })

        working_capital = finance.get('working_capital') or {}
        working_capital_groups = [
            {
                "key": "cash_items",
                "title": "Caixa",
                "items": working_capital.get('cash_items', []),
            },
            {
                "key": "receivables_items",
                "title": "Contas a Receber",
                "items": working_capital.get('receivables_items', []),
            },
            {
                "key": "inventory_items",
                "title": "Estoques",
                "items": working_capital.get('inventory_items', []),
            },
        ]
        for group in working_capital_groups:
            group["subtotal"] = sum(float(item.get('value') or 0) for item in group["items"] if isinstance(item, dict))

        sources = PlanService._normalize_finance_sources(finance)
        timeline = consolidated.get('timeline', []) if isinstance(consolidated, dict) else []
        active_timeline = [
            row for row in timeline
            if any(
                float(row.get(metric) or 0) != 0
                for metric in (
                    'revenue', 'investment', 'sources_equity', 'loans',
                    'operating_result', 'distributions', 'fixed_costs', 'fixed_expenses',
                    'taxes_total'
                )
            )
        ]
        timeline_focus = timeline or active_timeline

        payback_month = ""
        for row in timeline:
            if float(row.get('cumulative_investor') or 0) >= 0:
                payback_month = row.get('period') or ""
                break

        peak_revenue = max(timeline, key=lambda row: float(row.get('revenue') or 0), default={})
        peak_investment = max(timeline, key=lambda row: float(row.get('investment') or 0), default={})
        ramp_up_end_index = consolidated.get('ramp_up_end_index', 0) if isinstance(consolidated, dict) else 0
        ramp_up_end_period = ""
        if timeline and isinstance(ramp_up_end_index, int) and 0 <= ramp_up_end_index < len(timeline):
            ramp_up_end_period = timeline[ramp_up_end_index].get('period') or ""

        ramp_up_timeline = timeline[:ramp_up_end_index + 1] if timeline else []
        working_capital_settings = {
            "cash_reserve": float(working_capital.get('cash_reserve') or 0),
            "receivables_days": int(working_capital.get('receivables_days') or 30),
            "inventory_days": int(working_capital.get('inventory_days') or 30),
            "payable_days": int(working_capital.get('payable_days') or 30),
        }
        fixed_asset_rows = (consolidated.get('investments', {}) or {}).get('fixed_asset_rows', []) if isinstance(consolidated, dict) else []

        return {
            "alignment": alignment,
            "model": model,
            "execution": execution,
            "finance": finance,
            "consolidated": consolidated,
            "participants": participant_rows,
            "products": products,
            "segments": segments,
            "execution_areas": PlanService._build_implantation_execution_area_report(execution),
            "working_capital_groups": working_capital_groups,
            "working_capital_settings": working_capital_settings,
            "fixed_asset_rows": fixed_asset_rows,
            "funding_sources": sources,
            "profit_distribution": finance.get('profit_distribution', []) if isinstance(finance, dict) else [],
            "tax_rules": (consolidated.get('taxes', {}) or {}).get('rules', []) if isinstance(consolidated, dict) else [],
            "timeline_focus": timeline_focus,
            "ramp_up_timeline": ramp_up_timeline,
            "finance_executive_summary": finance.get('executive_summary', "") if isinstance(finance, dict) else "",
            "report_summary": {
                "partners_count": len(alignment.get('partners', [])) if isinstance(alignment, dict) else 0,
                "participants_count": len(participant_rows),
                "products_count": len(products),
                "segments_count": len(segments),
                "execution_items_count": sum(area["item_count"] for area in PlanService._build_implantation_execution_area_report(execution)),
                "active_timeline_months": len(active_timeline),
                "payback_period": payback_month,
                "ramp_up_end_period": ramp_up_end_period,
                "peak_revenue_period": peak_revenue.get('period') or "",
                "peak_investment_period": peak_investment.get('period') or "",
            }
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
        "summary": {"total_investment": 0, "total_revenue": 0, "total_taxes": 0},
        "taxes": {"rules": [], "preview_period": "", "preview_tax_lines": [], "preview_base_values": {}},
        "timeline": [],
        "params": {}
    }
