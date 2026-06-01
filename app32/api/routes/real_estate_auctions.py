from __future__ import annotations

from typing import Any

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from models import Company, Employee, db
from models.real_estate_auction import REAL_ESTATE_AUCTION_ATTACHMENT_CATEGORY_VALUES
from services.real_estate_auction_service import RealEstateAuctionError, RealEstateAuctionService
from utils.permissions import can_access_company, get_default_company_id, has_company_full_access, has_permission


real_estate_auctions_bp = Blueprint("real_estate_auctions", __name__)


STATUS_OPTIONS = [
    ("draft", "Rascunho"),
    ("in_analysis", "Em análise"),
    ("awaiting_auction", "Aguardando leilão"),
    ("won", "Arrematado"),
    ("lost", "Perdido"),
    ("discarded", "Descartado"),
    ("available_for_sale", "Disponível para venda"),
    ("sold", "Vendido"),
]

TRIAGE_OPTIONS = [
    ("pending", "Pendente"),
    ("awaiting_auction", "Aguardando leilão"),
    ("auction_won", "Leilão ganho"),
    ("auction_lost", "Leilão perdido"),
    ("discarded", "Descartado"),
]

PROPERTY_FORM_FIELDS = [
    "code",
    "nickname",
    "address",
    "district",
    "city",
    "state",
    "zip_code",
    "property_type",
    "auxiliary_filter",
    "sale_modality",
    "land_area",
    "private_area",
    "built_area",
    "registry_number",
    "registry_office",
    "court_district",
    "bank",
    "status",
    "triage_status",
    "triage_reason_code",
    "triage_reason_label",
    "triage_notes",
    "appraisal_value",
    "estimated_quick_sale_value",
    "estimated_normal_sale_value",
    "recommended_max_bid",
    "auctioneer",
    "auction_url",
    "notice_url",
    "buyer_name",
    "broker_name",
    "closed_sale_value",
    "auction_won_at",
    "available_for_sale_at",
    "sold_at",
]
EVENT_FORM_FIELDS = [
    "auction_type",
    "auction_datetime",
    "minimum_bid",
    "modality",
    "auctioneer",
    "winning_bid",
    "result",
    "notes",
]
FINANCIAL_SHEET_FORM_FIELDS = [
    "winning_bid",
    "auctioneer_commission_percent",
    "other_acquisition_costs",
    "transfer_tax_percent",
    "transfer_tax_value",
    "registry_cost_percent",
    "registry_cost_value",
    "eviction_cost",
    "renovation_budget",
    "cleaning_cost",
    "overdue_property_tax",
    "future_property_tax",
    "overdue_condo_fee",
    "future_condo_fee",
    "legal_fees",
    "contingency_value",
    "capital_cost_months",
    "capital_cost_percent",
    "minimum_profit_percent",
    "minimum_profit_value",
    "projected_sale_value",
    "broker_commission_percent",
    "sale_tax_percent",
    "operational_expenses",
]
DUE_DILIGENCE_FORM_FIELDS = [
    "condo_fee_value",
    "building_age",
    "building_description",
    "property_description",
    "region_square_meter_value",
    "resident_report",
    "manager_report",
    "other_debts",
    "internal_notes",
]
ATTACHMENT_FORM_FIELDS = [
    "category",
    "original_filename",
    "stored_filename",
    "storage_path",
    "mime_type",
    "size_bytes",
]
SOURCE_FORM_FIELDS = [
    "name",
    "domain",
    "base_url",
    "link_pattern",
    "listing_selector",
]
STATUS_LABEL_MAP = dict(STATUS_OPTIONS)
TRIAGE_LABEL_MAP = dict(TRIAGE_OPTIONS)
WORKSPACE_FILTER_FIELDS = [
    {"name": "q", "label": "Buscar imóvel", "kind": "text", "placeholder": "Código, apelido ou endereço"},
    {"name": "status", "label": "Status", "kind": "select", "options": [("", "Todos")] + STATUS_OPTIONS},
    {"name": "triage_status", "label": "Triagem", "kind": "select", "options": [("", "Todas")] + TRIAGE_OPTIONS},
    {"name": "property_type", "label": "Tipo do imóvel", "kind": "text", "placeholder": "Casa, apartamento, terreno"},
    {"name": "bank", "label": "Banco", "kind": "text", "placeholder": "Caixa, Santander..."},
    {"name": "occupied", "label": "Ocupação", "kind": "select", "options": [("", "Todos"), ("1", "Ocupado"), ("0", "Desocupado")]},
    {"name": "city", "label": "Cidade", "kind": "text", "placeholder": "Feira de Santana"},
    {"name": "state", "label": "UF", "kind": "text", "placeholder": "BA", "maxlength": 2},
]
DETAIL_TABS = [
    {"id": "overview", "label": "Imóvel", "description": "Cadastro principal, localização e triagem."},
    {"id": "events", "label": "Leilões", "description": "Linha do tempo de leilões e resultados."},
    {"id": "financial", "label": "Financeiro", "description": "Viabilidade, custos e margem."},
    {"id": "due_diligence", "label": "Diligência", "description": "Posse, risco, débitos e observações."},
    {"id": "attachments", "label": "Anexos", "description": "Dossiê documental do imóvel."},
]
OVERVIEW_SECTIONS = [
    {
        "title": "Identificação",
        "fields": [
            {"name": "code", "label": "Código", "kind": "text", "required": True, "placeholder": "GND-001"},
            {"name": "nickname", "label": "Apelido", "kind": "text", "placeholder": "Casa Centro"},
            {"name": "property_type", "label": "Tipo do imóvel", "kind": "text"},
            {"name": "sale_modality", "label": "Modalidade", "kind": "text"},
        ],
    },
    {
        "title": "Localização",
        "fields": [
            {"name": "address", "label": "Endereço", "kind": "text", "required": True, "span": 2},
            {"name": "district", "label": "Bairro", "kind": "text"},
            {"name": "city", "label": "Cidade", "kind": "text"},
            {"name": "state", "label": "UF", "kind": "text", "maxlength": 2},
            {"name": "zip_code", "label": "CEP", "kind": "text"},
        ],
    },
    {
        "title": "Triagem e operação",
        "fields": [
            {"name": "status", "label": "Status", "kind": "select", "options": STATUS_OPTIONS},
            {"name": "triage_status", "label": "Triagem", "kind": "select", "options": TRIAGE_OPTIONS},
            {"name": "triage_reason_code", "label": "Código do motivo", "kind": "text"},
            {"name": "triage_reason_label", "label": "Motivo da triagem", "kind": "text"},
            {"name": "occupied", "label": "Imóvel ocupado", "kind": "checkbox", "span": 2},
            {"name": "triage_notes", "label": "Observações de triagem", "kind": "textarea", "rows": 3, "span": 2},
        ],
    },
    {
        "title": "Dados físicos e registrais",
        "fields": [
            {"name": "land_area", "label": "Área do terreno (m²)", "kind": "decimal"},
            {"name": "private_area", "label": "Área privativa (m²)", "kind": "decimal"},
            {"name": "built_area", "label": "Área construída (m²)", "kind": "decimal"},
            {"name": "auxiliary_filter", "label": "Filtro auxiliar", "kind": "text"},
            {"name": "registry_number", "label": "Matrícula", "kind": "text"},
            {"name": "registry_office", "label": "Cartório", "kind": "text"},
            {"name": "court_district", "label": "Comarca", "kind": "text"},
            {"name": "bank", "label": "Banco", "kind": "text"},
        ],
    },
    {
        "title": "Leitura econômica e comercial",
        "fields": [
            {"name": "appraisal_value", "label": "Valor avaliado", "kind": "money"},
            {"name": "estimated_quick_sale_value", "label": "Venda rápida estimada", "kind": "money"},
            {"name": "estimated_normal_sale_value", "label": "Venda normal estimada", "kind": "money"},
            {"name": "recommended_max_bid", "label": "Lance máximo recomendado", "kind": "money"},
            {"name": "closed_sale_value", "label": "Venda fechada", "kind": "money"},
            {"name": "auctioneer", "label": "Leiloeiro principal", "kind": "text"},
            {"name": "auction_url", "label": "URL do leilão", "kind": "url", "span": 2},
            {"name": "notice_url", "label": "URL do edital", "kind": "url", "span": 2},
            {"name": "buyer_name", "label": "Comprador", "kind": "text"},
            {"name": "broker_name", "label": "Corretor", "kind": "text"},
            {"name": "auction_won_at", "label": "Arrematado em", "kind": "datetime"},
            {"name": "available_for_sale_at", "label": "Disponível em", "kind": "datetime"},
            {"name": "sold_at", "label": "Vendido em", "kind": "datetime"},
        ],
    },
]
EVENT_FORM_SCHEMA = [
    {"name": "auction_type", "label": "Tipo do leilão", "kind": "text", "required": True},
    {"name": "auction_datetime", "label": "Data e hora", "kind": "datetime"},
    {"name": "minimum_bid", "label": "Lance mínimo", "kind": "money"},
    {"name": "modality", "label": "Modalidade", "kind": "text"},
    {"name": "auctioneer", "label": "Leiloeiro", "kind": "text"},
    {"name": "winning_bid", "label": "Lance vencedor", "kind": "money"},
    {"name": "result", "label": "Resultado", "kind": "text"},
    {"name": "notes", "label": "Notas", "kind": "textarea", "rows": 3, "span": 2},
]
FINANCIAL_SECTIONS = [
    {
        "title": "Aquisição e impostos",
        "fields": [
            {"name": "winning_bid", "label": "Lance vencedor", "kind": "money"},
            {"name": "auctioneer_commission_percent", "label": "Comissão leiloeiro (%)", "kind": "percent", "step": "0.0001"},
            {"name": "other_acquisition_costs", "label": "Outros custos de aquisição", "kind": "money"},
            {"name": "transfer_tax_percent", "label": "ITBI (%)", "kind": "percent", "step": "0.0001"},
            {"name": "transfer_tax_value", "label": "ITBI (valor)", "kind": "money"},
            {"name": "registry_cost_percent", "label": "Registro (%)", "kind": "percent", "step": "0.0001"},
            {"name": "registry_cost_value", "label": "Registro (valor)", "kind": "money"},
        ],
    },
    {
        "title": "Obras, débitos e custos operacionais",
        "fields": [
            {"name": "eviction_cost", "label": "Desocupação", "kind": "money"},
            {"name": "renovation_budget", "label": "Reforma", "kind": "money"},
            {"name": "cleaning_cost", "label": "Limpeza", "kind": "money"},
            {"name": "overdue_property_tax", "label": "IPTU vencido", "kind": "money"},
            {"name": "future_property_tax", "label": "IPTU futuro", "kind": "money"},
            {"name": "overdue_condo_fee", "label": "Condomínio vencido", "kind": "money"},
            {"name": "future_condo_fee", "label": "Condomínio futuro", "kind": "money"},
            {"name": "legal_fees", "label": "Honorários jurídicos", "kind": "money"},
            {"name": "contingency_value", "label": "Contingência", "kind": "money"},
            {"name": "operational_expenses", "label": "Despesas operacionais", "kind": "money"},
        ],
    },
    {
        "title": "Capital, margem e saída",
        "fields": [
            {"name": "capital_cost_months", "label": "Custo de capital (meses)", "kind": "int"},
            {"name": "capital_cost_percent", "label": "Custo de capital (%)", "kind": "percent", "step": "0.0001"},
            {"name": "minimum_profit_percent", "label": "Lucro mínimo (%)", "kind": "percent", "step": "0.0001"},
            {"name": "minimum_profit_value", "label": "Lucro mínimo (valor)", "kind": "money"},
            {"name": "projected_sale_value", "label": "Venda projetada", "kind": "money"},
            {"name": "broker_commission_percent", "label": "Comissão corretor (%)", "kind": "percent", "step": "0.0001"},
            {"name": "sale_tax_percent", "label": "Impostos sobre venda (%)", "kind": "percent", "step": "0.0001"},
        ],
    },
]
DUE_DILIGENCE_SECTIONS = [
    {
        "title": "Riscos e contato",
        "fields": [
            {"name": "condo_fee_value", "label": "Condomínio", "kind": "money"},
            {"name": "building_age", "label": "Idade do prédio", "kind": "int"},
            {"name": "region_square_meter_value", "label": "R$/m² da região", "kind": "money"},
            {"name": "other_debts", "label": "Outras dívidas", "kind": "money"},
            {"name": "resident_contacted", "label": "Morador contatado", "kind": "checkbox", "span": 2},
            {"name": "manager_contacted", "label": "Síndico contatado", "kind": "checkbox", "span": 2},
        ],
    },
    {
        "title": "Descrição e observações",
        "fields": [
            {"name": "building_description", "label": "Descrição do prédio", "kind": "textarea", "rows": 3, "span": 2},
            {"name": "property_description", "label": "Descrição do imóvel", "kind": "textarea", "rows": 3, "span": 2},
            {"name": "resident_report", "label": "Relato do morador", "kind": "textarea", "rows": 3, "span": 2},
            {"name": "manager_report", "label": "Relato do síndico", "kind": "textarea", "rows": 3, "span": 2},
            {"name": "internal_notes", "label": "Notas internas", "kind": "textarea", "rows": 3, "span": 2},
        ],
    },
]
ATTACHMENT_FORM_SCHEMA = [
    {"name": "category", "label": "Categoria", "kind": "select", "options": [(item, item) for item in REAL_ESTATE_AUCTION_ATTACHMENT_CATEGORY_VALUES]},
    {"name": "original_filename", "label": "Arquivo original", "kind": "text", "required": True},
    {"name": "stored_filename", "label": "Arquivo interno", "kind": "text"},
    {"name": "storage_path", "label": "Storage path", "kind": "text"},
    {"name": "mime_type", "label": "MIME type", "kind": "text"},
    {"name": "size_bytes", "label": "Tamanho (bytes)", "kind": "int"},
]
SOURCE_FORM_SCHEMA = [
    {"name": "name", "label": "Nome da fonte", "kind": "text", "required": True},
    {"name": "domain", "label": "Domínio", "kind": "text"},
    {"name": "base_url", "label": "Base URL", "kind": "url", "required": True},
    {"name": "link_pattern", "label": "Pattern do link", "kind": "text"},
    {"name": "listing_selector", "label": "Selector da listagem", "kind": "text", "span": 2},
    {"name": "active", "label": "Fonte ativa", "kind": "checkbox", "span": 2},
]


