from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func

from models import (
    Company,
    RealEstateAuctionAttachment,
    RealEstateAuctionDueDiligence,
    RealEstateAuctionEvent,
    RealEstateAuctionFinancialSheet,
    RealEstateAuctionProperty,
    RealEstateAuctionSource,
    RealEstateAuctionTenantSettings,
    db,
)
from models.real_estate_auction import (
    REAL_ESTATE_AUCTION_ATTACHMENT_CATEGORY_VALUES,
    REAL_ESTATE_AUCTION_STATUS_VALUES,
    REAL_ESTATE_AUCTION_TRIAGE_STATUS_VALUES,
)


class RealEstateAuctionError(ValueError):
    """Erro de domínio do módulo Leilões Imobiliários."""


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_int(value: Any, *, field: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise RealEstateAuctionError(f"Campo '{field}' deve ser inteiro.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RealEstateAuctionError(f"Campo '{field}' deve ser inteiro.") from exc


def _safe_decimal(value: Any, *, field: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception as exc:  # noqa: BLE001 - erro de domínio com mensagem controlada
        raise RealEstateAuctionError(f"Campo '{field}' deve ser numérico.") from exc


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return False
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "sim", "yes", "y", "s", "ativo", "enabled"}:
        return True
    if normalized in {"0", "false", "nao", "não", "no", "n", "inativo", "disabled"}:
        return False
    return bool(value)


class RealEstateAuctionService:
    """Service tenant-safe do módulo Leilões Imobiliários.

    O serviço é intencionalmente genérico: GanduInvest é apenas uma configuração
    por empresa em `real_estate_auction_tenant_settings`, não um fork de código.
    """

    MODULE_KEY = "real_estate_auctions"
    DEFAULT_DISPLAY_NAME = "Leilões Imobiliários"

    PROPERTY_TEXT_FIELDS = {
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
        "registry_number",
        "registry_office",
        "court_district",
        "bank",
        "triage_reason_code",
        "triage_reason_label",
        "triage_notes",
        "auctioneer",
        "auction_url",
        "notice_url",
        "buyer_name",
        "broker_name",
    }
    PROPERTY_DECIMAL_FIELDS = {
        "land_area",
        "private_area",
        "built_area",
        "appraisal_value",
        "estimated_quick_sale_value",
        "estimated_normal_sale_value",
        "recommended_max_bid",
        "closed_sale_value",
    }
    PROPERTY_BOOL_FIELDS = {"occupied"}
    PROPERTY_DATETIME_FIELDS = {"auction_won_at", "available_for_sale_at", "sold_at", "deleted_at"}
    PROPERTY_JSON_FIELDS = {"metadata_json"}
    EVENT_TEXT_FIELDS = {"auction_type", "modality", "auctioneer", "result", "notes"}
    EVENT_DECIMAL_FIELDS = {"minimum_bid", "winning_bid"}
    EVENT_DATETIME_FIELDS = {"auction_datetime"}
    FINANCIAL_DECIMAL_FIELDS = {
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
        "capital_cost_percent",
        "minimum_profit_percent",
        "minimum_profit_value",
        "projected_sale_value",
        "broker_commission_percent",
        "sale_tax_percent",
        "operational_expenses",
    }
    FINANCIAL_INT_FIELDS = {"capital_cost_months"}
    FINANCIAL_JSON_FIELDS = {"last_calculation_snapshot_json"}
    DUE_DILIGENCE_TEXT_FIELDS = {
        "building_description",
        "property_description",
        "resident_report",
        "manager_report",
        "internal_notes",
    }
    DUE_DILIGENCE_DECIMAL_FIELDS = {"condo_fee_value", "region_square_meter_value", "other_debts"}
    DUE_DILIGENCE_INT_FIELDS = {"building_age"}
    DUE_DILIGENCE_BOOL_FIELDS = {"resident_contacted", "manager_contacted"}
    ATTACHMENT_TEXT_FIELDS = {"category", "original_filename", "stored_filename", "storage_path", "mime_type"}
    ATTACHMENT_INT_FIELDS = {"size_bytes"}
    ATTACHMENT_JSON_FIELDS = {"metadata_json"}
    SOURCE_TEXT_FIELDS = {"name", "domain", "base_url", "link_pattern", "listing_selector"}
    SOURCE_BOOL_FIELDS = {"active"}
    SOURCE_JSON_FIELDS = {"metadata_json"}

    @staticmethod
    def _require_company(company_id: int) -> Company:
        company = Company.query.filter_by(id=company_id).first()
        if company is None:
            raise RealEstateAuctionError(f"Empresa não encontrada: company_id={company_id}.")
        return company

    @staticmethod
    def _settings_query(company_id: int):
        return RealEstateAuctionTenantSettings.query.filter_by(company_id=company_id)

    @staticmethod
    def get_tenant_settings(company_id: int) -> dict[str, Any]:
        RealEstateAuctionService._require_company(company_id)
        settings = RealEstateAuctionService._settings_query(company_id).first()
        if settings is not None:
            return settings.to_dict()
        return {
            "id": None,
            "company_id": company_id,
            "module_enabled": False,
            "display_name": RealEstateAuctionService.DEFAULT_DISPLAY_NAME,
            "code_prefix": None,
            "settings_json": {},
            "created_at": None,
            "updated_at": None,
        }

    @staticmethod
    def upsert_tenant_settings(
        company_id: int,
        payload: dict[str, Any],
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RealEstateAuctionError("Payload de configuração deve ser um objeto.")
        RealEstateAuctionService._require_company(company_id)
        settings = RealEstateAuctionService._settings_query(company_id).first()
        if settings is None:
            settings = RealEstateAuctionTenantSettings(company_id=company_id)
            db.session.add(settings)

        if "module_enabled" in payload:
            settings.module_enabled = _safe_bool(payload.get("module_enabled"))
        if "display_name" in payload:
            settings.display_name = _clean_text(payload.get("display_name")) or RealEstateAuctionService.DEFAULT_DISPLAY_NAME
        if "code_prefix" in payload:
            settings.code_prefix = _clean_text(payload.get("code_prefix"))
        if "settings_json" in payload:
            settings.settings_json = RealEstateAuctionService._require_dict(payload.get("settings_json"), "settings_json")

        if commit:
            db.session.commit()
        return settings.to_dict()

    @staticmethod
    def ensure_module_enabled(company_id: int) -> dict[str, Any]:
        settings = RealEstateAuctionService.get_tenant_settings(company_id)
        if not settings.get("module_enabled"):
            raise RealEstateAuctionError(
                "Módulo Leilões Imobiliários não está habilitado para esta empresa. "
                "Habilite em real_estate_auction_tenant_settings antes de operar."
            )
        return settings

    @staticmethod
    def get_workspace(company_id: int, *, include_disabled: bool = True) -> dict[str, Any]:
        settings = RealEstateAuctionService.get_tenant_settings(company_id)
        if not include_disabled and not settings.get("module_enabled"):
            raise RealEstateAuctionError("Módulo Leilões Imobiliários não habilitado para esta empresa.")

        query = RealEstateAuctionProperty.query.filter_by(company_id=company_id, deleted_at=None)
        total = query.count()
        status_counts = dict(
            query.with_entities(RealEstateAuctionProperty.status, func.count(RealEstateAuctionProperty.id))
            .group_by(RealEstateAuctionProperty.status)
            .all()
        )
        triage_counts = dict(
            query.with_entities(RealEstateAuctionProperty.triage_status, func.count(RealEstateAuctionProperty.id))
            .group_by(RealEstateAuctionProperty.triage_status)
            .all()
        )
        recent = query.order_by(RealEstateAuctionProperty.updated_at.desc()).limit(10).all()
        sources = (
            RealEstateAuctionSource.query.filter_by(company_id=company_id)
            .order_by(RealEstateAuctionSource.name.asc())
            .all()
        )
        return {
            "company_id": company_id,
            "module_key": RealEstateAuctionService.MODULE_KEY,
            "settings": settings,
            "summary": {
                "properties_total": total,
                "status_counts": status_counts,
                "triage_counts": triage_counts,
                "sources_total": len(sources),
                "active_sources_total": len([source for source in sources if source.active]),
            },
            "recent_properties": [item.to_dict() for item in recent],
            "sources": [source.to_dict() for source in sources],
        }

    @staticmethod
    def list_properties(
        company_id: int,
        *,
        status: str | None = None,
        triage_status: str | None = None,
        city: str | None = None,
        state: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        query = RealEstateAuctionProperty.query.filter_by(company_id=company_id, deleted_at=None)

        if status:
            RealEstateAuctionService._validate_choice(status, REAL_ESTATE_AUCTION_STATUS_VALUES, "status")
            query = query.filter(RealEstateAuctionProperty.status == status)
        if triage_status:
            RealEstateAuctionService._validate_choice(
                triage_status,
                REAL_ESTATE_AUCTION_TRIAGE_STATUS_VALUES,
                "triage_status",
            )
            query = query.filter(RealEstateAuctionProperty.triage_status == triage_status)
        if city:
            query = query.filter(RealEstateAuctionProperty.city.ilike(f"%{_clean_text(city)}%"))
        if state:
            query = query.filter(RealEstateAuctionProperty.state == str(state).strip().upper()[:2])

        safe_limit = max(1, min(int(limit or 100), 200))
        rows = query.order_by(RealEstateAuctionProperty.updated_at.desc()).limit(safe_limit).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def get_property_detail(company_id: int, property_id: int) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        row = RealEstateAuctionService._require_property(company_id, property_id)
        events = (
            RealEstateAuctionEvent.query.filter_by(company_id=company_id, property_id=property_id)
            .order_by(RealEstateAuctionEvent.auction_datetime.asc(), RealEstateAuctionEvent.id.asc())
            .all()
        )
        sheet = RealEstateAuctionFinancialSheet.query.filter_by(company_id=company_id, property_id=property_id).first()
        due_diligence = RealEstateAuctionDueDiligence.query.filter_by(company_id=company_id, property_id=property_id).first()
        attachments = (
            RealEstateAuctionAttachment.query.filter_by(company_id=company_id, property_id=property_id)
            .order_by(RealEstateAuctionAttachment.created_at.desc())
            .all()
        )
        return {
            "property": row.to_dict(),
            "events": [event.to_dict() for event in events],
            "financial_sheet": sheet.to_dict() if sheet else None,
            "due_diligence": due_diligence.to_dict() if due_diligence else None,
            "attachments": [attachment.to_dict() for attachment in attachments],
        }

    @staticmethod
    def list_sources(company_id: int) -> list[dict[str, Any]]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        rows = RealEstateAuctionSource.query.filter_by(company_id=company_id).order_by(RealEstateAuctionSource.name.asc()).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def create_property(
        company_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        data = RealEstateAuctionService._normalize_property_payload(payload, partial=False)
        if RealEstateAuctionService._property_by_code(company_id, data["code"]) is not None:
            raise RealEstateAuctionError(f"Já existe imóvel com code='{data['code']}' neste tenant.")

        row = RealEstateAuctionProperty(company_id=company_id, created_by_user_id=user_id, updated_by_user_id=user_id)
        RealEstateAuctionService._apply_property_payload(row, data)
        db.session.add(row)
        if commit:
            db.session.commit()
        return row.to_dict()

    @staticmethod
    def update_property(
        company_id: int,
        property_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        row = RealEstateAuctionService._require_property(company_id, property_id)
        data = RealEstateAuctionService._normalize_property_payload(payload, partial=True)
        if "code" in data:
            existing = RealEstateAuctionService._property_by_code(company_id, data["code"])
            if existing is not None and int(existing.id) != int(property_id):
                raise RealEstateAuctionError(f"Já existe imóvel com code='{data['code']}' neste tenant.")
        RealEstateAuctionService._apply_property_payload(row, data)
        row.updated_by_user_id = user_id
        if commit:
            db.session.commit()
        return row.to_dict()

    @staticmethod
    def archive_property(
        company_id: int,
        property_id: int,
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        row = RealEstateAuctionService._require_property(company_id, property_id)
        row.deleted_at = datetime.utcnow()
        row.updated_by_user_id = user_id
        if commit:
            db.session.commit()
        return {"archived": True, "property": row.to_dict()}

    @staticmethod
    def create_event(
        company_id: int,
        property_id: int,
        payload: dict[str, Any],
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        RealEstateAuctionService._require_property(company_id, property_id)
        data = RealEstateAuctionService._normalize_event_payload(payload, partial=False)
        row = RealEstateAuctionEvent(company_id=company_id, property_id=property_id)
        RealEstateAuctionService._apply_payload(row, data)
        db.session.add(row)
        if commit:
            db.session.commit()
        return row.to_dict()

    @staticmethod
    def update_event(
        company_id: int,
        property_id: int,
        event_id: int,
        payload: dict[str, Any],
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        row = RealEstateAuctionService._require_event(company_id, property_id, event_id)
        data = RealEstateAuctionService._normalize_event_payload(payload, partial=True)
        RealEstateAuctionService._apply_payload(row, data)
        if commit:
            db.session.commit()
        return row.to_dict()

    @staticmethod
    def delete_event(
        company_id: int,
        property_id: int,
        event_id: int,
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        row = RealEstateAuctionService._require_event(company_id, property_id, event_id)
        db.session.delete(row)
        if commit:
            db.session.commit()
        return {"deleted": True, "event_id": event_id}

    @staticmethod
    def upsert_financial_sheet(
        company_id: int,
        property_id: int,
        payload: dict[str, Any],
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        RealEstateAuctionService._require_property(company_id, property_id)
        data = RealEstateAuctionService._normalize_financial_sheet_payload(payload)
        row = RealEstateAuctionFinancialSheet.query.filter_by(company_id=company_id, property_id=property_id).first()
        if row is None:
            row = RealEstateAuctionFinancialSheet(company_id=company_id, property_id=property_id)
            db.session.add(row)
        RealEstateAuctionService._apply_payload(row, data)
        if commit:
            db.session.commit()
        return row.to_dict()

    @staticmethod
    def upsert_due_diligence(
        company_id: int,
        property_id: int,
        payload: dict[str, Any],
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        RealEstateAuctionService._require_property(company_id, property_id)
        data = RealEstateAuctionService._normalize_due_diligence_payload(payload)
        row = RealEstateAuctionDueDiligence.query.filter_by(company_id=company_id, property_id=property_id).first()
        if row is None:
            row = RealEstateAuctionDueDiligence(company_id=company_id, property_id=property_id)
            db.session.add(row)
        RealEstateAuctionService._apply_payload(row, data)
        if commit:
            db.session.commit()
        return row.to_dict()

    @staticmethod
    def create_attachment(
        company_id: int,
        property_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        RealEstateAuctionService._require_property(company_id, property_id)
        data = RealEstateAuctionService._normalize_attachment_payload(payload, partial=False)
        row = RealEstateAuctionAttachment(company_id=company_id, property_id=property_id, created_by_user_id=user_id)
        RealEstateAuctionService._apply_payload(row, data)
        db.session.add(row)
        if commit:
            db.session.commit()
        return row.to_dict()

    @staticmethod
    def delete_attachment(
        company_id: int,
        property_id: int,
        attachment_id: int,
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        row = RealEstateAuctionService._require_attachment(company_id, property_id, attachment_id)
        db.session.delete(row)
        if commit:
            db.session.commit()
        return {"deleted": True, "attachment_id": attachment_id}

    @staticmethod
    def create_source(
        company_id: int,
        payload: dict[str, Any],
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        data = RealEstateAuctionService._normalize_source_payload(payload, partial=False)
        if RealEstateAuctionSource.query.filter_by(company_id=company_id, base_url=data["base_url"]).first() is not None:
            raise RealEstateAuctionError(f"Já existe fonte com base_url='{data['base_url']}' neste tenant.")
        row = RealEstateAuctionSource(company_id=company_id)
        RealEstateAuctionService._apply_payload(row, data)
        db.session.add(row)
        if commit:
            db.session.commit()
        return row.to_dict()

    @staticmethod
    def update_source(
        company_id: int,
        source_id: int,
        payload: dict[str, Any],
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        row = RealEstateAuctionService._require_source(company_id, source_id)
        data = RealEstateAuctionService._normalize_source_payload(payload, partial=True)
        if "base_url" in data:
            existing = RealEstateAuctionSource.query.filter_by(company_id=company_id, base_url=data["base_url"]).first()
            if existing is not None and int(existing.id) != int(source_id):
                raise RealEstateAuctionError(f"Já existe fonte com base_url='{data['base_url']}' neste tenant.")
        RealEstateAuctionService._apply_payload(row, data)
        if commit:
            db.session.commit()
        return row.to_dict()

    @staticmethod
    def delete_source(
        company_id: int,
        source_id: int,
        *,
        commit: bool = True,
    ) -> dict[str, Any]:
        RealEstateAuctionService.ensure_module_enabled(company_id)
        row = RealEstateAuctionService._require_source(company_id, source_id)
        db.session.delete(row)
        if commit:
            db.session.commit()
        return {"deleted": True, "source_id": source_id}

    @staticmethod
    def _require_property(company_id: int, property_id: int) -> RealEstateAuctionProperty:
        row = RealEstateAuctionProperty.query.filter_by(
            company_id=company_id,
            id=property_id,
            deleted_at=None,
        ).first()
        if row is None:
            raise RealEstateAuctionError(
                f"Imóvel não encontrado no tenant: company_id={company_id}, property_id={property_id}."
            )
        return row

    @staticmethod
    def _property_by_code(company_id: int, code: str) -> RealEstateAuctionProperty | None:
        return RealEstateAuctionProperty.query.filter_by(company_id=company_id, code=code).first()

    @staticmethod
    def _require_event(company_id: int, property_id: int, event_id: int) -> RealEstateAuctionEvent:
        row = RealEstateAuctionEvent.query.filter_by(company_id=company_id, property_id=property_id, id=event_id).first()
        if row is None:
            raise RealEstateAuctionError(
                f"Evento não encontrado no tenant: company_id={company_id}, property_id={property_id}, event_id={event_id}."
            )
        return row

    @staticmethod
    def _require_attachment(company_id: int, property_id: int, attachment_id: int) -> RealEstateAuctionAttachment:
        row = RealEstateAuctionAttachment.query.filter_by(company_id=company_id, property_id=property_id, id=attachment_id).first()
        if row is None:
            raise RealEstateAuctionError(
                "Anexo não encontrado no tenant: "
                f"company_id={company_id}, property_id={property_id}, attachment_id={attachment_id}."
            )
        return row

    @staticmethod
    def _require_source(company_id: int, source_id: int) -> RealEstateAuctionSource:
        row = RealEstateAuctionSource.query.filter_by(company_id=company_id, id=source_id).first()
        if row is None:
            raise RealEstateAuctionError(f"Fonte não encontrada no tenant: company_id={company_id}, source_id={source_id}.")
        return row

    @staticmethod
    def _normalize_property_payload(payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RealEstateAuctionError("Payload de imóvel deve ser um objeto.")
        data: dict[str, Any] = {}

        for field in RealEstateAuctionService.PROPERTY_TEXT_FIELDS:
            if field in payload:
                value = _clean_text(payload.get(field))
                if field == "state" and value:
                    value = value.upper()[:2]
                data[field] = value
        for field in RealEstateAuctionService.PROPERTY_DECIMAL_FIELDS:
            if field in payload:
                data[field] = _safe_decimal(payload.get(field), field=field)
        for field in RealEstateAuctionService.PROPERTY_BOOL_FIELDS:
            if field in payload:
                data[field] = _safe_bool(payload.get(field))
        for field in RealEstateAuctionService.PROPERTY_DATETIME_FIELDS:
            if field in payload:
                data[field] = RealEstateAuctionService._parse_datetime(payload.get(field), field=field)
        for field in RealEstateAuctionService.PROPERTY_JSON_FIELDS:
            if field in payload:
                data[field] = RealEstateAuctionService._require_dict(payload.get(field), field)

        if "status" in payload:
            data["status"] = RealEstateAuctionService._validate_choice(
                _clean_text(payload.get("status")),
                REAL_ESTATE_AUCTION_STATUS_VALUES,
                "status",
            )
        if "triage_status" in payload:
            data["triage_status"] = RealEstateAuctionService._validate_choice(
                _clean_text(payload.get("triage_status")),
                REAL_ESTATE_AUCTION_TRIAGE_STATUS_VALUES,
                "triage_status",
            )

        if not partial:
            required = ("code", "address")
            missing = [field for field in required if not data.get(field)]
            if missing:
                raise RealEstateAuctionError("Campos obrigatórios ausentes: " + ", ".join(missing))
            data.setdefault("status", "in_analysis")
            data.setdefault("triage_status", "pending")
            data.setdefault("occupied", True)
        return data

    @staticmethod
    def _apply_property_payload(row: RealEstateAuctionProperty, payload: dict[str, Any]) -> None:
        for field, value in payload.items():
            setattr(row, field, value)

    @staticmethod
    def _apply_payload(row: Any, payload: dict[str, Any]) -> None:
        for field, value in payload.items():
            setattr(row, field, value)

    @staticmethod
    def _normalize_event_payload(payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RealEstateAuctionError("Payload de evento deve ser um objeto.")
        data: dict[str, Any] = {}
        for field in RealEstateAuctionService.EVENT_TEXT_FIELDS:
            if field in payload:
                data[field] = _clean_text(payload.get(field))
        for field in RealEstateAuctionService.EVENT_DECIMAL_FIELDS:
            if field in payload:
                data[field] = _safe_decimal(payload.get(field), field=field)
        for field in RealEstateAuctionService.EVENT_DATETIME_FIELDS:
            if field in payload:
                data[field] = RealEstateAuctionService._parse_datetime(payload.get(field), field=field)
        if not partial:
            if not data.get("result"):
                data["result"] = "pending"
        return data

    @staticmethod
    def _normalize_financial_sheet_payload(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RealEstateAuctionError("Payload de ficha financeira deve ser um objeto.")
        data: dict[str, Any] = {}
        for field in RealEstateAuctionService.FINANCIAL_DECIMAL_FIELDS:
            if field in payload:
                data[field] = _safe_decimal(payload.get(field), field=field) or Decimal("0")
        for field in RealEstateAuctionService.FINANCIAL_INT_FIELDS:
            if field in payload:
                data[field] = _safe_int(payload.get(field), field=field) or 0
        for field in RealEstateAuctionService.FINANCIAL_JSON_FIELDS:
            if field in payload:
                data[field] = RealEstateAuctionService._require_dict(payload.get(field), field)
        return data

    @staticmethod
    def _normalize_due_diligence_payload(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RealEstateAuctionError("Payload de diligência deve ser um objeto.")
        data: dict[str, Any] = {}
        for field in RealEstateAuctionService.DUE_DILIGENCE_TEXT_FIELDS:
            if field in payload:
                data[field] = _clean_text(payload.get(field))
        for field in RealEstateAuctionService.DUE_DILIGENCE_DECIMAL_FIELDS:
            if field in payload:
                data[field] = _safe_decimal(payload.get(field), field=field) or Decimal("0")
        for field in RealEstateAuctionService.DUE_DILIGENCE_INT_FIELDS:
            if field in payload:
                data[field] = _safe_int(payload.get(field), field=field)
        for field in RealEstateAuctionService.DUE_DILIGENCE_BOOL_FIELDS:
            if field in payload:
                data[field] = _safe_bool(payload.get(field))
        return data

    @staticmethod
    def _normalize_attachment_payload(payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RealEstateAuctionError("Payload de anexo deve ser um objeto.")
        data: dict[str, Any] = {}
        for field in RealEstateAuctionService.ATTACHMENT_TEXT_FIELDS:
            if field in payload:
                data[field] = _clean_text(payload.get(field))
        for field in RealEstateAuctionService.ATTACHMENT_INT_FIELDS:
            if field in payload:
                data[field] = _safe_int(payload.get(field), field=field) or 0
        for field in RealEstateAuctionService.ATTACHMENT_JSON_FIELDS:
            if field in payload:
                data[field] = RealEstateAuctionService._require_dict(payload.get(field), field)
        if "category" in data and data["category"] not in REAL_ESTATE_AUCTION_ATTACHMENT_CATEGORY_VALUES:
            raise RealEstateAuctionError(
                "Campo 'category' inválido. Valores permitidos: "
                + ", ".join(REAL_ESTATE_AUCTION_ATTACHMENT_CATEGORY_VALUES)
                + "."
            )
        if not partial:
            required = ("category", "storage_path")
            missing = [field for field in required if not data.get(field)]
            if missing:
                raise RealEstateAuctionError("Campos obrigatórios ausentes em anexo: " + ", ".join(missing))
        return data

    @staticmethod
    def _normalize_source_payload(payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RealEstateAuctionError("Payload de fonte deve ser um objeto.")
        data: dict[str, Any] = {}
        for field in RealEstateAuctionService.SOURCE_TEXT_FIELDS:
            if field in payload:
                data[field] = _clean_text(payload.get(field))
        for field in RealEstateAuctionService.SOURCE_BOOL_FIELDS:
            if field in payload:
                data[field] = _safe_bool(payload.get(field))
        for field in RealEstateAuctionService.SOURCE_JSON_FIELDS:
            if field in payload:
                data[field] = RealEstateAuctionService._require_dict(payload.get(field), field)
        if not partial:
            required = ("name", "domain", "base_url")
            missing = [field for field in required if not data.get(field)]
            if missing:
                raise RealEstateAuctionError("Campos obrigatórios ausentes em fonte: " + ", ".join(missing))
            data.setdefault("active", True)
        return data

    @staticmethod
    def _validate_choice(value: str | None, allowed: tuple[str, ...], field: str) -> str:
        if not value or value not in allowed:
            raise RealEstateAuctionError(f"Campo '{field}' inválido. Valores permitidos: {', '.join(allowed)}.")
        return value

    @staticmethod
    def _require_dict(value: Any, field: str) -> dict[str, Any]:
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise RealEstateAuctionError(f"Campo '{field}' deve ser um objeto.")
        return value

    @staticmethod
    def _parse_datetime(value: Any, *, field: str) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError as exc:
                raise RealEstateAuctionError(f"Campo '{field}' deve estar em ISO-8601.") from exc
        raise RealEstateAuctionError(f"Campo '{field}' deve estar em ISO-8601.")


__all__ = ["RealEstateAuctionError", "RealEstateAuctionService"]
