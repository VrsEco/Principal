import io

from flask import Blueprint, abort, render_template, request, send_file, session
from flask_login import current_user

from models import Company, FinancialEntry
from services.financial_import_service import FinancialImportService
from services.financial_budget_import_service import FinancialBudgetImportService
from utils.permissions import get_default_company_id, has_permission, permission_required


financial_bp = Blueprint("financial", __name__)


FINANCIAL_CATALOG_PAGES = {
    "bank-accounts": {
        "api_type": "bank_accounts",
        "title": "Contas Bancárias",
        "new_label": "Nova conta bancária",
        "eyebrow": "Base operacional",
        "description": "Gestão de contas bancárias, PIX, agência, conta, titularidade e moeda base do financeiro.",
    },
    "chart-accounts": {
        "api_type": "chart_accounts",
        "title": "Plano de Contas",
        "new_label": "Nova conta",
        "eyebrow": "Estrutura contábil",
        "description": "Estruture contas e naturezas para lançamentos, relatórios e evolução futura por árvore e parâmetros.",
    },
    "cost-centers": {
        "api_type": "cost_centers",
        "title": "Centros de Resultados",
        "new_label": "Novo centro de resultados",
        "eyebrow": "Estrutura gerencial",
        "description": "Organize rateios, análises gerenciais e futuras abas específicas por centro, gestor e governança.",
    },
    "counterparties": {
        "api_type": "counterparties",
        "title": "Favorecidos",
        "new_label": "Novo favorecido",
        "eyebrow": "Relacionamentos financeiros",
        "description": "Cadastre fornecedores e favorecidos com dados operacionais, defaults financeiros e evolução por abas.",
    },
    "account-categories": {
        "api_type": "account_categories",
        "title": "Categorias de Conta",
        "new_label": "Nova categoria",
        "eyebrow": "Classificação auxiliar",
        "description": "Classifique contas e lançamentos com categorias auxiliares do financeiro.",
    },
    "payment-terms": {
        "api_type": "payment_terms",
        "title": "Condições de Pagamento",
        "new_label": "Nova condição",
        "eyebrow": "Parâmetros comerciais",
        "description": "Defina parcelamento, intervalo e padrões para previsões e títulos.",
    },
    "asset-accounts": {
        "api_type": "asset_accounts",
        "title": "Contas Patrimoniais",
        "new_label": "Nova conta patrimonial",
        "eyebrow": "Patrimônio",
        "description": "Cadastre contas patrimoniais para controle de bens, ativos e integrações correlatas.",
    },
    "correction-indexes": {
        "api_type": "correction_indexes",
        "title": "Correções Financeiras",
        "new_label": "Nova correção",
        "eyebrow": "Ajustes financeiros",
        "description": "Mantenha índices e parâmetros de correção para contratos e lançamentos.",
    },
    "discount-rules": {
        "api_type": "discount_rules",
        "title": "Descontos",
        "new_label": "Novo desconto",
        "eyebrow": "Condições comerciais",
        "description": "Cadastre regras de desconto para reutilização em lançamentos e integrações.",
    },
    "payment-methods": {
        "api_type": "payment_methods",
        "title": "Formas Financeiras",
        "new_label": "Nova forma financeira",
        "eyebrow": "Meios de pagamento",
        "description": "Mantenha formas financeiras usadas no operacional, importações e automações.",
    },
}


def get_active_company():
    from models import Employee

    company_id = request.args.get("company_id", type=int) or session.get("active_company_id")

    if not company_id and current_user.is_authenticated:
        employee = Employee.query.filter_by(user_id=current_user.id, status="active").first()
        if employee and employee.company_id:
            company_id = employee.company_id
        else:
            company_id = get_default_company_id()

    if company_id:
        if not has_permission(company_id, "financial", "view"):
            abort(403, description="Acesso negado ao contexto financeiro da empresa.")
        session["active_company_id"] = company_id
        return Company.query.get(company_id)

    return None


def _get_entry_with_access(entry_id: int) -> FinancialEntry:
    entry = FinancialEntry.query.get_or_404(entry_id)
    if not current_user.is_authenticated:
        abort(403, description="Usuário não autenticado.")

    if session.get("active_company_id") != entry.company_id:
        session["active_company_id"] = entry.company_id

    if not has_permission(entry.company_id, "financial", "view"):
        abort(403, description="Acesso negado ao lançamento financeiro solicitado.")

    return entry


@financial_bp.route("/financial")
@financial_bp.route("/financial/dashboard")
@permission_required("financial", "view")
def financial_dashboard_page():
    company = get_active_company()
    return render_template(
        "modules/financial/dashboard.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/entries")
@permission_required("financial", "view")
def financial_entries_page():
    company = get_active_company()
    return render_template(
        "modules/financial/entries_list.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/entries/direct")
@permission_required("financial", "create")
def financial_direct_entry_page():
    company = get_active_company()
    return render_template(
        "modules/financial/entry_direct.html",
        company=company,
        company_id=company.id if company else None,
        initial_entry_type=(request.args.get("entry_type") or "").strip().lower(),
    )


