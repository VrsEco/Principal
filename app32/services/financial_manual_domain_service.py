from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialManualDomain
from schemas.financial import FinancialManualDomainInput, FinancialManualDomainUpdateInput


class FinancialManualDomainService:
    @staticmethod
    def _validate_scope(company_id: int, allowed_company_ids: Optional[Sequence[int]]) -> Optional[str]:
        from services.financial_service import FinancialService

        return FinancialService._ensure_company_scope(company_id, allowed_company_ids)

    @staticmethod
    def _serialize_item(item: FinancialManualDomain) -> Dict:
        return {
            "id": item.id,
            "domain_type": item.domain_type,
            "source_kind": "manual",
            "source_id": item.id,
            "source_code": item.code,
            "source_name": item.name,
            "source_status": "Manual",
            "source_is_active": bool(item.is_active),
            "display_label": f"{item.code + ' - ' if item.code else ''}{item.name}",
            "is_active": bool(item.is_active),
            "is_enabled": bool(item.is_enabled),
            "is_default_suggestion": bool(item.is_default_suggestion),
            "notes": item.notes,
            "metadata_json": dict(item.metadata_json or {}),
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }

    @staticmethod
    def _clear_default_suggestions(*, company_id: int, exclude_item_id: Optional[int] = None) -> None:
        query = FinancialManualDomain.query.filter(
            FinancialManualDomain.company_id == company_id,
            FinancialManualDomain.deleted_at.is_(None),
            FinancialManualDomain.is_default_suggestion.is_(True),
        )
        if exclude_item_id:
            query = query.filter(FinancialManualDomain.id != exclude_item_id)
        for item in query.all():
            item.is_default_suggestion = False

    @staticmethod
    def load_item(
        *,
        company_id: int,
        item_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[FinancialManualDomain], Optional[str]]:
        scope_error = FinancialManualDomainService._validate_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        item = FinancialManualDomain.query.filter(
            FinancialManualDomain.company_id == company_id,
            FinancialManualDomain.id == item_id,
            FinancialManualDomain.deleted_at.is_(None),
        ).first()
        if not item:
            return None, "Cadastro manual financeiro não encontrado para a empresa informada."
        return item, None

    @staticmethod
    def list_items(
        *,
        company_id: int,
        domain_type: Optional[str] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialManualDomainService._validate_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialManualDomain.query.filter(
            FinancialManualDomain.company_id == company_id,
            FinancialManualDomain.deleted_at.is_(None),
        )
        if domain_type:
            query = query.filter(FinancialManualDomain.domain_type == domain_type)

        items = (
            query.order_by(
                FinancialManualDomain.domain_type.asc(),
                FinancialManualDomain.code.asc().nullslast(),
                FinancialManualDomain.name.asc(),
                FinancialManualDomain.id.asc(),
            ).all()
        )
        serialized = [FinancialManualDomainService._serialize_item(item) for item in items]
        if domain_type:
            return {"items": serialized, "domain_type": domain_type}, None

        grouped: Dict[str, list] = {}
        for item in serialized:
            grouped.setdefault(item["domain_type"], []).append(item)
        return {"items_by_type": grouped}, None

    @staticmethod
    def create_item(
        *,
        company_id: int,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialManualDomainService._validate_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        normalized_payload = dict(payload or {})
        normalized_payload["company_id"] = company_id
        validated = FinancialManualDomainInput.model_validate(normalized_payload)
        data = validated.model_dump()

        item = FinancialManualDomain(
            company_id=company_id,
            domain_type=data["domain_type"],
            code=data.get("code"),
            name=data["name"],
            is_active=bool(data.get("is_active", True)),
            is_enabled=bool(data.get("is_enabled", True)),
            is_default_suggestion=bool(data.get("is_default_suggestion")) and bool(data.get("is_enabled", True)),
            notes=data.get("notes"),
            metadata_json=data.get("metadata_json") or {},
        )
        db.session.add(item)
        db.session.flush()
        if item.is_default_suggestion:
            FinancialManualDomainService._clear_default_suggestions(company_id=company_id, exclude_item_id=item.id)
        db.session.commit()
        db.session.refresh(item)
        return FinancialManualDomainService._serialize_item(item), None

    @staticmethod
    def update_item(
        *,
        company_id: int,
        item_id: int,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        item, error = FinancialManualDomainService.load_item(
            company_id=company_id,
            item_id=item_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        validated = FinancialManualDomainUpdateInput.model_validate(payload or {})
        data = validated.model_dump(exclude_unset=True)

        if "domain_type" in data:
            item.domain_type = data["domain_type"]
        if "code" in data:
            item.code = data["code"]
        if "name" in data:
            item.name = data["name"]
        if "is_active" in data:
            item.is_active = bool(data["is_active"])
            if not item.is_active:
                item.is_enabled = False
                item.is_default_suggestion = False
        if "is_enabled" in data:
            item.is_enabled = bool(data["is_enabled"])
            if not item.is_enabled:
                item.is_default_suggestion = False
        if "is_default_suggestion" in data:
            item.is_default_suggestion = (
                bool(data["is_default_suggestion"])
                and bool(item.is_enabled)
                and bool(item.is_active)
            )
        if "notes" in data:
            item.notes = data["notes"]
        if "metadata_json" in data:
            item.metadata_json = data["metadata_json"] or {}

        db.session.flush()
        if item.is_default_suggestion:
            FinancialManualDomainService._clear_default_suggestions(company_id=company_id, exclude_item_id=item.id)
        db.session.commit()
        db.session.refresh(item)
        return FinancialManualDomainService._serialize_item(item), None

    @staticmethod
    def delete_item(
        *,
        company_id: int,
        item_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        item, error = FinancialManualDomainService.load_item(
            company_id=company_id,
            item_id=item_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        item.deleted_at = db.func.now()
        item.is_enabled = False
        item.is_default_suggestion = False
        db.session.commit()
        return {"ok": True, "id": item_id}, None

    @staticmethod
    def list_enabled_items(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[list[Dict]], Optional[str]]:
        scope_error = FinancialManualDomainService._validate_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        items = (
            FinancialManualDomain.query.filter(
                FinancialManualDomain.company_id == company_id,
                FinancialManualDomain.deleted_at.is_(None),
                FinancialManualDomain.is_active.is_(True),
                FinancialManualDomain.is_enabled.is_(True),
            )
            .order_by(
                FinancialManualDomain.domain_type.asc(),
                FinancialManualDomain.code.asc().nullslast(),
                FinancialManualDomain.name.asc(),
                FinancialManualDomain.id.asc(),
            )
            .all()
        )
        return [FinancialManualDomainService._serialize_item(item) for item in items], None

    @staticmethod
    def get_default_suggestion(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialManualDomainService._validate_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        item = (
            FinancialManualDomain.query.filter(
                FinancialManualDomain.company_id == company_id,
                FinancialManualDomain.deleted_at.is_(None),
                FinancialManualDomain.is_active.is_(True),
                FinancialManualDomain.is_enabled.is_(True),
                FinancialManualDomain.is_default_suggestion.is_(True),
            )
            .order_by(FinancialManualDomain.updated_at.desc(), FinancialManualDomain.id.desc())
            .first()
        )
        if not item:
            return None, None
        return FinancialManualDomainService._serialize_item(item), None
