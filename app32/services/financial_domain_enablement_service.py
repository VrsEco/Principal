from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple, Type

from models import db
from models.financial import FinancialDomainEnablement
from models.process import Process
from models.project import Project
from models.portfolio import Portfolio
from schemas.financial import FinancialDomainEnablementInput, FinancialDomainEnablementUpdateInput


class FinancialDomainEnablementService:
    DOMAIN_MODELS: Dict[str, Type] = {
        "project": Project,
        "process": Process,
    }

    @staticmethod
    def _validate_scope(company_id: int, allowed_company_ids: Optional[Sequence[int]]) -> Optional[str]:
        from services.financial_service import FinancialService

        return FinancialService._ensure_company_scope(company_id, allowed_company_ids)

    @staticmethod
    def _get_model(domain_type: str):
        return FinancialDomainEnablementService.DOMAIN_MODELS.get(str(domain_type or "").strip().lower())

    @staticmethod
    def _load_source(company_id: int, domain_type: str, source_id: int):
        model = FinancialDomainEnablementService._get_model(domain_type)
        if not model:
            return None, "Tipo de vínculo financeiro inválido."

        source = model.query.filter(
            model.id == source_id,
            model.company_id == company_id,
        ).first()
        if not source:
            return None, "Projeto/Processo não encontrado para a empresa informada."
        return source, None

    @staticmethod
    def _serialize_source(enablement: Optional[FinancialDomainEnablement], domain_type: str, source) -> Dict:
        code = getattr(source, "code", None)
        name = getattr(source, "name", None) or getattr(source, "title", None)
        status = getattr(source, "status", None) or getattr(source, "kanban_stage", None)
        is_source_active = getattr(source, "is_active", True)
        metadata_json: Dict = dict(enablement.metadata_json or {}) if enablement else {}

        if domain_type == "project":
            portfolio = None
            portfolio_id = getattr(source, "portfolio_id", None)
            if portfolio_id:
                portfolio = Portfolio.query.filter(
                    Portfolio.id == portfolio_id,
                    Portfolio.company_id == getattr(source, "company_id", None),
                ).first()
            metadata_json.update(
                {
                    "portfolio_id": portfolio.id if portfolio else None,
                    "portfolio_code": getattr(portfolio, "code", None) if portfolio else None,
                    "portfolio_name": getattr(portfolio, "name", None) if portfolio else None,
                }
            )

        if domain_type == "process":
            macro = getattr(source, "macro", None)
            area = getattr(macro, "area", None) if macro else None
            metadata_json.update(
                {
                    "macro_id": getattr(macro, "id", None) if macro else None,
                    "macro_code": getattr(macro, "code", None) if macro else None,
                    "macro_name": getattr(macro, "name", None) if macro else None,
                    "area_id": getattr(area, "id", None) if area else None,
                    "area_code": getattr(area, "code", None) if area else None,
                    "area_name": getattr(area, "name", None) if area else None,
                }
            )

        return {
            "id": enablement.id if enablement else None,
            "domain_type": domain_type,
            "source_id": source.id,
            "source_code": code,
            "source_name": name,
            "source_status": status,
            "source_is_active": bool(is_source_active if is_source_active is not None else True),
            "display_label": f"{code + ' - ' if code else ''}{name}",
            "is_enabled": bool(enablement.is_enabled) if enablement else False,
            "is_default_suggestion": bool(enablement.is_default_suggestion) if enablement else False,
            "notes": enablement.notes if enablement else None,
            "metadata_json": metadata_json,
            "updated_at": enablement.updated_at.isoformat() if enablement and enablement.updated_at else None,
        }

    @staticmethod
    def _clear_default_suggestions(*, company_id: int, exclude_item_id: Optional[int] = None) -> None:
        query = FinancialDomainEnablement.query.filter(
            FinancialDomainEnablement.company_id == company_id,
            FinancialDomainEnablement.deleted_at.is_(None),
            FinancialDomainEnablement.is_default_suggestion.is_(True),
        )
        if exclude_item_id:
            query = query.filter(FinancialDomainEnablement.id != exclude_item_id)
        for item in query.all():
            item.is_default_suggestion = False

    @staticmethod
    def list_items(
        *,
        company_id: int,
        domain_type: Optional[str] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialDomainEnablementService._validate_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        domain_keys = [domain_type] if domain_type else list(FinancialDomainEnablementService.DOMAIN_MODELS.keys())
        result: Dict[str, list] = {}

        for current_domain in domain_keys:
            model = FinancialDomainEnablementService._get_model(current_domain)
            if not model:
                return None, "Tipo de vínculo financeiro inválido."

            sources = (
                model.query.filter(model.company_id == company_id)
                .order_by(model.id.asc())
                .all()
            )
            source_ids = [item.id for item in sources]
            enablements = (
                FinancialDomainEnablement.query.filter(
                    FinancialDomainEnablement.company_id == company_id,
                    FinancialDomainEnablement.domain_type == current_domain,
                    FinancialDomainEnablement.deleted_at.is_(None),
                    FinancialDomainEnablement.source_id.in_(source_ids) if source_ids else db.text("1=0"),
                ).all()
            ) if source_ids else []
            enablements_by_source = {item.source_id: item for item in enablements}
            result[current_domain] = [
                FinancialDomainEnablementService._serialize_source(
                    enablements_by_source.get(source.id),
                    current_domain,
                    source,
                )
                for source in sources
            ]

        if domain_type:
            return {"items": result.get(domain_type, []), "domain_type": domain_type}, None
        return {"items_by_type": result}, None

    @staticmethod
    def upsert_item(
        *,
        company_id: int,
        domain_type: str,
        source_id: int,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialDomainEnablementService._validate_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        source, source_error = FinancialDomainEnablementService._load_source(company_id, domain_type, source_id)
        if source_error:
            return None, source_error

        normalized_payload = dict(payload or {})
        normalized_payload["company_id"] = company_id
        normalized_payload["domain_type"] = domain_type
        normalized_payload["source_id"] = source_id

        validated = FinancialDomainEnablementInput.model_validate(normalized_payload)
        data = validated.model_dump()

        item = FinancialDomainEnablement.query.filter(
            FinancialDomainEnablement.company_id == company_id,
            FinancialDomainEnablement.domain_type == domain_type,
            FinancialDomainEnablement.source_id == source_id,
        ).first()

        if not item:
            item = FinancialDomainEnablement(
                company_id=company_id,
                domain_type=domain_type,
                source_id=source_id,
            )
            db.session.add(item)

        item.is_enabled = data["is_enabled"]
        item.is_default_suggestion = bool(data.get("is_default_suggestion")) and bool(data["is_enabled"])
        item.notes = data.get("notes")
        item.metadata_json = data.get("metadata_json") or {}
        item.deleted_at = None
        if item.is_default_suggestion:
            db.session.flush()
            FinancialDomainEnablementService._clear_default_suggestions(
                company_id=company_id,
                exclude_item_id=item.id,
            )

        db.session.commit()
        db.session.refresh(item)
        return FinancialDomainEnablementService._serialize_source(item, domain_type, source), None

    @staticmethod
    def toggle_item(
        *,
        company_id: int,
        domain_type: str,
        source_id: int,
        is_enabled: bool,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        return FinancialDomainEnablementService.upsert_item(
            company_id=company_id,
            domain_type=domain_type,
            source_id=source_id,
            payload={"is_enabled": bool(is_enabled)},
            allowed_company_ids=allowed_company_ids,
        )

    @staticmethod
    def update_item(
        *,
        company_id: int,
        domain_type: str,
        source_id: int,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialDomainEnablementService._validate_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        source, source_error = FinancialDomainEnablementService._load_source(company_id, domain_type, source_id)
        if source_error:
            return None, source_error

        item = FinancialDomainEnablement.query.filter(
            FinancialDomainEnablement.company_id == company_id,
            FinancialDomainEnablement.domain_type == domain_type,
            FinancialDomainEnablement.source_id == source_id,
            FinancialDomainEnablement.deleted_at.is_(None),
        ).first()

        if not item:
            return None, "Projeto/Processo ainda não foi habilitado no Financeiro."

        validated = FinancialDomainEnablementUpdateInput.model_validate(payload or {})
        data = validated.model_dump(exclude_unset=True)

        if "is_enabled" in data:
            item.is_enabled = bool(data["is_enabled"])
            if not item.is_enabled:
                item.is_default_suggestion = False
        if "is_default_suggestion" in data:
            item.is_default_suggestion = bool(data["is_default_suggestion"]) and bool(item.is_enabled)
        if "notes" in data:
            item.notes = data.get("notes")
        if "metadata_json" in data and data["metadata_json"] is not None:
            item.metadata_json = data["metadata_json"]
        if item.is_default_suggestion:
            FinancialDomainEnablementService._clear_default_suggestions(
                company_id=company_id,
                exclude_item_id=item.id,
            )

        db.session.commit()
        db.session.refresh(item)
        return FinancialDomainEnablementService._serialize_source(item, domain_type, source), None
