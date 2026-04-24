import io
from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, send_file

from api.routes.financial import get_active_company
from services.financial_import_service import FinancialImportService
from utils.permissions import permission_required


financial_automation_bp = Blueprint("financial_automation", __name__)


def _financial_automation_asset_version() -> str:
    root = Path(current_app.root_path)
    candidates = [
        root / "static" / "css" / "financial_automation_center.css",
        root / "static" / "js" / "financial_automation_center.js",
        root / "templates" / "modules" / "financial" / "automation_center.html",
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return "1"
    latest_mtime = max(int(path.stat().st_mtime) for path in existing)
    return str(latest_mtime)


@financial_automation_bp.route("/financial/automation")
@permission_required("financial", "view")
def financial_automation_page():
    company = get_active_company()
    return render_template(
        "modules/financial/automation_center.html",
        company=company,
        company_id=company.id if company else None,
        asset_version=_financial_automation_asset_version(),
    )


@financial_automation_bp.route("/financial/automation/template")
@permission_required("financial", "view")
def financial_automation_template_download():
    content, error = FinancialImportService.build_import_template()
    if error:
        abort(500, description=error)

    return send_file(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="app32_modelo_importacao_automacao_financeira.xlsx",
    )
