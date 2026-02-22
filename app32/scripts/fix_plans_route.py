
import re

file_path = r'c:\GestaoVersus\app32\api\routes\plans.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new implementation of the function
new_func = """@plans_bp.route('/<int:plan_id>/implantation')
@login_required
def implantation_dashboard(plan_id):
    \"\"\"Implantation planning dashboard.\"\"\"
    company = get_active_company()
    company_id = company.id if company else None
    
    data = PlanService.get_plan_dashboard_data(plan_id, company_id)
    if not data or data['plan']['mode'] != 'implantation':
        return redirect(url_for('plans.plans_list'))
        
    return render_template('modules/plans/implantation_dashboard.html', 
                           plan=data['plan'], 
                           company=company,
                           sections=data['sections'],
                           active_section='dashboard',
                           completed_sections=data['stats']['completed_sections'],
                           total_completable=data['stats']['total_completable'],
                           total_investment=data['finance']['total_investment'],
                           payback=data['finance']['payback'],
                           participants_count=data['stats']['participants_count'])
"""

# Use regex to find and replace the whole function
# Finding from @plans_bp.route('/<int:plan_id>/implantation') until the return statement
pattern = r"@plans_bp\.route\('/<int:plan_id>/implantation'\)\s+@login_required\s+def implantation_dashboard\(plan_id\):.*?return render_template\('modules/plans/implantation_dashboard\.html',.*?\)"

# The DOTALL flag allows . to match newlines
new_content = re.sub(pattern, new_func, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Refatoração aplicada com sucesso via Script de Elite.")
