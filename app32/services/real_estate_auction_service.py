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