def _current_user_id() -> int | None:
    if getattr(current_user, "is_authenticated", False):
        return getattr(current_user, "id", None)
    return None


def _request_company_id() -> int | None:
    company_id = request.args.get("company_id", type=int) or request.form.get("company_id", type=int)
    if company_id:
        return company_id

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        try:
            return int(payload.get("company_id")) if payload.get("company_id") else None
        except (TypeError, ValueError):
            abort(400, description="company_id inválido.")

    return session.get("active_company_id")


def _resolve_company(*, require_permission: bool = True, action: str = "view") -> Company:
    company_id = _request_company_id()
    if not company_id and getattr(current_user, "is_authenticated", False):
        employee = Employee.query.filter_by(user_id=current_user.id, status="active").first()
        company_id = getattr(employee, "company_id", None) or get_default_company_id()

    company = Company.query.get(company_id) if company_id else None
    if company is None:
        abort(400, description="Empresa ativa obrigatória para operar Leilões Imobiliários.")

    if not can_access_company(company.id):
        abort(403, description="Empresa fora do escopo do usuário autenticado.")

    if require_permission and not _has_module_permission(company.id, action):
        abort(403, description=f"Permissão negada para Leilões Imobiliários: {action}.")

    session["active_company_id"] = company.id
    return company


def _has_module_permission(company_id: int, action: str) -> bool:
    if has_company_full_access(company_id):
        return True
    return has_permission(company_id, RealEstateAuctionService.MODULE_KEY, action)


