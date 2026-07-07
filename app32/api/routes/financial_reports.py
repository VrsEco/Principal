import io
import re

from flask import abort, jsonify, redirect, render_template, request, send_file, url_for

from services.financial_report_service import FinancialReportService
from utils.company_access import get_accessible_company_ids
from utils.permissions import permission_required

from .financial import financial_bp, get_active_company


_BOOLEAN_FILTER_KEYS = {
    "include_projected",
    "include_reconciled_only",
    "include_overdraft",
    "enable_title_exclusions",
    "include_open",
    "include_settled",
    "include_partial",
    "include_bordero",
    "include_receivable",
    "include_payable",
    "include_budget_vs_actual",
    "show_code",
    "show_description",
    "show_budget_column",
    "show_competence_column",
    "show_due_column",
    "show_liquidation_column",
    "show_title_number",
    "show_installment",
    "show_history",
    "show_counterparty",
    "show_title_amount",
    "show_correction_amount",
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
    "excluded_entry_ids",
    "excluded_projected_refs",
    "collapsed_row_ids",
    "visible_row_ids",
}

_SINGLE_VALUE_FILTER_KEYS = {
    "dossier_mode",
}

_IGNORED_FILTER_QUERY_KEYS = {
    "company_id",
    "bucket",
    "detail_chart_account_id",
    "title_filter_movement_nature",
    "title_filter_counterparty_id",
    "title_filter_chart_account_id",
    "title_filter_cost_center_id",
    "title_filter_search",
    "ui_refresh",
    "refresh",
}


def _normalize_list_filter_values(values):
    normalized = [value for value in values if value != '']
    if "-1" in normalized and any(value != "-1" for value in normalized):
        normalized = [value for value in normalized if value != "-1"]
    return normalized


def _request_filters_payload(*, excluded_keys=None):
    excluded = set(_IGNORED_FILTER_QUERY_KEYS)
    if excluded_keys:
        excluded.update({str(key) for key in excluded_keys if key})
    payload = {}
    manual_values = {}
    for key in request.args.keys():
        if key in excluded:
            continue
        values = _normalize_list_filter_values(request.args.getlist(key))
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
        if key in _SINGLE_VALUE_FILTER_KEYS:
            payload[key] = values[-1]
            continue
        payload[key] = values if len(values) > 1 else values[0]
    if manual_values:
        payload['manual_values'] = manual_values
    return payload


def _current_filters_state():
    state = {}
    for key in request.args.keys():
        values = _normalize_list_filter_values(request.args.getlist(key))
        if not values:
            continue
        if key in _BOOLEAN_FILTER_KEYS:
            state[key] = [values[-1]]
            continue
        state[key] = values
    return state


def _cash_flow_title_filter_payload():
    return {
        "movement_nature": request.args.get("title_filter_movement_nature"),
        "counterparty_id": request.args.get("title_filter_counterparty_id"),
        "chart_account_id": request.args.get("title_filter_chart_account_id"),
        "cost_center_id": request.args.get("title_filter_cost_center_id"),
        "search": request.args.get("title_filter_search"),
    }


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
    if report_definition["code"] in {"schedule_report", "bank_statement", "bank_statement_dossier", "income_statement", "income_statement_2", "ledger"}:
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


def _build_financial_report_with_definition_or_abort(report_slug: str, *, forced_filters: dict | None = None):
    company = get_active_company()
    if not company:
        abort(400, description='Empresa ativa não identificada para relatórios financeiros.')

    report_definition, error = FinancialReportService.get_report_definition_or_error(report_slug)
    if error:
        abort(404, description=error)

    filters_payload = _request_filters_payload()
    if forced_filters:
        filters_payload.update(forced_filters)

    report, error = FinancialReportService.build_management_report(
        company_id=company.id,
        report_type=report_definition["code"],
        filters=filters_payload,
        allowed_company_ids=get_accessible_company_ids(),
    )
    if error:
        abort(400, description=error)
    return company, report_definition, report


@financial_bp.route('/financial/reports/<report_slug>/view')
@permission_required('financial', 'view')
def financial_report_view_page(report_slug: str):
    if str(report_slug or '').strip().lower() in {'agendamento', 'extrato-bancario', 'dossie-extrato-bancario', 'demonstrativo-resultados', 'demonstrativo-resultados-02', 'razao'}:
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


@financial_bp.route('/financial/reports/<report_slug>/layout-test')
@permission_required('financial', 'view')
def financial_report_layout_test_page(report_slug: str):
    company, report_definition, report = _build_financial_report_with_definition_or_abort(
        report_slug,
        forced_filters={"orientation": "landscape"},
    )
    if report_definition["code"] != "bank_statement_dossier":
        abort(404, description='Página de teste disponível apenas para o Dossiê do Extrato Bancário.')

    return render_template(
        'modules/financial/report_layout_bank_statement_dossier_landscape_test.html',
        company=company,
        company_id=company.id,
        report_definition=report_definition,
        report=report,
    )


@financial_bp.route('/financial/reports/<report_slug>/drilldown')
@permission_required('financial', 'view')
def financial_report_income_statement_drilldown(report_slug: str):
    company = get_active_company()
    if not company:
        abort(400, description='Empresa ativa não identificada para relatórios financeiros.')

    bucket = request.args.get('bucket')
    raw_chart_account_id = request.args.get('detail_chart_account_id')
    using_legacy_chart_account_param = False
    if raw_chart_account_id in (None, ''):
        raw_chart_account_id = request.args.get('chart_account_id')
        using_legacy_chart_account_param = raw_chart_account_id not in (None, '')
    chart_account_id = None
    if raw_chart_account_id not in (None, ''):
        try:
            chart_account_id = int(raw_chart_account_id)
        except (TypeError, ValueError):
            abort(400, description='Conta contábil inválida para drill-down da DRE.')

    filters_payload = _request_filters_payload()
    if using_legacy_chart_account_param:
        filters_payload.pop('chart_account_id', None)

    payload, error = FinancialReportService.build_income_statement_drilldown(
        company_id=company.id,
        report_type=report_slug,
        bucket=bucket or '',
        chart_account_id=chart_account_id,
        filters=filters_payload,
        allowed_company_ids=get_accessible_company_ids(),
    )
    if error:
        abort(400, description=error)
    return jsonify(payload)


@financial_bp.route('/financial/reports/<report_slug>/projected-titles')
@permission_required('financial', 'view')
def financial_report_cash_flow_projected_titles(report_slug: str):
    company = get_active_company()
    if not company:
        abort(400, description='Empresa ativa não identificada para relatórios financeiros.')

    report_definition, error = FinancialReportService.get_report_definition_or_error(report_slug)
    if error or not report_definition or report_definition["code"] != "cash_flow":
        abort(404, description='Pré-visualização disponível apenas para o Fluxo de Caixa.')

    payload, error = FinancialReportService.build_cash_flow_title_preview(
        company_id=company.id,
        filters=_request_filters_payload(),
        selection_filters=_cash_flow_title_filter_payload(),
        allowed_company_ids=get_accessible_company_ids(),
    )
    if error:
        abort(400, description=error)
    return jsonify(payload)


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
