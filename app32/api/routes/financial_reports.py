import io
import re

from flask import abort, redirect, render_template, request, send_file, url_for

from services.financial_report_service import FinancialReportService
from utils.company_access import get_accessible_company_ids
from utils.permissions import permission_required

from .financial import financial_bp, get_active_company


_BOOLEAN_FILTER_KEYS = {
    "include_projected",
    "include_reconciled_only",
    "include_overdraft",
    "include_open",
    "include_settled",
    "include_partial",
    "include_bordero",
    "include_receivable",
    "include_payable",
    "include_budget_vs_actual",
    "show_code",
    "show_description",
    "show_title_number",
    "show_installment",
    "show_history",
    "show_counterparty",
    "show_title_amount",
    "show_balance_amount",
    "show_competence_date",
    "show_due_date",
    "show_settlement_date",
}

_LIST_FILTER_KEYS = {
    "bank_account_ids",
    "chart_account_ids",
    "cost_center_ids",
    "project_ids",
    "process_ids",
    "working_capital_accounts",
    "counterparty_ids",
}


def _request_filters_payload():
    payload = {}
    manual_values = {}
    for key in request.args.keys():
        values = [value for value in request.args.getlist(key) if value != '']
        if not values:
            continue
        manual_match = re.match(r'^manual_value_(\d+)$', key)
        if manual_match:
            manual_values[int(manual_match.group(1))] = values[-1]
            continue
        if key in _BOOLEAN_FILTER_KEYS:
            payload[key] = values[-1]
            continue
        if key in _LIST_FILTER_KEYS:
            payload[key] = values
            continue
        payload[key] = values if len(values) > 1 else values[0]
    if manual_values:
        payload['manual_values'] = manual_values
    payload.pop('company_id', None)
    return payload


def _current_filters_state():
    state = {}
    for key in request.args.keys():
        values = [value for value in request.args.getlist(key) if value != '']
        if not values:
            continue
        if key in _BOOLEAN_FILTER_KEYS:
            state[key] = [values[-1]]
            continue
        state[key] = values
    return state


@financial_bp.route('/financial/reports')
@permission_required('financial', 'view')
def financial_reports_page():
    company = get_active_company()
    if not company:
        abort(400, description='Empresa ativa não identificada para relatórios financeiros.')
    return redirect(url_for('financial.financial_report_filters_page', report_slug='agendamento', company_id=company.id))


@financial_bp.route('/financial/reports/<report_slug>')
@permission_required('financial', 'view')
def financial_report_filters_page(report_slug: str):
    company = get_active_company()
    if not company:
        abort(400, description='Empresa ativa não identificada para relatórios financeiros.')

    report_definition, error = FinancialReportService.get_report_definition_or_error(report_slug)
    if error:
        abort(404, description=error)

    options, error = FinancialReportService.get_filter_options(
        company_id=company.id,
        allowed_company_ids=get_accessible_company_ids(),
    )
    if error:
        abort(403, description=error)

    default_period_start, default_period_end = FinancialReportService.default_period()
    current_filters = _current_filters_state()
    report = None
    if report_definition["code"] in {"schedule_report", "bank_statement", "income_statement"}:
        report, error = FinancialReportService.build_management_report(
            company_id=company.id,
            report_type=report_definition["code"],
            filters=_request_filters_payload(),
            allowed_company_ids=get_accessible_company_ids(),
        )
        if error:
            abort(400, description=error)
    return render_template(
        'modules/financial/report_filters.html',
        company=company,
        company_id=company.id,
        report_definition=report_definition,
        options=options,
        default_period_start=default_period_start.isoformat(),
        default_period_end=default_period_end.isoformat(),
        current_filters=current_filters,
        report=report,
    )


def _build_financial_report_or_abort(report_slug: str):
    company = get_active_company()
    if not company:
        abort(400, description='Empresa ativa não identificada para relatórios financeiros.')

    report, error = FinancialReportService.build_management_report(
        company_id=company.id,
        report_type=report_slug,
        filters=_request_filters_payload(),
        allowed_company_ids=get_accessible_company_ids(),
    )
    if error:
        abort(400, description=error)
    return company, report


@financial_bp.route('/financial/reports/<report_slug>/view')
@permission_required('financial', 'view')
def financial_report_view_page(report_slug: str):
    if str(report_slug or '').strip().lower() in {'agendamento', 'extrato-bancario', 'demonstrativo-resultados'}:
        target = url_for('financial.financial_report_filters_page', report_slug=report_slug)
        query_string = request.query_string.decode('utf-8')
        if query_string:
            target = f'{target}?{query_string}'
        return redirect(target)
    company, report = _build_financial_report_or_abort(report_slug)
    return render_template(
        'modules/financial/report_view.html',
        company=company,
        company_id=company.id,
        report=report,
    )


@financial_bp.route('/financial/reports/<report_slug>/export.xlsx')
@financial_bp.route('/financial/reports/<report_slug>/export-xlsx')
@permission_required('financial', 'view')
def financial_report_export_xlsx(report_slug: str):
    company, report = _build_financial_report_or_abort(report_slug)
    report["company_name"] = company.name
    content = FinancialReportService.export_xlsx(report)
    return send_file(
        io.BytesIO(content),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"{report['report_slug']}_{company.id}.xlsx",
    )


@financial_bp.route('/financial/reports/<report_slug>/export.pdf')
@financial_bp.route('/financial/reports/<report_slug>/export-pdf')
@permission_required('financial', 'view')
def financial_report_export_pdf(report_slug: str):
    company, report = _build_financial_report_or_abort(report_slug)
    report["company_name"] = company.name
    pdf_bytes = FinancialReportService.export_pdf(report)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{report['report_slug']}_{company.id}.pdf",
    )
