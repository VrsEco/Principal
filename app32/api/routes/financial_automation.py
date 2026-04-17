from flask import Blueprint, render_template

from api.routes.financial import get_active_company
from utils.permissions import permission_required


financial_automation_bp = Blueprint("financial_automation", __name__)


@financial_automation_bp.route("/financial/automation")
@permission_required("financial", "view")
def financial_automation_page():
    company = get_active_company()
    return render_template(
        "modules/financial/automation_center.html",
        company=company,
        company_id=company.id if company else None,
    )