def _require_write_access(company_id: int, action: str = "edit") -> None:
    if not _has_module_permission(company_id, action):
        abort(403, description=f"Permissão negada para Leilões Imobiliários: {action}.")


def _property_payload_from_form() -> dict[str, Any]:
    payload = {field: request.form.get(field) for field in PROPERTY_FORM_FIELDS if field in request.form}
    payload["occupied"] = bool(request.form.get("occupied"))
    return payload


def _json_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        abort(400, description="Payload deve ser um objeto JSON.")
    return payload


def _form_payload(fields: list[str]) -> dict[str, Any]:
    return {field: request.form.get(field) for field in fields if field in request.form}


def _parse_optional_bool(raw_value: str | None) -> bool | None:
    if raw_value in (None, ""):
        return None
    return str(raw_value).strip().lower() in {"1", "true", "sim", "yes"}


def _active_detail_tab() -> str:
    allowed = {item["id"] for item in DETAIL_TABS}
    raw = (request.args.get("tab") or request.form.get("tab") or "overview").strip().lower()
    return raw if raw in allowed else "overview"


def _detail_redirect(company_id: int, property_id: int, *, fallback_tab: str | None = None):
    tab = fallback_tab or _active_detail_tab()
    return redirect(url_for("real_estate_auctions.property_detail", property_id=property_id, company_id=company_id, tab=tab))


