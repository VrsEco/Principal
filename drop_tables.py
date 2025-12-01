from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

password = quote_plus("*Paraiso1978")
url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
engine = create_engine(url, isolation_level="AUTOCOMMIT")

tables_to_drop = [
    'vision_records', 'plan_alignment_overview', 'plan_finance_investor_periods',
    'company_performance_settings', 'plan_sections', 'market_records', 'process_instances',
    'report_templates', 'plan_finance_variable_costs', 'okrs', 'report_models',
    'plan_finance_investment_categories', 'plan_finance_metrics', 'routine_collaborators',
    'ui_elements_v2', 'report_patterns', 'plan_alignment_project', 'okr_preliminary_records',
    'process_activities', 'indicator_goals', 'plan_finance_result_rules',
    'plan_finance_investments', 'routines', 'processes', 'plan_structure_capacities',
    'plan_alignment_members', 'process_instance_collaborators', 'indicator_groups',
    'company_projects', 'process_activity_entries', 'ui_pages_v2', 'ui_pages',
    'misalignment_records', 'directional_records', 'okr_global_records',
    'plan_alignment_agenda', 'project_activities', 'plan_finance_capital_giro',
    'macro_processes', 'portfolios', 'meetings', 'routine_triggers',
    'plan_finance_investment_contributions', 'meeting_agenda_items',
    'plan_finance_business_distribution', 'plan_finance_premises',
    'plan_product_monthly_growth', 'plan_implantation_dashboard', 'company_records',
    'workshop_discussions', 'okr_area_records', 'plan_finance_investment_items',
    'plan_sales_rampup_config', 'alignment_records', 'plan_alignment_principles',
    'ui_elements', 'plan_segments', 'okr_area_preliminary_records',
    'plan_implantation_phases', 'ui_audit_log', 'indicator_data', 'drivers',
    'process_areas', 'indicators', 'plan_implantation_checkpoints',
    'plan_structure_installments', 'report_instances', 'occurrences',
    'plan_finance_business_periods', 'routine_tasks', 'interviews',
    'plan_finance_profit_distribution', 'plan_structures', 'okr_global_key_results',
    'plan_finance_funding_sources', 'plan_finance_sources'
]

with engine.connect() as conn:
    for table in tables_to_drop:
        print(f"Dropping {table}...")
        try:
            conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        except Exception as e:
            print(f"Error dropping {table}: {e}")
    print("Done.")