@financial_bp.route("/financial/entries/<int:entry_id>")
@permission_required("financial", "view")
def financial_entry_manage(entry_id: int):
    entry = _get_entry_with_access(entry_id)
    company = Company.query.get(entry.company_id)
    return render_template(
        "modules/financial/entry_manage.html",
        company=company,
        company_id=entry.company_id,
        entry_id=entry.id,
        entry=entry,
    )


@financial_bp.route("/financial/imports/<int:batch_id>")
@permission_required("financial", "view")
def financial_import_batch_manage(batch_id: int):
    company = get_active_company()
    return render_template(
        "modules/financial/import_batch_manage.html",
        company=company,
        company_id=company.id if company else None,
        batch_id=batch_id,
    )


@financial_bp.route("/financial/import-template")
@permission_required("financial", "view")
def financial_import_template_download():
    content, error = FinancialImportService.build_import_template()
    if error:
        abort(500, description=error)

    return send_file(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="app32_modelo_importacao_financeira.xlsx",
    )


@financial_bp.route("/financial/budget-template")
@permission_required("financial", "view")
def financial_budget_template_download():
    company = get_active_company()
    company_id = company.id if company else None
    version_id = request.args.get("version_id", type=int)
    if not company_id or not version_id:
        abort(400, description="Informe company_id e version_id para gerar o modelo de orçamento.")

    content, error = FinancialBudgetImportService.build_template(
        company_id=company_id,
        version_id=version_id,
    )
    if error:
        abort(400, description=error)

    return send_file(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"app32_modelo_orcamento_{version_id}.xlsx",
    )


@financial_bp.route("/financial/classification-rules")
@permission_required("financial", "view")
def financial_classification_rules_page():
    company = get_active_company()
    return render_template(
        "modules/financial/classification_rules.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/classification-memories")
@permission_required("financial", "view")
def financial_classification_memories_page():
    company = get_active_company()
    return render_template(
        "modules/financial/classification_memories.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/classification-queue")
@permission_required("financial", "view")
def financial_classification_queue_page():
    company = get_active_company()
    return render_template(
        "modules/financial/classification_queue.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/classification-dashboard")
@permission_required("financial", "view")
def financial_classification_dashboard_page():
    company = get_active_company()
    return render_template(
        "modules/financial/classification_dashboard.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/catalogs")
@permission_required("financial", "view")
def financial_catalogs_page():
    company = get_active_company()
    return render_template(
        "modules/financial/catalogs.html",
        company=company,
        company_id=company.id if company else None,
        catalog_pages=FINANCIAL_CATALOG_PAGES,
    )


@financial_bp.route("/financial/catalogs/<string:catalog_slug>")
@permission_required("financial", "view")
def financial_catalog_detail_page(catalog_slug: str):
    catalog_page = FINANCIAL_CATALOG_PAGES.get(catalog_slug)
    if not catalog_page:
        abort(404, description="Cadastro financeiro não encontrado.")

    company = get_active_company()
    template_name = "modules/financial/catalog_detail.html"
    if catalog_slug == "counterparties":
        template_name = "modules/financial/counterparties_workspace.html"
    return render_template(
        template_name,
        company=company,
        company_id=company.id if company else None,
        catalog_slug=catalog_slug,
        catalog_pages=FINANCIAL_CATALOG_PAGES,
        catalog_page=catalog_page,
    )


@financial_bp.route("/financial/domain-enablements")
@permission_required("financial", "view")
def financial_domain_enablements_page():
    company = get_active_company()
    return render_template(
        "modules/financial/domain_enablements.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/ingestions")
@permission_required("financial", "view")
def financial_ingestions_page():
    company = get_active_company()
    return render_template(
        "modules/financial/ingestions.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/schedules")
@permission_required("financial", "view")
def financial_schedules_page():
    company = get_active_company()
    return render_template(
        "modules/financial/schedules_list.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/schedules/new")
@financial_bp.route("/financial/schedules/<int:schedule_id>")
@permission_required("financial", "view")
def financial_schedule_form_page(schedule_id: int | None = None):
    company = get_active_company()
    return render_template(
        "modules/financial/schedules.html",
        company=company,
        company_id=company.id if company else None,
        schedule_id=schedule_id,
        initial_entry_type=(request.args.get("entry_type") or "").strip().lower(),
    )


@financial_bp.route("/financial/automation-rules")
@permission_required("financial", "view")
def financial_automation_rules_page():
    company = get_active_company()
    return render_template(
        "modules/financial/automation_rules.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/automation-audit")
@permission_required("financial", "view")
def financial_automation_audit_page():
    company = get_active_company()
    return render_template(
        "modules/financial/automation_audit.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/closings")
@permission_required("financial", "view")
def financial_closings_page():
    company = get_active_company()
    return render_template(
        "modules/financial/closings.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/reports")
@permission_required("financial", "view")
def financial_reports_page():
    company = get_active_company()
    return render_template(
        "modules/financial/reports.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/budget")
@permission_required("financial", "view")
def financial_budget_planning_page():
    company = get_active_company()
    return render_template(
        "modules/financial/budget_matrix.html",
        company=company,
        company_id=company.id if company else None,
    )


@financial_bp.route("/financial/budget/execution")
@permission_required("financial", "view")
def financial_budget_execution_page():
    company = get_active_company()
    return render_template(
        "modules/financial/budget_execution.html",
        company=company,
        company_id=company.id if company else None,
    )