def _html_datetime_value(value: Any) -> str:
    if not value:
        return ""
    text = str(value).strip()
    return text[:16] if "T" in text else text.replace(" ", "T")[:16]


def _json_error(exc: Exception, *, status: int = 400):
    return jsonify({"success": False, "error": str(exc)}), status


@real_estate_auctions_bp.route("/real-estate-auctions")
@login_required
def workspace():
    company = _resolve_company(action="view")
    filters = {
        "q": request.args.get("q") or None,
        "status": request.args.get("status") or None,
        "triage_status": request.args.get("triage_status") or None,
        "property_type": request.args.get("property_type") or None,
        "bank": request.args.get("bank") or None,
        "occupied": _parse_optional_bool(request.args.get("occupied")),
        "city": request.args.get("city") or None,
        "state": request.args.get("state") or None,
    }
    try:
        workspace_payload = RealEstateAuctionService.get_workspace(company.id, include_disabled=True)
        if workspace_payload["settings"].get("module_enabled"):
            properties = RealEstateAuctionService.list_properties(company.id, **filters, limit=100)
        else:
            properties = []
    except RealEstateAuctionError as exc:
        flash(str(exc), "warning")
        workspace_payload = RealEstateAuctionService.get_workspace(company.id, include_disabled=True)
        properties = []

    kanban_columns = [
        {
            **column,
            "label": STATUS_LABEL_MAP.get(column["status"], column["status"]),
        }
        for column in RealEstateAuctionService.group_properties_by_status(properties)
    ]

    return render_template(
        "modules/real_estate_auctions/workspace.html",
        company=company,
        company_id=company.id,
        workspace=workspace_payload,
        properties=properties,
        kanban_columns=kanban_columns,
        filters=filters,
        filter_fields=WORKSPACE_FILTER_FIELDS,
        status_options=STATUS_OPTIONS,
        status_label_map=STATUS_LABEL_MAP,
        triage_options=TRIAGE_OPTIONS,
        triage_label_map=TRIAGE_LABEL_MAP,
        can_create=_has_module_permission(company.id, "create"),
        can_edit=_has_module_permission(company.id, "edit"),
        can_configure=_has_module_permission(company.id, "configure"),
        can_manage_sources=_has_module_permission(company.id, "manage_sources"),
    )


