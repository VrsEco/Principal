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


def _json_error(exc: Exception, *, status: int = 400):
    return jsonify({"success": False, "error": str(exc)}), status


@real_estate_auctions_bp.route("/real-estate-auctions")
@login_required
def workspace():
    company = _resolve_company(action="view")
    filters = {
        "status": request.args.get("status") or None,
        "triage_status": request.args.get("triage_status") or None,
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

    return render_template(
        "modules/real_estate_auctions/workspace.html",
        company=company,
        company_id=company.id,
        workspace=workspace_payload,
        properties=properties,
        filters=filters,
        status_options=STATUS_OPTIONS,
        triage_options=TRIAGE_OPTIONS,
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

    return render_template(
        "modules/real_estate_auctions/property_detail.html",
        company=company,
        company_id=company.id,
        detail=detail,
        property=detail["property"],
        status_options=STATUS_OPTIONS,
        triage_options=TRIAGE_OPTIONS,
        can_edit=_has_module_permission(company.id, "edit"),
        can_delete=_has_module_permission(company.id, "delete"),
        can_manage_financial_sheet=_has_module_permission(company.id, "manage_financial_sheet"),
        can_manage_sources=_has_module_permission(company.id, "manage_sources"),
        attachment_categories=REAL_ESTATE_AUCTION_ATTACHMENT_CATEGORY_VALUES,
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
    return redirect(url_for("real_estate_auctions.property_detail", property_id=property_id, company_id=company.id))


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
    return redirect(url_for("real_estate_auctions.property_detail", property_id=property_id, company_id=company.id))


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/events/<int:event_id>/delete", methods=["POST"])
@login_required
def property_event_delete(property_id: int, event_id: int):
    company = _resolve_company(action="edit")
    try:
        RealEstateAuctionService.delete_event(company.id, property_id, event_id)
        flash("Evento removido com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return redirect(url_for("real_estate_auctions.property_detail", property_id=property_id, company_id=company.id))


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/financial-sheet", methods=["POST"])
@login_required
def property_financial_sheet_upsert(property_id: int):
    company = _resolve_company(action="manage_financial_sheet")
    try:
        RealEstateAuctionService.upsert_financial_sheet(company.id, property_id, _form_payload(FINANCIAL_SHEET_FORM_FIELDS))
        flash("Ficha financeira atualizada com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return redirect(url_for("real_estate_auctions.property_detail", property_id=property_id, company_id=company.id))


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
    return redirect(url_for("real_estate_auctions.property_detail", property_id=property_id, company_id=company.id))


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
    return redirect(url_for("real_estate_auctions.property_detail", property_id=property_id, company_id=company.id))


@real_estate_auctions_bp.route("/real-estate-auctions/properties/<int:property_id>/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
def property_attachment_delete(property_id: int, attachment_id: int):
    company = _resolve_company(action="edit")
    try:
        RealEstateAuctionService.delete_attachment(company.id, property_id, attachment_id)
        flash("Anexo removido com sucesso.", "success")
    except RealEstateAuctionError as exc:
        flash(str(exc), "error")
    return redirect(url_for("real_estate_auctions.property_detail", property_id=property_id, company_id=company.id))


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
            status=request.args.get("status") or None,
            triage_status=request.args.get("triage_status") or None,
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