@real_estate_auctions_bp.route("/real-estate-auctions/settings", methods=["POST"])
@login_required
def settings_update():
    company = _resolve_company(action="view")
    _require_write_access(company.id, "configure")
    payload = {
        "module_enabled": bool(request.form.get("module_enabled")),
        "display_name": request.form.get("display_name") or RealEstateAuctionService.DEFAULT_DISPLAY_NAME,
        "code_prefix": request.form.get("code_prefix") or None,
    }
    try:
        RealEstateAuctionService.upsert_tenant_settings(company.id, payload)
        flash("Configuração de Leilões Imobiliários atualizada.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return redirect(url_for("real_estate_auctions.workspace", company_id=company.id))


@real_estate_auctions_bp.route("/real-estate-auctions/properties/new")
@login_required
def property_new():
    company = _resolve_company(action="create")
    try:
        RealEstateAuctionService.ensure_module_enabled(company.id)
    except RealEstateAuctionError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("real_estate_auctions.workspace", company_id=company.id))

    return render_template(
        "modules/real_estate_auctions/property_form.html",
        company=company,
        company_id=company.id,
        property=None,
        status_options=STATUS_OPTIONS,
        triage_options=TRIAGE_OPTIONS,
        form_action=url_for("real_estate_auctions.property_create", company_id=company.id),
    )


@real_estate_auctions_bp.route("/real-estate-auctions/properties", methods=["POST"])
@login_required
def property_create():
    company = _resolve_company(action="create")
    try:
        row = RealEstateAuctionService.create_property(
            company.id,
            _property_payload_from_form(),
            user_id=_current_user_id(),
        )
        flash("Imóvel criado com sucesso.", "success")
        return redirect(url_for("real_estate_auctions.property_detail", property_id=row["id"], company_id=company.id))
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
        return redirect(url_for("real_estate_auctions.property_new", company_id=company.id))


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>")
@login_required
def property_detail(property_id: int):
    company = _resolve_company(action="view")
    try:
        detail = RealEstateAuctionService.get_property_detail(company.id, property_id)
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
        return redirect(url_for("real_estate_auctions.workspace", company_id=company.id))

    active_tab = _active_detail_tab()
    return render_template(
        "modules/real_estate_auctions/property_detail.html",
        company=company,
        company_id=company.id,
        detail=detail,
        property=detail["property"],
        active_tab=active_tab,
        detail_tabs=DETAIL_TABS,
        overview_sections=OVERVIEW_SECTIONS,
        event_form_schema=EVENT_FORM_SCHEMA,
        financial_sections=FINANCIAL_SECTIONS,
        due_diligence_sections=DUE_DILIGENCE_SECTIONS,
        attachment_form_schema=ATTACHMENT_FORM_SCHEMA,
        source_form_schema=SOURCE_FORM_SCHEMA,
        status_options=STATUS_OPTIONS,
        status_label_map=STATUS_LABEL_MAP,
        triage_options=TRIAGE_OPTIONS,
        triage_label_map=TRIAGE_LABEL_MAP,
        can_edit=_has_module_permission(company.id, "edit"),
        can_delete=_has_module_permission(company.id, "delete"),
        can_manage_financial_sheet=_has_module_permission(company.id, "manage_financial_sheet"),
        can_manage_sources=_has_module_permission(company.id, "manage_sources"),
        attachment_categories=REAL_ESTATE_AUCTION_ATTACHMENT_CATEGORY_VALUES,
        html_datetime_value=_html_datetime_value,
    )


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/edit")
@login_required
def property_edit(property_id: int):
    company = _resolve_company(action="edit")
    try:
        detail = RealEstateAuctionService.get_property_detail(company.id, property_id)
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
        return redirect(url_for("real_estate_auctions.workspace", company_id=company.id))

    return render_template(
        "modules/real_estate_auctions/property_form.html",
        company=company,
        company_id=company.id,
        property=detail["property"],
        status_options=STATUS_OPTIONS,
        triage_options=TRIAGE_OPTIONS,
        form_action=url_for("real_estate_auctions.property_update", property_id=property_id, company_id=company.id),
    )


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>", methods=["POST"])
@login_required
def property_update(property_id: int):
    company = _resolve_company(action="edit")
    try:
        RealEstateAuctionService.update_property(
            company.id,
            property_id,
            _property_payload_from_form(),
            user_id=_current_user_id(),
        )
        flash("Imóvel atualizado com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
        return redirect(url_for("real_estate_auctions.property_edit", property_id=property_id, company_id=company.id))
    return _detail_redirect(company.id, property_id)


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/archive", methods=["POST"])
@login_required
def property_archive(property_id: int):
    company = _resolve_company(action="delete")
    try:
        RealEstateAuctionService.archive_property(company.id, property_id, user_id=_current_user_id())
        flash("Imóvel arquivado com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return redirect(url_for("real_estate_auctions.workspace", company_id=company.id))


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/events", methods=["POST"])
@login_required
def property_event_create(property_id: int):
    company = _resolve_company(action="edit")
    try:
        RealEstateAuctionService.create_event(company.id, property_id, _form_payload(EVENT_FORM_FIELDS))
        flash("Evento de leilão registrado com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return _detail_redirect(company.id, property_id, fallback_tab="events")


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/events/<int:event_id>/delete", methods=["POST"])
@login_required
def property_event_delete(property_id: int, event_id: int):
    company = _resolve_company(action="edit")
    try:
        RealEstateAuctionService.delete_event(company.id, property_id, event_id)
        flash("Evento removido com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return _detail_redirect(company.id, property_id, fallback_tab="events")


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/financial-sheet", methods=["POST"])
@login_required
def property_financial_sheet_upsert(property_id: int):
    company = _resolve_company(action="manage_financial_sheet")
    try:
        RealEstateAuctionService.upsert_financial_sheet(company.id, property_id, _form_payload(FINANCIAL_SHEET_FORM_FIELDS))
        flash("Ficha financeira atualizada com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return _detail_redirect(company.id, property_id, fallback_tab="financial")


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/due-diligence", methods=["POST"])
@login_required
def property_due_diligence_upsert(property_id: int):
    company = _resolve_company(action="edit")
    try:
        payload = _form_payload(DUE_DILIGENCE_FORM_FIELDS)
        payload["resident_contacted"] = bool(request.form.get("resident_contacted"))
        payload["manager_contacted"] = bool(request.form.get("manager_contacted"))
        RealEstateAuctionService.upsert_due_diligence(company.id, property_id, payload)
        flash("Diligência atualizada com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return _detail_redirect(company.id, property_id, fallback_tab="due_diligence")


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/attachments", methods=["POST"])
@login_required
def property_attachment_create(property_id: int):
    company = _resolve_company(action="edit")
    try:
        RealEstateAuctionService.create_attachment(
            company.id,
            property_id,
            _form_payload(ATTACHMENT_FORM_FIELDS),
            user_id=_current_user_id(),
        )
        flash("Metadado de anexo registrado com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return _detail_redirect(company.id, property_id, fallback_tab="attachments")


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
def property_attachment_delete(property_id: int, attachment_id: int):
    company = _resolve_company(action="edit")
    try:
        RealEstateAuctionService.delete_attachment(company.id, property_id, attachment_id)
        flash("Anexo removido com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return _detail_redirect(company.id, property_id, fallback_tab="attachments")


@real_estate_auctions_bp.route("/real-estate-auctions/sources", methods=["POST"])
@login_required
def source_create():
    company = _resolve_company(action="manage_sources")
    try:
        payload = _form_payload(SOURCE_FORM_FIELDS)
        payload["active"] = bool(request.form.get("active"))
        RealEstateAuctionService.create_source(company.id, payload)
        flash("Fonte cadastrada com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return redirect(url_for("real_estate_auctions.workspace", company_id=company.id))


@real_estate_auctions_bp.route("/real-estate-auctions/sources/<int:source_id>/delete", methods=["POST"])
@login_required
def source_delete(source_id: int):
    company = _resolve_company(action="manage_sources")
    try:
        RealEstateAuctionService.delete_source(company.id, source_id)
        flash("Fonte removida com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return redirect(url_for("real_estate_auctions.workspace", company_id=company.id))


@real_estate_auctions_bp.route("/api/real-estate-auctions/settings", methods=["GET"])
@login_required
def api_settings_get():
    company = _resolve_company(action="view")
    return jsonify({"success": True, "settings": RealEstateAuctionService.get_tenant_settings(company.id)})


@real_estate_auctions_bp.route("/api/real-estate-auctions/settings", methods=["POST"])
@login_required
def api_settings_upsert():
    company = _resolve_company(action="configure")
    try:
        settings = RealEstateAuctionService.upsert_tenant_settings(company.id, _json_payload())
        return jsonify({"success": True, "settings": settings})
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/workspace", methods=["GET"])
@login_required
def api_workspace():
    company = _resolve_company(action="view")
    try:
        return jsonify({"success": True, "workspace": RealEstateAuctionService.get_workspace(company.id)})
    except RealEstateAuctionError as exc:
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties", methods=["GET"])
@login_required
def api_properties_list():
    company = _resolve_company(action="view")
    try:
        properties = RealEstateAuctionService.list_properties(
            company.id,
            q=request.args.get("q") or None,
            status=request.args.get("status") or None,
            triage_status=request.args.get("triage_status") or None,
            property_type=request.args.get("property_type") or None,
            bank=request.args.get("bank") or None,
            occupied=_parse_optional_bool(request.args.get("occupied")),
            city=request.args.get("city") or None,
            state=request.args.get("state") or None,
            limit=request.args.get("limit", default=100, type=int),
        )
        return jsonify({"success": True, "properties": properties})
    except RealEstateAuctionError as exc:
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties", methods=["POST"])
@login_required
def api_property_create():
    company = _resolve_company(action="create")
    try:
        row = RealEstateAuctionService.create_property(company.id, _json_payload(), user_id=_current_user_id())
        return jsonify({"success": True, "property": row}), 201
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties/<int:property_id>", methods=["GET"])
@login_required
def api_property_get(property_id: int):
    company = _resolve_company(action="view")
    try:
        return jsonify({"success": True, "detail": RealEstateAuctionService.get_property_detail(company.id, property_id)})
    except RealEstateAuctionError as exc:
        return _json_error(exc, status=404)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties/<int:property_id>", methods=["PATCH"])
@login_required
def api_property_update(property_id: int):
    company = _resolve_company(action="edit")
    try:
        row = RealEstateAuctionService.update_property(company.id, property_id, _json_payload(), user_id=_current_user_id())
        return jsonify({"success": True, "property": row})
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties/<int:property_id>", methods=["DELETE"])
@login_required
def api_property_archive(property_id: int):
    company = _resolve_company(action="delete")
    try:
        payload = RealEstateAuctionService.archive_property(company.id, property_id, user_id=_current_user_id())
        return jsonify({"success": True, **payload})
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties/<int:property_id>/events", methods=["POST"])
@login_required
def api_property_event_create(property_id: int):
    company = _resolve_company(action="edit")
    try:
        event = RealEstateAuctionService.create_event(company.id, property_id, _json_payload())
        return jsonify({"success": True, "event": event}), 201
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties/<int:property_id>/events/<int:event_id>", methods=["PATCH"])
@login_required
def api_property_event_update(property_id: int, event_id: int):
    company = _resolve_company(action="edit")
    try:
        event = RealEstateAuctionService.update_event(company.id, property_id, event_id, _json_payload())
        return jsonify({"success": True, "event": event})
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties/<int:property_id>/events/<int:event_id>", methods=["DELETE"])
@login_required
def api_property_event_delete(property_id: int, event_id: int):
    company = _resolve_company(action="edit")
    try:
        payload = RealEstateAuctionService.delete_event(company.id, property_id, event_id)
        return jsonify({"success": True, **payload})
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties/<int:property_id>/financial-sheet", methods=["PUT"])
@login_required
def api_property_financial_sheet_upsert(property_id: int):
    company = _resolve_company(action="manage_financial_sheet")
    try:
        sheet = RealEstateAuctionService.upsert_financial_sheet(company.id, property_id, _json_payload())
        return jsonify({"success": True, "financial_sheet": sheet})
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties/<int:property_id>/due-diligence", methods=["PUT"])
@login_required
def api_property_due_diligence_upsert(property_id: int):
    company = _resolve_company(action="edit")
    try:
        due = RealEstateAuctionService.upsert_due_diligence(company.id, property_id, _json_payload())
        return jsonify({"success": True, "due_diligence": due})
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties/<int:property_id>/attachments", methods=["POST"])
@login_required
def api_property_attachment_create(property_id: int):
    company = _resolve_company(action="edit")
    try:
        attachment = RealEstateAuctionService.create_attachment(
            company.id,
            property_id,
            _json_payload(),
            user_id=_current_user_id(),
        )
        return jsonify({"success": True, "attachment": attachment}), 201
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/properties/<int:property_id>/attachments/<int:attachment_id>", methods=["DELETE"])
@login_required
def api_property_attachment_delete(property_id: int, attachment_id: int):
    company = _resolve_company(action="edit")
    try:
        payload = RealEstateAuctionService.delete_attachment(company.id, property_id, attachment_id)
        return jsonify({"success": True, **payload})
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/sources", methods=["GET"])
@login_required
def api_sources_list():
    company = _resolve_company(action="view")
    try:
        return jsonify({"success": True, "sources": RealEstateAuctionService.list_sources(company.id)})
    except RealEstateAuctionError as exc:
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/sources", methods=["POST"])
@login_required
def api_source_create():
    company = _resolve_company(action="manage_sources")
    try:
        source = RealEstateAuctionService.create_source(company.id, _json_payload())
        return jsonify({"success": True, "source": source}), 201
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/sources/<int:source_id>", methods=["PATCH"])
@login_required
def api_source_update(source_id: int):
    company = _resolve_company(action="manage_sources")
    try:
        source = RealEstateAuctionService.update_source(company.id, source_id, _json_payload())
        return jsonify({"success": True, "source": source})
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)


@real_estate_auctions_bp.route("/api/real-estate-auctions/sources/<int:source_id>", methods=["DELETE"])
@login_required
def api_source_delete(source_id: int):
    company = _resolve_company(action="manage_sources")
    try:
        payload = RealEstateAuctionService.delete_source(company.id, source_id)
        return jsonify({"success": True, **payload})
    except RealEstateAuctionError as exc:
        db.session.rollback()
        return _json_error(exc)
