from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Iterable

from models import (
    Company,
    Indicator,
    IndicatorLineOfSight,
    OKRArea,
    OKRGlobal,
    OrganizationalIdentity,
    Process,
    ProcessStrategicAlignmentLink,
    ProcessStrategyProfile,
    StrategyMaturationItem,
    db,
)
from models.strategy_alignment import (
    INDICATOR_LINE_OF_SIGHT_RELATIONSHIP_TYPES,
    PROCESS_MATURITY_LEVEL_VALUES,
    PROCESS_STRATEGIC_CRITICALITY_VALUES,
    STRATEGY_ALIGNMENT_LINK_TYPES,
    STRATEGY_ALIGNMENT_TARGET_REF_TYPES,
    STRATEGY_MATURATION_BLOCK_TYPES,
    STRATEGY_MATURATION_REVIEW_DECISIONS,
    STRATEGY_MATURATION_SOURCE_VALUES,
    STRATEGY_MATURATION_STATE_VALUES,
    STRATEGY_MATURATION_STATUS_VALUES,
)


class StrategyAlignmentN1Error(ValueError):
    """Erro de domínio para readiness/análise N1 de alinhamento estratégico."""


def _slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_list(value: Any, *, field: str) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    raise StrategyAlignmentN1Error(f"Campo '{field}' deve ser uma lista estruturada.")


def _safe_dict(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise StrategyAlignmentN1Error(f"Campo '{field}' deve ser um objeto estruturado.")


def _json_text(value: Any) -> str | None:
    if value in (None, "", [], {}):
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _item_label(item: dict[str, Any]) -> str | None:
    for key in ("name", "nome", "title", "titulo", "objective", "objetivo", "label", "code", "codigo", "key"):
        if _clean_text(item.get(key)):
            return _clean_text(item.get(key))
    return None


def _normalize_identity_items(items: Any, *, kind: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(_safe_list(items, field=kind)):
        if isinstance(raw, str):
            item: dict[str, Any] = {"name": raw}
        elif isinstance(raw, dict):
            item = dict(raw)
        else:
            item = {"value": raw}
        label = _item_label(item) or f"{kind}-{index + 1}"
        key = _clean_text(item.get("key")) or _clean_text(item.get("id")) or _clean_text(item.get("code")) or _slug(label)
        item.setdefault("name", label)
        item["key"] = str(key)
        item["target_key"] = str(key)
        item["kind"] = kind
        normalized.append(item)
    return normalized


def _model_dict(row: Any) -> dict[str, Any]:
    if hasattr(row, "to_dict"):
        return row.to_dict()
    return dict(row or {})


class StrategyAlignmentN1Service:
    """Service tenant-safe para leitura/escrita e análise N1 de alinhamento estratégico."""

    ANALYSIS_ID = "strategic_alignment_n1"
    READ_MODEL = "strategic.alignment_n1"

    _IDENTITY_FIELD_MAP = {
        "mission": "mission",
        "vision": "vision",
        "vision_horizon_year": "vision_horizon_year",
        "purpose": "purpose",
        "values": "values_json",
        "values_json": "values_json",
        "value_propositions": "value_propositions_json",
        "value_propositions_json": "value_propositions_json",
        "differentials": "differentials_json",
        "differentials_json": "differentials_json",
        "pillars": "pillars_json",
        "pillars_json": "pillars_json",
        "strategic_objectives": "strategic_objectives_json",
        "strategic_objectives_json": "strategic_objectives_json",
        "essential_competencies": "essential_competencies_json",
        "essential_competencies_json": "essential_competencies_json",
        "segments_icp": "segments_icp_json",
        "segments_icp_json": "segments_icp_json",
        "policies": "policies_json",
        "policies_json": "policies_json",
        "stakeholders": "stakeholders_json",
        "stakeholders_json": "stakeholders_json",
        "swot": "swot_json",
        "swot_json": "swot_json",
        "corporate_indicators": "corporate_indicators_json",
        "corporate_indicators_json": "corporate_indicators_json",
    }
    _IDENTITY_LIST_ATTRS = {
        "values_json",
        "value_propositions_json",
        "differentials_json",
        "pillars_json",
        "strategic_objectives_json",
        "essential_competencies_json",
        "segments_icp_json",
        "policies_json",
        "stakeholders_json",
        "corporate_indicators_json",
    }
    _IDENTITY_LIST_FIELD_ALIASES = {
        "values_json": "values",
        "value_propositions_json": "value_propositions",
        "differentials_json": "differentials",
        "pillars_json": "pillars",
        "strategic_objectives_json": "strategic_objectives",
        "essential_competencies_json": "essential_competencies",
        "segments_icp_json": "segments_icp",
        "policies_json": "policies",
        "stakeholders_json": "stakeholders",
        "corporate_indicators_json": "corporate_indicators",
    }
    _IDENTITY_ITEM_TYPE_BY_FIELD = {
        "values": "value",
        "value_propositions": "value_proposition",
        "differentials": "differential",
        "pillars": "strategic_pillar",
        "strategic_objectives": "strategic_objective",
        "essential_competencies": "essential_competence",
        "segments_icp": "segment_icp",
        "policies": "policy",
        "stakeholders": "stakeholder",
        "corporate_indicators": "corporate_indicator",
        "swot": "swot",
    }
    _MATURATION_CONTROL_KEYS = {
        "status",
        "source",
        "confidence",
        "state",
        "title",
        "description",
        "notes",
        "item_type",
        "target_key",
        "target_ref_type",
        "target_ref_id",
    }
    _PROFILE_FIELD_MAP = {
        "objective": "objective",
        "owner": "owner",
        "owner_employee_id": "owner_employee_id",
        "customer_type": "customer_type",
        "customer_description": "customer_description",
        "customer": "customer_description",
        "strategic_criticality": "strategic_criticality",
        "criticidade_estrategica": "strategic_criticality",
        "maturity_level": "maturity_level",
        "nivel_maturidade": "maturity_level",
        "regulatory_exposure": "regulatory_exposure",
        "risco_exposicao_regulatoria": "regulatory_exposure",
        "indicators": "indicators_json",
        "indicators_json": "indicators_json",
        "sipoc": "sipoc_json",
        "sipoc_json": "sipoc_json",
        "cost_resources_volume": "cost_resources_volume_json",
        "cost_resources_volume_json": "cost_resources_volume_json",
        "applicable_policies": "applicable_policies_json",
        "applicable_policies_json": "applicable_policies_json",
        "risks": "risks_json",
        "risks_json": "risks_json",
    }
    _PROFILE_LIST_ATTRS = {"indicators_json", "applicable_policies_json", "risks_json"}
    _PROFILE_DICT_ATTRS = {"sipoc_json", "cost_resources_volume_json"}
    _MATURATION_CANONICAL_STATUS = "confirmed"
    _MATURATION_NON_CANONICAL_STATUSES = {"draft", "pending", "rejected"}

    @staticmethod
    def _ensure_access(company_id: int, accessible_company_ids: Iterable[int] | None = None) -> None:
        if accessible_company_ids is None:
            return
        if int(company_id) not in {int(item) for item in accessible_company_ids}:
            raise PermissionError("Empresa fora do escopo analítico autorizado para alinhamento estratégico N1.")

    @staticmethod
    def _require_company(company_id: int) -> Company:
        company = Company.query.filter_by(id=company_id).first()
        if company is None:
            raise StrategyAlignmentN1Error(f"Empresa não encontrada: company_id={company_id}.")
        return company

    @staticmethod
    def _require_process(company_id: int, process_id: int) -> Process:
        process = Process.query.filter_by(company_id=company_id, id=process_id).first()
        if process is None:
            raise StrategyAlignmentN1Error(
                f"Processo não encontrado no tenant informado: company_id={company_id}, process_id={process_id}."
            )
        return process

    @staticmethod
    def _require_indicator(company_id: int, indicator_id: int, *, label: str = "indicador") -> Indicator:
        indicator = Indicator.query.filter_by(company_id=company_id, id=indicator_id).first()
        if indicator is None:
            raise StrategyAlignmentN1Error(
                f"{label.capitalize()} não encontrado no tenant informado: company_id={company_id}, indicator_id={indicator_id}."
            )
        return indicator

    @staticmethod
    def _normalize_maturation_status(value: Any, *, default: str = "confirmed") -> str:
        normalized = _slug(value or default).replace("-", "_")
        if normalized in STRATEGY_MATURATION_STATUS_VALUES:
            return normalized
        return default

    @staticmethod
    def _normalize_maturation_source(value: Any) -> str:
        normalized = _slug(value or "ia_inferido").replace("-", "_")
        if normalized in STRATEGY_MATURATION_SOURCE_VALUES:
            return normalized
        return "ia_inferido"

    @staticmethod
    def _normalize_maturation_state(value: Any) -> str:
        normalized = _slug(value or "as_is").replace("-", "_")
        if normalized in STRATEGY_MATURATION_STATE_VALUES:
            return normalized
        return "as_is"

    @staticmethod
    def _should_stage_payload(payload: dict[str, Any]) -> bool:
        status = StrategyAlignmentN1Service._normalize_maturation_status(payload.get("status"), default="confirmed")
        return status in StrategyAlignmentN1Service._MATURATION_NON_CANONICAL_STATUSES

    @staticmethod
    def _identity_payload_field(key: str) -> str:
        return StrategyAlignmentN1Service._IDENTITY_LIST_FIELD_ALIASES.get(key, key)

    @staticmethod
    def _identity_target_key(field: str, payload: dict[str, Any]) -> str | None:
        return (
            _clean_text(payload.get("target_key"))
            or _clean_text(payload.get("key"))
            or _clean_text(payload.get("id"))
            or _clean_text(payload.get("code"))
            or _clean_text(payload.get("name"))
            or _clean_text(payload.get("title"))
            or _clean_text(payload.get("objective"))
            or _clean_text(payload.get("segment"))
            or field
        )

    @staticmethod
    def _identity_nested_maturation_payload(field: str, item: dict[str, Any]) -> dict[str, Any]:
        payload = dict(item)
        payload.setdefault("identity_field", field)
        payload.setdefault("item_type", StrategyAlignmentN1Service._IDENTITY_ITEM_TYPE_BY_FIELD.get(field, field))
        payload.setdefault("target_key", StrategyAlignmentN1Service._identity_target_key(field, payload))
        return payload

    @staticmethod
    def _identity_field_for_maturation_item(item_type: str | None, payload: dict[str, Any]) -> str | None:
        raw_field = _clean_text(payload.get("identity_field") or payload.get("field"))
        if raw_field:
            field = StrategyAlignmentN1Service._identity_payload_field(raw_field)
            if field in StrategyAlignmentN1Service._IDENTITY_ITEM_TYPE_BY_FIELD:
                return field

        normalized_item_type = _slug(payload.get("item_type") or item_type).replace("-", "_")
        item_type_to_field = {
            _slug(mapped_item_type).replace("-", "_"): field
            for field, mapped_item_type in StrategyAlignmentN1Service._IDENTITY_ITEM_TYPE_BY_FIELD.items()
        }
        return item_type_to_field.get(normalized_item_type)

    @staticmethod
    def _canonical_identity_item_payload(field: str, payload: dict[str, Any]) -> dict[str, Any]:
        canonical = dict(payload)
        canonical.pop("identity_field", None)
        canonical.pop("field", None)
        canonical.pop("item_type", None)
        canonical["status"] = "confirmed"

        target_key = StrategyAlignmentN1Service._identity_target_key(field, canonical)
        if target_key:
            canonical.setdefault("target_key", target_key)
            canonical.setdefault("key", target_key)
        return canonical

    @staticmethod
    def _identity_item_keys_match(left: str | None, right: str | None) -> bool:
        left_clean = _clean_text(left)
        right_clean = _clean_text(right)
        if not left_clean or not right_clean:
            return False
        return left_clean.casefold() == right_clean.casefold() or _slug(left_clean) == _slug(right_clean)

    @staticmethod
    def _upsert_identity_list_item(
        existing_items: Any,
        *,
        field: str,
        item_payload: dict[str, Any],
    ) -> tuple[list[Any], str, str | None]:
        target_key = StrategyAlignmentN1Service._identity_target_key(field, item_payload)
        updated_items: list[Any] = []
        replaced = False

        for existing in _safe_list(existing_items, field=field):
            existing_key = (
                StrategyAlignmentN1Service._identity_target_key(field, existing)
                if isinstance(existing, dict)
                else _clean_text(existing)
            )
            if target_key and StrategyAlignmentN1Service._identity_item_keys_match(existing_key, target_key):
                updated_items.append(item_payload)
                replaced = True
            else:
                updated_items.append(existing)

        if not replaced:
            updated_items.append(item_payload)

        return updated_items, ("replace" if replaced else "append"), target_key

    @staticmethod
    def _split_identity_payload_for_maturation(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        canonical_payload = dict(payload)
        staged_payloads: list[dict[str, Any]] = []

        for raw_field in tuple(StrategyAlignmentN1Service._IDENTITY_LIST_FIELD_ALIASES.keys()) + tuple(
            value for value in StrategyAlignmentN1Service._IDENTITY_ITEM_TYPE_BY_FIELD if value != "swot"
        ):
            if raw_field not in payload:
                continue
            field = StrategyAlignmentN1Service._identity_payload_field(raw_field)
            canonical_items: list[Any] = []
            staged_field_item = False
            for item in _safe_list(payload.get(raw_field), field=raw_field):
                if isinstance(item, dict) and StrategyAlignmentN1Service._should_stage_payload(item):
                    staged_field_item = True
                    staged_payloads.append(
                        StrategyAlignmentN1Service._identity_nested_maturation_payload(field, item)
                    )
                    continue
                canonical_items.append(item)
            if staged_field_item and not canonical_items:
                canonical_payload.pop(raw_field, None)
            else:
                canonical_payload[raw_field] = canonical_items

        for raw_field in ("swot", "swot_json"):
            if raw_field not in payload:
                continue
            swot_payload = _safe_dict(payload.get(raw_field), field=raw_field)
            if swot_payload and StrategyAlignmentN1Service._should_stage_payload(swot_payload):
                staged = StrategyAlignmentN1Service._identity_nested_maturation_payload("swot", swot_payload)
                staged.setdefault("target_key", "swot")
                staged_payloads.append(staged)
                canonical_payload.pop(raw_field, None)

        return canonical_payload, staged_payloads

    @staticmethod
    def _has_canonical_identity_update(payload: dict[str, Any]) -> bool:
        for key, value in (payload or {}).items():
            if key in StrategyAlignmentN1Service._MATURATION_CONTROL_KEYS:
                continue
            if key not in StrategyAlignmentN1Service._IDENTITY_FIELD_MAP:
                continue
            if value in (None, ""):
                continue
            if isinstance(value, (list, tuple, dict)) and len(value) == 0:
                continue
            return True
        return False

    @staticmethod
    def _maturation_title(block_type: str, payload: dict[str, Any]) -> str:
        return (
            _clean_text(payload.get("title"))
            or _clean_text(payload.get("name"))
            or _clean_text(payload.get("objective"))
            or _clean_text(payload.get("target_key"))
            or _clean_text(payload.get("key"))
            or f"Item de maturação {block_type}"
        )

    @staticmethod
    def create_maturation_item(
        company_id: int,
        *,
        block_type: str,
        payload: dict[str, Any],
        item_type: str | None = None,
        target_ref_type: str | None = None,
        target_ref_id: int | None = None,
        target_key: str | None = None,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        StrategyAlignmentN1Service._require_company(company_id)
        if block_type not in STRATEGY_MATURATION_BLOCK_TYPES:
            raise StrategyAlignmentN1Error(f"Bloco de maturação inválido: {block_type}.")
        if not isinstance(payload, dict):
            raise StrategyAlignmentN1Error("Payload de maturação deve ser um objeto.")

        status = StrategyAlignmentN1Service._normalize_maturation_status(payload.get("status"), default="pending")
        item = StrategyMaturationItem(
            company_id=company_id,
            block_type=block_type,
            item_type=item_type or _clean_text(payload.get("item_type")),
            status=status,
            source=StrategyAlignmentN1Service._normalize_maturation_source(payload.get("source")),
            confidence=payload.get("confidence"),
            state=StrategyAlignmentN1Service._normalize_maturation_state(payload.get("state")),
            title=StrategyAlignmentN1Service._maturation_title(block_type, payload),
            description=_clean_text(payload.get("description") or payload.get("notes")),
            target_ref_type=target_ref_type or _clean_text(payload.get("target_ref_type")),
            target_ref_id=target_ref_id or (int(payload["target_ref_id"]) if payload.get("target_ref_id") not in (None, "") else None),
            target_key=target_key or _clean_text(payload.get("target_key") or payload.get("key")),
            payload_json=dict(payload),
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        db.session.add(item)
        db.session.flush()
        if commit:
            db.session.commit()
        return {"staged": True, "maturation_item": item.to_dict()}

    @staticmethod
    def _is_all_status_filter(status: Any) -> bool:
        return str(status or "").strip().lower() in {"all", "*", "todos", "todas"}

    @staticmethod
    def _payload_status(payload: Any) -> str:
        if isinstance(payload, dict) and payload.get("status") not in (None, ""):
            return StrategyAlignmentN1Service._normalize_maturation_status(payload.get("status"), default="confirmed")
        return "confirmed"

    @staticmethod
    def _payload_matches_status(payload: Any, status: str | None = "confirmed") -> bool:
        if status is None or StrategyAlignmentN1Service._is_all_status_filter(status):
            return True
        normalized = StrategyAlignmentN1Service._normalize_maturation_status(status, default="confirmed")
        return StrategyAlignmentN1Service._payload_status(payload) == normalized

    @staticmethod
    def _filter_payload_list_by_status(items: Any, *, status: str | None = "confirmed", field: str = "items") -> list[Any]:
        return [
            item
            for item in _safe_list(items, field=field)
            if StrategyAlignmentN1Service._payload_matches_status(item, status)
        ]

    @staticmethod
    def _filter_payload_dict_by_status(payload: Any, *, status: str | None = "confirmed", field: str = "payload") -> dict[str, Any]:
        data = _safe_dict(payload, field=field)
        if not data:
            return {}
        return data if StrategyAlignmentN1Service._payload_matches_status(data, status) else {}

    @staticmethod
    def _filter_identity_payload_by_status(
        identity: dict[str, Any],
        *,
        status: str | None = "confirmed",
    ) -> dict[str, Any]:
        payload = dict(identity or {})
        if status is None or StrategyAlignmentN1Service._is_all_status_filter(status):
            return payload
        for field in (
            "values",
            "value_propositions",
            "differentials",
            "pillars",
            "strategic_objectives",
            "essential_competencies",
            "segments_icp",
            "policies",
            "stakeholders",
            "corporate_indicators",
        ):
            payload[field] = StrategyAlignmentN1Service._filter_payload_list_by_status(
                payload.get(field, []),
                status=status,
                field=field,
            )
        payload["swot"] = StrategyAlignmentN1Service._filter_payload_dict_by_status(
            payload.get("swot", {}),
            status=status,
            field="swot",
        )
        return payload

    @staticmethod
    def _filter_profile_payload_by_status(
        profile: dict[str, Any],
        *,
        status: str | None = "confirmed",
    ) -> dict[str, Any]:
        payload = dict(profile or {})
        if status is None or StrategyAlignmentN1Service._is_all_status_filter(status):
            return payload
        for field in ("indicators", "applicable_policies", "risks"):
            payload[field] = StrategyAlignmentN1Service._filter_payload_list_by_status(
                payload.get(field, []),
                status=status,
                field=field,
            )
        payload["sipoc"] = StrategyAlignmentN1Service._filter_payload_dict_by_status(
            payload.get("sipoc", {}),
            status=status,
            field="sipoc",
        )
        payload["cost_resources_volume"] = StrategyAlignmentN1Service._filter_payload_dict_by_status(
            payload.get("cost_resources_volume", {}),
            status=status,
            field="cost_resources_volume",
        )
        return payload

    @staticmethod
    def _filter_records_by_status(
        records: list[dict[str, Any]],
        *,
        status: str | None = "confirmed",
    ) -> list[dict[str, Any]]:
        if status is None or StrategyAlignmentN1Service._is_all_status_filter(status):
            return list(records or [])
        return [
            dict(item)
            for item in records or []
            if StrategyAlignmentN1Service._payload_matches_status(item, status)
        ]

    @staticmethod
    def _maturation_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
        rows = list(items or [])
        status_counts = Counter(str(item.get("status") or "pending") for item in rows)
        block_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in rows:
            block_rows[str(item.get("block_type") or "unknown")].append(item)

        by_status = {status: int(status_counts.get(status, 0)) for status in STRATEGY_MATURATION_STATUS_VALUES}
        by_block: dict[str, dict[str, Any]] = {}
        for block_type in STRATEGY_MATURATION_BLOCK_TYPES:
            block_items = block_rows.get(block_type, [])
            block_counts = Counter(str(item.get("status") or "pending") for item in block_items)
            canonical = int(block_counts.get("confirmed", 0))
            backlog = int(block_counts.get("draft", 0) + block_counts.get("pending", 0))
            total = len(block_items)
            by_block[block_type] = {
                "total": total,
                "canonical_confirmed": canonical,
                "backlog_open": backlog,
                "rejected": int(block_counts.get("rejected", 0)),
                "maturity_pct": StrategyAlignmentN1Service._pct(canonical, canonical + backlog),
                "by_status": {status: int(block_counts.get(status, 0)) for status in STRATEGY_MATURATION_STATUS_VALUES},
            }

        return {
            "total": len(rows),
            "backlog_open": int(status_counts.get("draft", 0) + status_counts.get("pending", 0)),
            "canonical_confirmed": int(status_counts.get("confirmed", 0)),
            "rejected": int(status_counts.get("rejected", 0)),
            "by_status": by_status,
            "by_block": by_block,
        }

    @staticmethod
    def _promote_maturation_payload(
        *,
        company_id: int,
        item: StrategyMaturationItem,
        payload: dict[str, Any],
        user_id: int | None = None,
    ) -> dict[str, Any]:
        block_type = item.block_type

        if block_type == "identity":
            result = StrategyAlignmentN1Service._promote_identity_maturation_payload(
                company_id=company_id,
                item=item,
                payload=payload,
                user_id=user_id,
            )
            promoted_ref_type = "organizational_identity"
            promoted_ref_id = result.get("id")
            promoted_ref_key = result.get("target_key")
        elif block_type == "process_profile":
            process_id = int(item.target_ref_id or payload.get("process_id") or 0)
            if process_id <= 0:
                raise StrategyAlignmentN1Error("process_id é obrigatório para promover perfil estratégico de processo.")
            result = StrategyAlignmentN1Service.upsert_process_profile(
                company_id=company_id,
                process_id=process_id,
                payload=payload,
                user_id=user_id,
                commit=False,
            )
            promoted_ref_type = "process_strategy_profile"
            promoted_ref_id = result.get("id")
            promoted_ref_key = str(process_id)
        elif block_type == "alignment_link":
            result = StrategyAlignmentN1Service.upsert_alignment_link(
                company_id=company_id,
                payload=payload,
                user_id=user_id,
                commit=False,
            )
            promoted_ref_type = "process_strategic_alignment_link"
            promoted_ref_id = result.get("id")
            promoted_ref_key = result.get("target_key")
        elif block_type == "indicator_line_of_sight":
            result = StrategyAlignmentN1Service.upsert_indicator_line_of_sight(
                company_id=company_id,
                payload=payload,
                user_id=user_id,
                commit=False,
            )
            promoted_ref_type = "indicator_line_of_sight"
            promoted_ref_id = result.get("id")
            promoted_ref_key = (
                f"{result.get('process_indicator_id')}->{result.get('corporate_indicator_id')}"
                if result.get("process_indicator_id") and result.get("corporate_indicator_id")
                else None
            )
        else:
            raise StrategyAlignmentN1Error(f"Bloco de maturação inválido para promoção: {block_type}.")

        item.promoted_ref_type = promoted_ref_type
        item.promoted_ref_id = int(promoted_ref_id) if promoted_ref_id not in (None, "") else None
        item.promoted_ref_key = _clean_text(promoted_ref_key)
        return {
            "block_type": block_type,
            "promoted_ref_type": item.promoted_ref_type,
            "promoted_ref_id": item.promoted_ref_id,
            "promoted_ref_key": item.promoted_ref_key,
            "record": result,
        }

    @staticmethod
    def _promote_identity_maturation_payload(
        *,
        company_id: int,
        item: StrategyMaturationItem,
        payload: dict[str, Any],
        user_id: int | None = None,
    ) -> dict[str, Any]:
        field = StrategyAlignmentN1Service._identity_field_for_maturation_item(item.item_type, payload)
        if not field:
            return StrategyAlignmentN1Service.upsert_identity(
                company_id=company_id,
                payload=payload,
                user_id=user_id,
                commit=False,
            )

        company = StrategyAlignmentN1Service._require_company(company_id)
        identity = OrganizationalIdentity.query.filter_by(company_id=company_id).first()
        if identity is None:
            identity = OrganizationalIdentity(company_id=company_id, created_by_user_id=user_id)
            db.session.add(identity)
        identity.updated_by_user_id = user_id

        item_payload = StrategyAlignmentN1Service._canonical_identity_item_payload(field, payload)
        target_key: str | None = None
        action = "merge"

        if field == "swot":
            current_swot = dict(_safe_dict(identity.swot_json, field="swot"))
            current_swot.update(item_payload)
            identity.swot_json = current_swot
            target_key = "swot"
        else:
            attr = StrategyAlignmentN1Service._IDENTITY_FIELD_MAP.get(field)
            if attr not in StrategyAlignmentN1Service._IDENTITY_LIST_ATTRS:
                return StrategyAlignmentN1Service.upsert_identity(
                    company_id=company_id,
                    payload=payload,
                    user_id=user_id,
                    commit=False,
                )
            next_items, action, target_key = StrategyAlignmentN1Service._upsert_identity_list_item(
                getattr(identity, attr),
                field=field,
                item_payload=item_payload,
            )
            setattr(identity, attr, next_items)
            if attr == "values_json":
                company.values = _json_text(next_items)

        db.session.flush()
        result = identity.to_dict()
        result["canonical_updated"] = True
        result["promoted_field"] = field
        result["promoted_action"] = action
        result["target_key"] = target_key
        return result

    @staticmethod
    def get_identity(company_id: int, *, status: str | None = "confirmed") -> dict[str, Any]:
        company = StrategyAlignmentN1Service._require_company(company_id)
        identity = OrganizationalIdentity.query.filter_by(company_id=company_id).first()
        if identity is not None:
            return StrategyAlignmentN1Service._filter_identity_payload_by_status(identity.to_dict(), status=status)

        payload = {
            "id": None,
            "company_id": company_id,
            "mission": company.mission,
            "vision": company.vision,
            "vision_horizon_year": None,
            "purpose": None,
            "values": [],
            "value_propositions": [],
            "differentials": [],
            "pillars": [],
            "strategic_objectives": [],
            "essential_competencies": [],
            "segments_icp": [],
            "policies": [],
            "stakeholders": [],
            "swot": {},
            "corporate_indicators": [],
            "legacy": {
                "mvv_mission": company.mission,
                "mvv_vision": company.vision,
                "mvv_values": company.values,
                "structured": False,
            },
            "structured": False,
        }
        return StrategyAlignmentN1Service._filter_identity_payload_by_status(payload, status=status)

    @staticmethod
    def upsert_identity(
        company_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise StrategyAlignmentN1Error("Payload de identidade deve ser um objeto.")

        company = StrategyAlignmentN1Service._require_company(company_id)
        if StrategyAlignmentN1Service._should_stage_payload(payload):
            return StrategyAlignmentN1Service.create_maturation_item(
                company_id,
                block_type="identity",
                payload=payload,
                item_type="organizational_identity",
                target_ref_type="organizational_identity",
                user_id=user_id,
                commit=commit,
            )

        canonical_payload, nested_maturation_payloads = StrategyAlignmentN1Service._split_identity_payload_for_maturation(payload)
        staged_items: list[dict[str, Any]] = []
        for staged_payload in nested_maturation_payloads:
            staged_items.append(
                StrategyAlignmentN1Service.create_maturation_item(
                    company_id,
                    block_type="identity",
                    payload=staged_payload,
                    item_type=_clean_text(staged_payload.get("item_type")) or "organizational_identity_item",
                    target_ref_type="organizational_identity",
                    target_key=_clean_text(staged_payload.get("target_key")),
                    user_id=user_id,
                    commit=False,
                )["maturation_item"]
            )

        identity = OrganizationalIdentity.query.filter_by(company_id=company_id).first()

        should_update_canonical = bool(StrategyAlignmentN1Service._has_canonical_identity_update(canonical_payload))
        if not should_update_canonical:
            if commit:
                db.session.commit()
            return {
                "staged": bool(staged_items),
                "canonical_updated": False,
                "maturation_items": staged_items,
            }

        if identity is None:
            identity = OrganizationalIdentity(company_id=company_id, created_by_user_id=user_id)
            db.session.add(identity)
        identity.updated_by_user_id = user_id

        for key, value in canonical_payload.items():
            attr = StrategyAlignmentN1Service._IDENTITY_FIELD_MAP.get(key)
            if not attr:
                continue
            if attr in StrategyAlignmentN1Service._IDENTITY_LIST_ATTRS:
                value = _safe_list(value, field=key)
            elif attr == "swot_json":
                value = _safe_dict(value, field=key)
            elif attr == "vision_horizon_year" and value not in (None, ""):
                value = int(value)
            elif attr in {"mission", "vision", "purpose"}:
                value = _clean_text(value)
            setattr(identity, attr, value)

        if "mission" in canonical_payload:
            company.mission = identity.mission
        if "vision" in canonical_payload:
            company.vision = identity.vision
        if "values" in canonical_payload or "values_json" in canonical_payload:
            company.values = _json_text(identity.values_json)

        if commit:
            db.session.commit()
        response = identity.to_dict()
        if staged_items:
            response["staged"] = True
            response["canonical_updated"] = True
            response["maturation_items"] = staged_items
        return response

    @staticmethod
    def get_process_profile(company_id: int, process_id: int, *, status: str | None = "confirmed") -> dict[str, Any]:
        process = StrategyAlignmentN1Service._require_process(company_id, process_id)
        profile = ProcessStrategyProfile.query.filter_by(company_id=company_id, process_id=process_id).first()
        if profile is not None:
            payload = StrategyAlignmentN1Service._filter_profile_payload_by_status(profile.to_dict(), status=status)
            payload["process"] = StrategyAlignmentN1Service._process_payload(process)
            payload["profile_exists"] = True
            return payload
        payload = {
            "id": None,
            "company_id": company_id,
            "process_id": process_id,
            "process": StrategyAlignmentN1Service._process_payload(process),
            "objective": None,
            "owner": process.responsible,
            "owner_employee_id": process.owner_employee_id,
            "customer_type": None,
            "customer_description": None,
            "strategic_criticality": None,
            "maturity_level": process.structuring_level,
            "regulatory_exposure": None,
            "indicators": [],
            "sipoc": {},
            "cost_resources_volume": {},
            "applicable_policies": [],
            "risks": [],
            "profile_exists": False,
        }
        return StrategyAlignmentN1Service._filter_profile_payload_by_status(payload, status=status)

    @staticmethod
    def upsert_process_profile(
        company_id: int,
        process_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise StrategyAlignmentN1Error("Payload do perfil estratégico do processo deve ser um objeto.")
        process = StrategyAlignmentN1Service._require_process(company_id, process_id)
        if StrategyAlignmentN1Service._should_stage_payload(payload):
            staged_payload = dict(payload)
            staged_payload.setdefault("process_id", process_id)
            return StrategyAlignmentN1Service.create_maturation_item(
                company_id,
                block_type="process_profile",
                payload=staged_payload,
                item_type="process_strategy_profile",
                target_ref_type="process",
                target_ref_id=process_id,
                target_key=process.code or str(process_id),
                user_id=user_id,
                commit=commit,
            )
        profile = ProcessStrategyProfile.query.filter_by(company_id=company_id, process_id=process_id).first()
        if profile is None:
            profile = ProcessStrategyProfile(
                company_id=company_id,
                process_id=process_id,
                owner=process.responsible,
                owner_employee_id=process.owner_employee_id,
                created_by_user_id=user_id,
            )
            db.session.add(profile)
        profile.updated_by_user_id = user_id

        for key, value in payload.items():
            attr = StrategyAlignmentN1Service._PROFILE_FIELD_MAP.get(key)
            if not attr:
                continue
            if attr in StrategyAlignmentN1Service._PROFILE_LIST_ATTRS:
                value = _safe_list(value, field=key)
            elif attr in StrategyAlignmentN1Service._PROFILE_DICT_ATTRS:
                value = _safe_dict(value, field=key)
            elif attr == "strategic_criticality" and value not in (None, ""):
                value = _slug(value).replace("-", "_")
                value = {"média": "media", "medio": "media", "médio": "media"}.get(value, value)
                if value not in PROCESS_STRATEGIC_CRITICALITY_VALUES:
                    raise StrategyAlignmentN1Error("Criticidade estratégica inválida. Use alta, media ou baixa.")
            elif attr == "maturity_level" and value not in (None, ""):
                value = _slug(value).replace("-", "_")
                if value not in PROCESS_MATURITY_LEVEL_VALUES:
                    raise StrategyAlignmentN1Error(
                        "Nível de maturidade inválido. Use nao_definido, inicial, gerenciado, padronizado, mensurado ou otimizado."
                    )
            elif attr == "owner_employee_id" and value not in (None, ""):
                value = int(value)
            else:
                value = _clean_text(value)
            setattr(profile, attr, value)

        if commit:
            db.session.commit()
        response = profile.to_dict()
        response["process"] = StrategyAlignmentN1Service._process_payload(process)
        response["profile_exists"] = True
        return response

    @staticmethod
    def list_alignment_links(company_id: int, process_id: int | None = None) -> list[dict[str, Any]]:
        StrategyAlignmentN1Service._require_company(company_id)
        query = ProcessStrategicAlignmentLink.query.filter_by(company_id=company_id)
        if process_id is not None:
            StrategyAlignmentN1Service._require_process(company_id, process_id)
            query = query.filter_by(process_id=process_id)
        links = query.order_by(
            ProcessStrategicAlignmentLink.process_id.asc(),
            ProcessStrategicAlignmentLink.link_type.asc(),
            ProcessStrategicAlignmentLink.id.asc(),
        ).all()
        return [link.to_dict() for link in links]

    @staticmethod
    def upsert_alignment_link(
        company_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise StrategyAlignmentN1Error("Payload do vínculo estratégico deve ser um objeto.")
        process_id = int(payload.get("process_id") or 0)
        if process_id <= 0:
            raise StrategyAlignmentN1Error("process_id é obrigatório para vínculo estratégico.")
        StrategyAlignmentN1Service._require_process(company_id, process_id)
        if StrategyAlignmentN1Service._should_stage_payload(payload):
            return StrategyAlignmentN1Service.create_maturation_item(
                company_id,
                block_type="alignment_link",
                payload=payload,
                item_type=_clean_text(payload.get("link_type")) or "alignment_link",
                target_ref_type=_clean_text(payload.get("target_ref_type")) or "identity_json",
                target_ref_id=int(payload["target_ref_id"]) if payload.get("target_ref_id") not in (None, "") else None,
                target_key=_clean_text(payload.get("target_key")),
                user_id=user_id,
                commit=commit,
            )

        link_id = payload.get("id")
        link = None
        if link_id:
            link = ProcessStrategicAlignmentLink.query.filter_by(company_id=company_id, id=int(link_id)).first()
            if link is None:
                raise StrategyAlignmentN1Error(f"Vínculo estratégico não encontrado: id={link_id}.")
        if link is None:
            link = ProcessStrategicAlignmentLink(company_id=company_id, process_id=process_id, created_by_user_id=user_id)
            db.session.add(link)

        link.link_type = _clean_text(payload.get("link_type")) or link.link_type
        if link.link_type not in STRATEGY_ALIGNMENT_LINK_TYPES:
            raise StrategyAlignmentN1Error(f"Tipo de vínculo estratégico inválido: {link.link_type}.")
        link.process_id = process_id
        link.target_ref_type = _clean_text(payload.get("target_ref_type"))
        if link.target_ref_type and link.target_ref_type not in STRATEGY_ALIGNMENT_TARGET_REF_TYPES:
            raise StrategyAlignmentN1Error(f"Tipo de alvo estratégico inválido: {link.target_ref_type}.")
        link.target_ref_id = int(payload["target_ref_id"]) if payload.get("target_ref_id") not in (None, "") else None
        link.target_key = _clean_text(payload.get("target_key"))
        link.target_payload_json = _safe_dict(payload.get("target_payload") or payload.get("target_payload_json"), field="target_payload") if (payload.get("target_payload") or payload.get("target_payload_json")) is not None else {}
        link.contribution_type = _clean_text(payload.get("contribution_type"))
        link.contribution_weight = payload.get("contribution_weight")
        link.notes = _clean_text(payload.get("notes"))
        link.updated_by_user_id = user_id

        StrategyAlignmentN1Service._validate_alignment_target(company_id, link)

        if commit:
            db.session.commit()
        return link.to_dict()

    @staticmethod
    def delete_alignment_link(company_id: int, link_id: int, *, commit: bool = True) -> dict[str, Any]:
        link = ProcessStrategicAlignmentLink.query.filter_by(company_id=company_id, id=link_id).first()
        if link is None:
            raise StrategyAlignmentN1Error(f"Vínculo estratégico não encontrado no tenant: id={link_id}.")
        payload = link.to_dict()
        db.session.delete(link)
        if commit:
            db.session.commit()
        return {"deleted": True, "link": payload}

    @staticmethod
    def list_indicator_line_of_sight(company_id: int, process_id: int | None = None) -> list[dict[str, Any]]:
        StrategyAlignmentN1Service._require_company(company_id)
        query = IndicatorLineOfSight.query.filter_by(company_id=company_id)
        if process_id is not None:
            StrategyAlignmentN1Service._require_process(company_id, process_id)
            process_indicator_ids = [
                row.id
                for row in Indicator.query.filter_by(company_id=company_id, process_id=process_id).with_entities(Indicator.id).all()
            ]
            if not process_indicator_ids:
                return []
            query = query.filter(IndicatorLineOfSight.process_indicator_id.in_(process_indicator_ids))
        links = query.order_by(IndicatorLineOfSight.id.asc()).all()
        return [item.to_dict() for item in links]

    @staticmethod
    def list_maturation_backlog(
        company_id: int,
        *,
        status: str | None = None,
        block_type: str | None = None,
        source: str | None = None,
        state: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        StrategyAlignmentN1Service._require_company(company_id)
        query = StrategyMaturationItem.query.filter_by(company_id=company_id)
        if status and not StrategyAlignmentN1Service._is_all_status_filter(status):
            query = query.filter_by(status=StrategyAlignmentN1Service._normalize_maturation_status(status, default="pending"))
        if block_type:
            normalized_block = _slug(block_type).replace("-", "_")
            if normalized_block not in STRATEGY_MATURATION_BLOCK_TYPES:
                raise StrategyAlignmentN1Error(f"Bloco de maturação inválido: {block_type}.")
            query = query.filter_by(block_type=normalized_block)
        if source:
            query = query.filter_by(source=StrategyAlignmentN1Service._normalize_maturation_source(source))
        if state:
            query = query.filter_by(state=StrategyAlignmentN1Service._normalize_maturation_state(state))

        rows = (
            query.order_by(StrategyMaturationItem.updated_at.desc(), StrategyMaturationItem.id.desc())
            .limit(max(1, min(int(limit or 200), 500)))
            .all()
        )
        all_rows = StrategyMaturationItem.query.filter_by(company_id=company_id).all()
        summary = StrategyAlignmentN1Service._maturation_summary([row.to_dict() for row in all_rows])
        return {
            "company_id": company_id,
            "summary": summary,
            "items": [row.to_dict() for row in rows],
        }

    @staticmethod
    def review_maturation_item(
        company_id: int,
        item_id: int,
        *,
        decision: str,
        reviewer_user_id: int | None = None,
        notes: str | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        StrategyAlignmentN1Service._require_company(company_id)
        item = StrategyMaturationItem.query.filter_by(company_id=company_id, id=item_id).first()
        if item is None:
            raise StrategyAlignmentN1Error(f"Item de maturação não encontrado no tenant: id={item_id}.")

        normalized_decision = _slug(decision).replace("-", "_")
        if normalized_decision not in STRATEGY_MATURATION_REVIEW_DECISIONS:
            raise StrategyAlignmentN1Error("Decisão inválida. Use confirm, reject ou hold.")

        promoted: dict[str, Any] | None = None
        now = datetime.utcnow()
        item.review_decision = normalized_decision
        item.review_notes = _clean_text(notes)
        item.reviewed_by_user_id = reviewer_user_id
        item.reviewed_at = now
        item.updated_by_user_id = reviewer_user_id

        if normalized_decision == "hold":
            item.status = "pending"
        elif normalized_decision == "reject":
            item.status = "rejected"
        elif normalized_decision == "confirm":
            item.status = "confirmed"
            item.confirmed_by_user_id = reviewer_user_id
            item.confirmed_at = now
            payload = dict(item.payload_json or {})
            payload["status"] = "confirmed"
            promoted = StrategyAlignmentN1Service._promote_maturation_payload(
                company_id=company_id,
                item=item,
                payload=payload,
                user_id=reviewer_user_id,
            )

        if commit:
            db.session.commit()
        return {
            "reviewed": True,
            "decision": normalized_decision,
            "item": item.to_dict(),
            "promoted": promoted,
        }

    @staticmethod
    def upsert_indicator_line_of_sight(
        company_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise StrategyAlignmentN1Error("Payload da linha de visada de indicadores deve ser um objeto.")
        process_indicator_id = int(payload.get("process_indicator_id") or 0)
        corporate_indicator_id = int(payload.get("corporate_indicator_id") or 0)
        if process_indicator_id <= 0 or corporate_indicator_id <= 0:
            raise StrategyAlignmentN1Error("process_indicator_id e corporate_indicator_id são obrigatórios.")

        process_indicator = StrategyAlignmentN1Service._require_indicator(
            company_id,
            process_indicator_id,
            label="indicador de processo",
        )
        corporate_indicator = StrategyAlignmentN1Service._require_indicator(
            company_id,
            corporate_indicator_id,
            label="indicador corporativo",
        )
        if not process_indicator.process_id:
            raise StrategyAlignmentN1Error("Indicador de processo precisa estar vinculado a um processo do tenant.")
        StrategyAlignmentN1Service._require_process(company_id, int(process_indicator.process_id))
        if corporate_indicator.process_id:
            raise StrategyAlignmentN1Error("Indicador corporativo não deve estar vinculado a um processo específico.")
        if StrategyAlignmentN1Service._should_stage_payload(payload):
            return StrategyAlignmentN1Service.create_maturation_item(
                company_id,
                block_type="indicator_line_of_sight",
                payload=payload,
                item_type="indicator_line_of_sight",
                target_ref_type="indicator",
                target_ref_id=process_indicator_id,
                target_key=str(process_indicator_id),
                user_id=user_id,
                commit=commit,
            )

        relationship_type = _clean_text(payload.get("relationship_type")) or "contributes_to"
        if relationship_type not in INDICATOR_LINE_OF_SIGHT_RELATIONSHIP_TYPES:
            raise StrategyAlignmentN1Error(f"Tipo de linha de visada inválido: {relationship_type}.")

        link_id = payload.get("id")
        line = None
        if link_id:
            line = IndicatorLineOfSight.query.filter_by(company_id=company_id, id=int(link_id)).first()
            if line is None:
                raise StrategyAlignmentN1Error(f"Linha de visada não encontrada: id={link_id}.")
        if line is None:
            line = IndicatorLineOfSight.query.filter_by(
                company_id=company_id,
                process_indicator_id=process_indicator_id,
                corporate_indicator_id=corporate_indicator_id,
            ).first()
        if line is None:
            line = IndicatorLineOfSight(
                company_id=company_id,
                process_indicator_id=process_indicator_id,
                corporate_indicator_id=corporate_indicator_id,
                created_by_user_id=user_id,
            )
            db.session.add(line)

        line.relationship_type = relationship_type
        line.contribution_weight = payload.get("contribution_weight")
        line.notes = _clean_text(payload.get("notes"))
        line.updated_by_user_id = user_id

        if commit:
            db.session.commit()
        return line.to_dict()

    @staticmethod
    def delete_indicator_line_of_sight(company_id: int, link_id: int, *, commit: bool = True) -> dict[str, Any]:
        line = IndicatorLineOfSight.query.filter_by(company_id=company_id, id=link_id).first()
        if line is None:
            raise StrategyAlignmentN1Error(f"Linha de visada não encontrada no tenant: id={link_id}.")
        payload = line.to_dict()
        db.session.delete(line)
        if commit:
            db.session.commit()
        return {"deleted": True, "line_of_sight": payload}

    @staticmethod
    def get_readiness(company_id: int, accessible_company_ids: Iterable[int] | None = None) -> dict[str, Any]:
        StrategyAlignmentN1Service._ensure_access(company_id, accessible_company_ids)
        identity = StrategyAlignmentN1Service.get_identity(company_id)
        process_count = Process.query.filter_by(company_id=company_id).count()
        profile_count = ProcessStrategyProfile.query.filter_by(company_id=company_id).count()
        links = StrategyAlignmentN1Service.list_alignment_links(company_id)
        line_of_sight_count = IndicatorLineOfSight.query.filter_by(company_id=company_id).count()
        maturation_rows = [row.to_dict() for row in StrategyMaturationItem.query.filter_by(company_id=company_id).all()]
        maturation_summary = StrategyAlignmentN1Service._maturation_summary(maturation_rows)
        process_indicator_count = Indicator.query.filter(
            Indicator.company_id == company_id,
            Indicator.process_id.isnot(None),
        ).count()
        corporate_indicator_count = Indicator.query.filter(
            Indicator.company_id == company_id,
            Indicator.process_id.is_(None),
        ).count()

        identity_fields = {
            "mission": bool(_clean_text(identity.get("mission"))),
            "vision": bool(_clean_text(identity.get("vision"))),
            "values": bool(identity.get("values")),
            "purpose": bool(_clean_text(identity.get("purpose"))),
            "value_propositions": bool(identity.get("value_propositions")),
            "differentials": bool(identity.get("differentials")),
            "pillars": bool(identity.get("pillars")),
            "strategic_objectives": bool(
                identity.get("strategic_objectives")
                or OKRGlobal.query.filter_by(company_id=company_id).first()
                or OKRArea.query.filter_by(company_id=company_id).first()
            ),
            "essential_competencies": bool(identity.get("essential_competencies")),
            "segments_icp": bool(identity.get("segments_icp")),
            "policies": bool(identity.get("policies")),
            "stakeholders": bool(identity.get("stakeholders")),
            "swot": bool(identity.get("swot")),
            "corporate_indicators": bool(identity.get("corporate_indicators") or corporate_indicator_count),
        }
        link_counts = Counter(link["link_type"] for link in links)
        required_link_types = {
            "strategic_objective",
            "strategic_pillar",
            "value_proposition",
            "differential",
            "essential_competence",
            "policy",
        }

        missing_identity = [field for field, present in identity_fields.items() if not present]
        missing_links = sorted(link_type for link_type in required_link_types if link_counts.get(link_type, 0) == 0)
        ready = (
            bool(identity_fields["mission"] and identity_fields["vision"] and identity_fields["strategic_objectives"])
            and process_count > 0
            and link_counts.get("strategic_objective", 0) > 0
        )

        return {
            "company_id": company_id,
            "analysis_id": StrategyAlignmentN1Service.ANALYSIS_ID,
            "read_model": StrategyAlignmentN1Service.READ_MODEL,
            "ready_for_analysis": ready,
            "identity": {
                "structured": bool(identity.get("structured")),
                "field_coverage": identity_fields,
                "missing_fields": missing_identity,
            },
            "process_architecture": {
                "processes": process_count,
                "process_strategy_profiles": profile_count,
                "coverage_pct": round((profile_count / process_count) * 100, 2) if process_count else 0,
            },
            "traceability": {
                "alignment_links": len(links),
                "alignment_links_by_type": dict(link_counts),
                "missing_link_types": missing_links,
                "indicator_line_of_sight_links": line_of_sight_count,
                "process_indicators": process_indicator_count,
                "corporate_indicators": corporate_indicator_count,
            },
            "maturation": maturation_summary,
            "recommended_next_actions": StrategyAlignmentN1Service._readiness_actions(
                missing_identity=missing_identity,
                missing_links=missing_links,
                process_count=process_count,
                profile_count=profile_count,
                process_indicator_count=process_indicator_count,
                line_of_sight_count=line_of_sight_count,
            ),
        }

    @staticmethod
    def run_alignment_analysis(company_id: int, accessible_company_ids: Iterable[int] | None = None) -> dict[str, Any]:
        StrategyAlignmentN1Service._ensure_access(company_id, accessible_company_ids)
        StrategyAlignmentN1Service._require_company(company_id)
        identity = StrategyAlignmentN1Service.get_identity(company_id)
        processes = [StrategyAlignmentN1Service._process_payload(row) for row in Process.query.filter_by(company_id=company_id).all()]
        profiles = [
            StrategyAlignmentN1Service._filter_profile_payload_by_status(row.to_dict(), status="confirmed")
            for row in ProcessStrategyProfile.query.filter_by(company_id=company_id).all()
        ]
        links = StrategyAlignmentN1Service.list_alignment_links(company_id)
        process_indicators = [
            StrategyAlignmentN1Service._indicator_payload(row)
            for row in Indicator.query.filter(Indicator.company_id == company_id, Indicator.process_id.isnot(None)).all()
        ]
        corporate_indicators = [
            StrategyAlignmentN1Service._indicator_payload(row)
            for row in Indicator.query.filter(Indicator.company_id == company_id, Indicator.process_id.is_(None)).all()
        ]
        indicator_line_of_sight = StrategyAlignmentN1Service.list_indicator_line_of_sight(company_id)
        okr_objectives = StrategyAlignmentN1Service._load_okr_objectives(company_id)
        return StrategyAlignmentN1Service.build_alignment_analysis_from_records(
            company_id=company_id,
            identity=identity,
            processes=processes,
            profiles=profiles,
            links=links,
            process_indicators=process_indicators,
            corporate_indicators=corporate_indicators,
            indicator_line_of_sight=indicator_line_of_sight,
            okr_objectives=okr_objectives,
        )

    @staticmethod
    def build_alignment_analysis_from_records(
        *,
        company_id: int,
        identity: dict[str, Any],
        processes: list[dict[str, Any]],
        profiles: list[dict[str, Any]],
        links: list[dict[str, Any]],
        process_indicators: list[dict[str, Any]],
        corporate_indicators: list[dict[str, Any]],
        indicator_line_of_sight: list[dict[str, Any]],
        okr_objectives: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        identity = StrategyAlignmentN1Service._filter_identity_payload_by_status(identity or {}, status="confirmed")
        profiles = [
            StrategyAlignmentN1Service._filter_profile_payload_by_status(item, status="confirmed")
            for item in StrategyAlignmentN1Service._filter_records_by_status(profiles, status="confirmed")
        ]
        links = StrategyAlignmentN1Service._filter_records_by_status(links, status="confirmed")
        process_indicators = StrategyAlignmentN1Service._filter_records_by_status(process_indicators, status="confirmed")
        corporate_indicators = StrategyAlignmentN1Service._filter_records_by_status(corporate_indicators, status="confirmed")
        indicator_line_of_sight = StrategyAlignmentN1Service._filter_records_by_status(indicator_line_of_sight, status="confirmed")
        processes_by_id = {int(item["id"]): item for item in processes if item.get("id") is not None}
        profiles_by_process = {
            int(item["process_id"]): item
            for item in profiles
            if item.get("process_id") is not None
        }
        links_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for link in links:
            links_by_type[str(link.get("link_type"))].append(link)

        objectives = _normalize_identity_items(identity.get("strategic_objectives", []), kind="strategic_objective")
        objectives.extend(okr_objectives or [])
        pillars = _normalize_identity_items(identity.get("pillars", []), kind="strategic_pillar")
        value_propositions = _normalize_identity_items(identity.get("value_propositions", []), kind="value_proposition")
        differentials = _normalize_identity_items(identity.get("differentials", []), kind="differential")
        competencies = _normalize_identity_items(identity.get("essential_competencies", []), kind="essential_competence")
        policies = _normalize_identity_items(identity.get("policies", []), kind="policy")

        objectives_without_process = StrategyAlignmentN1Service._targets_without_process(
            objectives,
            links_by_type["strategic_objective"],
            gap_type="objectives_without_process",
            reason="Objetivo estratégico sem processo contribuinte mapeado.",
        )
        pillars_without_process = StrategyAlignmentN1Service._targets_without_process(
            pillars,
            links_by_type["strategic_pillar"],
            gap_type="pillars_without_process",
            reason="Pilar estratégico sem processo contribuinte mapeado.",
        )
        value_props_without_process = StrategyAlignmentN1Service._targets_without_process(
            value_propositions,
            links_by_type["value_proposition"],
            gap_type="value_propositions_without_process",
            reason="Proposta de valor sem processo que a sustente.",
        )
        differentials_without_process = StrategyAlignmentN1Service._targets_without_process(
            differentials,
            links_by_type["differential"],
            gap_type="differentials_without_process",
            reason="Diferencial competitivo sem processo core mapeado.",
        )
        competencies_without_process = StrategyAlignmentN1Service._targets_without_process(
            competencies,
            links_by_type["essential_competence"],
            gap_type="essential_competencies_without_process",
            reason="Competência essencial sem processo sustentador mapeado.",
        )
        policies_without_process = StrategyAlignmentN1Service._targets_without_process(
            policies,
            links_by_type["policy"],
            gap_type="policies_without_process",
            reason="Política sem processo aplicável mapeado.",
        )

        processes_with_objective = {
            int(link["process_id"])
            for link in links_by_type["strategic_objective"]
            if link.get("process_id") in processes_by_id or int(link.get("process_id") or 0) in processes_by_id
        }
        processes_without_objective = [
            StrategyAlignmentN1Service._with_gap_meta(
                process,
                gap_type="processes_without_objective",
                reason="Processo sem objetivo estratégico contribuído mapeado.",
            )
            for process_id, process in processes_by_id.items()
            if process_id not in processes_with_objective
        ]
        processes_without_purpose = []
        for process_id, process in processes_by_id.items():
            profile = profiles_by_process.get(process_id) or {}
            if not _clean_text(profile.get("objective")) and process_id not in processes_with_objective:
                processes_without_purpose.append(
                    StrategyAlignmentN1Service._with_gap_meta(
                        process,
                        gap_type="processes_without_purpose",
                        reason="Processo sem objetivo do processo e sem contribuição estratégica explícita.",
                    )
                )

        line_process_indicator_ids = {
            int(item["process_indicator_id"])
            for item in indicator_line_of_sight
            if item.get("process_indicator_id") is not None
        }
        process_indicators_without_corporate = [
            StrategyAlignmentN1Service._with_gap_meta(
                indicator,
                gap_type="process_indicators_without_corporate",
                reason="Indicador de processo sem linha de visada para indicador corporativo.",
            )
            for indicator in process_indicators
            if int(indicator.get("id") or 0) not in line_process_indicator_ids
        ]

        values_without_policy = [
            StrategyAlignmentN1Service._with_gap_meta(
                value,
                gap_type="values_without_policy",
                reason="Valor organizacional sem política vinculada.",
            )
            for value in StrategyAlignmentN1Service._values_without_policy(identity)
        ]
        crossings = {
            "process_to_objectives": StrategyAlignmentN1Service._crossings_for_links(
                links_by_type["strategic_objective"],
                processes_by_id,
                objectives,
            ),
            "process_to_pillars": StrategyAlignmentN1Service._crossings_for_links(
                links_by_type["strategic_pillar"],
                processes_by_id,
                pillars,
            ),
            "process_to_value_propositions": StrategyAlignmentN1Service._crossings_for_links(
                links_by_type["value_proposition"],
                processes_by_id,
                value_propositions,
            ),
            "process_to_differentials": StrategyAlignmentN1Service._crossings_for_links(
                links_by_type["differential"],
                processes_by_id,
                differentials,
            ),
            "process_to_policies": StrategyAlignmentN1Service._crossings_for_links(
                links_by_type["policy"],
                processes_by_id,
                policies,
            ),
            "indicator_line_of_sight": indicator_line_of_sight,
        }
        gaps = {
            "objectives_without_process": objectives_without_process,
            "processes_without_objective": processes_without_objective,
            "processes_without_purpose": processes_without_purpose,
            "pillars_without_process": pillars_without_process,
            "value_propositions_without_process": value_props_without_process,
            "differentials_without_process": differentials_without_process,
            "essential_competencies_without_process": competencies_without_process,
            "policies_without_process": policies_without_process,
            "values_without_policy": values_without_policy,
            "process_indicators_without_corporate": process_indicators_without_corporate,
        }
        gap_counts = {name: len(items) for name, items in gaps.items()}
        completeness = StrategyAlignmentN1Service._analysis_completeness(
            identity=identity,
            processes=processes,
            profiles=profiles,
            objectives=objectives,
            pillars=pillars,
            value_propositions=value_propositions,
            differentials=differentials,
            competencies=competencies,
            policies=policies,
            process_indicators=process_indicators,
            indicator_line_of_sight=indicator_line_of_sight,
            gaps=gaps,
        )
        risk_signals = StrategyAlignmentN1Service._analysis_risk_signals(
            gaps=gaps,
            crossings=crossings,
            profiles_by_process=profiles_by_process,
            processes_by_id=processes_by_id,
            links_by_type=links_by_type,
        )

        return {
            "company_id": company_id,
            "analysis_id": StrategyAlignmentN1Service.ANALYSIS_ID,
            "read_model": StrategyAlignmentN1Service.READ_MODEL,
            "summary": {
                "processes": len(processes),
                "process_profiles": len(profiles),
                "strategic_objectives": len(objectives),
                "pillars": len(pillars),
                "value_propositions": len(value_propositions),
                "differentials": len(differentials),
                "essential_competencies": len(competencies),
                "policies": len(policies),
                "alignment_links": len(links),
                "process_indicators": len(process_indicators),
                "corporate_indicators": len(corporate_indicators),
                "indicator_line_of_sight_links": len(indicator_line_of_sight),
                "gap_counts": gap_counts,
                "risk_signal_count": len(risk_signals),
            },
            "completeness": completeness,
            "risk_signals": risk_signals,
            "gaps": gaps,
            "crossings": crossings,
            "recommended_actions": StrategyAlignmentN1Service._analysis_actions(
                gaps=gaps,
                risk_signals=risk_signals,
            ),
        }

    @staticmethod
    def _validate_alignment_target(company_id: int, link: ProcessStrategicAlignmentLink) -> None:
        if link.target_ref_type in {"identity_json", "policy", "custom", None}:
            if not link.target_ref_id and not link.target_key:
                raise StrategyAlignmentN1Error("Informe target_key ou target_ref_id para o vínculo estratégico.")
            return
        if not link.target_ref_id:
            raise StrategyAlignmentN1Error(f"target_ref_id é obrigatório para target_ref_type={link.target_ref_type}.")
        if link.target_ref_type == "okr_global":
            exists = OKRGlobal.query.filter_by(company_id=company_id, id=link.target_ref_id).first()
        elif link.target_ref_type == "okr_area":
            exists = OKRArea.query.filter_by(company_id=company_id, id=link.target_ref_id).first()
        elif link.target_ref_type == "indicator":
            exists = Indicator.query.filter_by(company_id=company_id, id=link.target_ref_id).first()
        else:
            exists = True
        if not exists:
            raise StrategyAlignmentN1Error(
                f"Alvo estratégico não encontrado no tenant: {link.target_ref_type}:{link.target_ref_id}."
            )

    @staticmethod
    def _process_payload(process: Process) -> dict[str, Any]:
        return {
            "id": process.id,
            "company_id": process.company_id,
            "macro_id": process.macro_id,
            "code": process.code,
            "name": process.name,
            "description": process.description,
            "responsible": process.responsible,
            "responsible_id": process.responsible_id,
            "owner_employee_id": process.owner_employee_id,
            "structuring_level": process.structuring_level,
            "performance_level": process.performance_level,
            "is_active": bool(process.is_active),
        }

    @staticmethod
    def _indicator_payload(indicator: Indicator) -> dict[str, Any]:
        payload = indicator.to_dict()
        payload.update(
            {
                "process_id": indicator.process_id,
                "source_scope": indicator.source_scope,
                "source_module": indicator.source_module,
                "indicator_type": indicator.indicator_type,
            }
        )
        return payload

    @staticmethod
    def _load_okr_objectives(company_id: int) -> list[dict[str, Any]]:
        objectives: list[dict[str, Any]] = []
        for okr in OKRGlobal.query.filter_by(company_id=company_id).all():
            objectives.append(
                {
                    "kind": "strategic_objective",
                    "key": f"okr_global:{okr.id}",
                    "target_key": f"okr_global:{okr.id}",
                    "target_ref_type": "okr_global",
                    "target_ref_id": okr.id,
                    "objective": okr.objective,
                    "owner": okr.owner,
                    "deadline": okr.deadline.isoformat() if okr.deadline else None,
                    "key_results": [kr.to_dict() for kr in okr.key_results],
                }
            )
        for okr in OKRArea.query.filter_by(company_id=company_id).all():
            objectives.append(
                {
                    "kind": "strategic_objective",
                    "key": f"okr_area:{okr.id}",
                    "target_key": f"okr_area:{okr.id}",
                    "target_ref_type": "okr_area",
                    "target_ref_id": okr.id,
                    "objective": okr.objective,
                    "owner": okr.owner,
                    "department": okr.department,
                    "deadline": okr.deadline.isoformat() if okr.deadline else None,
                    "key_results": [kr.to_dict() for kr in okr.key_results],
                }
            )
        return objectives

    @staticmethod
    def _target_matches(link: dict[str, Any], target: dict[str, Any]) -> bool:
        target_ref_type = target.get("target_ref_type")
        target_ref_id = target.get("target_ref_id")
        if target_ref_type and target_ref_id and link.get("target_ref_type") == target_ref_type:
            try:
                if int(link.get("target_ref_id") or 0) == int(target_ref_id):
                    return True
            except (TypeError, ValueError):
                pass
        link_key = _clean_text(link.get("target_key"))
        if link_key:
            candidates = {
                _slug(target.get("key")),
                _slug(target.get("target_key")),
                _slug(target.get("name")),
                _slug(target.get("objective")),
                _slug(target.get("title")),
                _slug(target.get("code")),
            }
            return _slug(link_key) in candidates
        return False

    @staticmethod
    def _with_gap_meta(
        item: dict[str, Any],
        *,
        gap_type: str,
        reason: str,
        status: str = "unmapped",
        severity: str = "medium",
    ) -> dict[str, Any]:
        payload = dict(item or {})
        payload["gap_type"] = gap_type
        payload["gap_status"] = StrategyAlignmentN1Service._normalize_gap_status(
            payload.get("gap_status") or payload.get("mapping_status") or payload.get("status") or status
        )
        payload["severity"] = payload.get("severity") or severity
        payload["reason"] = payload.get("reason") or reason
        return payload

    @staticmethod
    def _normalize_gap_status(value: Any) -> str:
        normalized = _slug(value).replace("-", "_")
        if normalized in {"mapped", "unmapped", "confirmed_none", "misaligned"}:
            return normalized
        return "unmapped"

    @staticmethod
    def _targets_without_process(
        targets: list[dict[str, Any]],
        links: list[dict[str, Any]],
        *,
        gap_type: str,
        reason: str,
    ) -> list[dict[str, Any]]:
        missing: list[dict[str, Any]] = []
        for target in targets:
            if not any(StrategyAlignmentN1Service._target_matches(link, target) for link in links):
                missing.append(
                    StrategyAlignmentN1Service._with_gap_meta(
                        target,
                        gap_type=gap_type,
                        reason=reason,
                    )
                )
        return missing

    @staticmethod
    def _pct(numerator: int | float, denominator: int | float) -> float | None:
        if not denominator:
            return None
        return round((float(numerator) / float(denominator)) * 100, 2)

    @staticmethod
    def _analysis_completeness(
        *,
        identity: dict[str, Any],
        processes: list[dict[str, Any]],
        profiles: list[dict[str, Any]],
        objectives: list[dict[str, Any]],
        pillars: list[dict[str, Any]],
        value_propositions: list[dict[str, Any]],
        differentials: list[dict[str, Any]],
        competencies: list[dict[str, Any]],
        policies: list[dict[str, Any]],
        process_indicators: list[dict[str, Any]],
        indicator_line_of_sight: list[dict[str, Any]],
        gaps: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        identity_fields = {
            "mission": bool(_clean_text(identity.get("mission"))),
            "vision": bool(_clean_text(identity.get("vision"))),
            "values": bool(identity.get("values")),
            "purpose": bool(_clean_text(identity.get("purpose"))),
            "value_propositions": bool(identity.get("value_propositions")),
            "differentials": bool(identity.get("differentials")),
            "pillars": bool(identity.get("pillars")),
            "strategic_objectives": bool(identity.get("strategic_objectives") or objectives),
            "essential_competencies": bool(identity.get("essential_competencies")),
            "segments_icp": bool(identity.get("segments_icp")),
            "policies": bool(identity.get("policies")),
            "stakeholders": bool(identity.get("stakeholders")),
            "swot": bool(identity.get("swot")),
            "corporate_indicators": bool(identity.get("corporate_indicators")),
        }
        identity_present = sum(1 for present in identity_fields.values() if present)
        identity_total = len(identity_fields)

        target_totals = {
            "objectives": len(objectives),
            "pillars": len(pillars),
            "value_propositions": len(value_propositions),
            "differentials": len(differentials),
            "essential_competencies": len(competencies),
            "policies": len(policies),
        }
        target_missing = {
            "objectives": len(gaps.get("objectives_without_process", [])),
            "pillars": len(gaps.get("pillars_without_process", [])),
            "value_propositions": len(gaps.get("value_propositions_without_process", [])),
            "differentials": len(gaps.get("differentials_without_process", [])),
            "essential_competencies": len(gaps.get("essential_competencies_without_process", [])),
            "policies": len(gaps.get("policies_without_process", [])),
        }
        traceability_total = sum(target_totals.values()) + len(processes)
        traceability_mapped = (
            sum(max(target_totals[key] - target_missing[key], 0) for key in target_totals)
            + max(len(processes) - len(gaps.get("processes_without_objective", [])), 0)
        )
        line_process_indicator_ids = {
            int(item["process_indicator_id"])
            for item in indicator_line_of_sight
            if item.get("process_indicator_id") is not None
        }
        indicator_total = len(process_indicators)
        indicator_mapped = len(
            {
                int(indicator.get("id") or 0)
                for indicator in process_indicators
                if int(indicator.get("id") or 0) in line_process_indicator_ids
            }
        )
        block_scores = {
            "identity": StrategyAlignmentN1Service._pct(identity_present, identity_total),
            "process_profiles": StrategyAlignmentN1Service._pct(len(profiles), len(processes)),
            "traceability": StrategyAlignmentN1Service._pct(traceability_mapped, traceability_total),
            "indicators": StrategyAlignmentN1Service._pct(indicator_mapped, indicator_total),
        }
        applicable_scores = [score for score in block_scores.values() if score is not None]
        gap_status_counts: dict[str, dict[str, int]] = {}
        for gap_type, items in gaps.items():
            counts = Counter(item.get("gap_status", "unmapped") for item in items)
            gap_status_counts[gap_type] = {
                "unmapped": int(counts.get("unmapped", 0)),
                "confirmed_none": int(counts.get("confirmed_none", 0)),
                "misaligned": int(counts.get("misaligned", 0)),
            }

        return {
            "overall_pct": round(sum(applicable_scores) / len(applicable_scores), 2) if applicable_scores else 100.0,
            "by_block": {
                "identity": {
                    "pct": block_scores["identity"],
                    "present": identity_present,
                    "total": identity_total,
                    "missing_fields": [field for field, present in identity_fields.items() if not present],
                },
                "process_profiles": {
                    "pct": block_scores["process_profiles"],
                    "mapped": len(profiles),
                    "total": len(processes),
                },
                "traceability": {
                    "pct": block_scores["traceability"],
                    "mapped": traceability_mapped,
                    "total": traceability_total,
                    "target_totals": target_totals,
                    "target_missing": target_missing,
                },
                "indicators": {
                    "pct": block_scores["indicators"],
                    "mapped": indicator_mapped,
                    "total": indicator_total,
                },
            },
            "gap_status_counts": gap_status_counts,
        }

    @staticmethod
    def _crossings_for_links(
        links: list[dict[str, Any]],
        processes_by_id: dict[int, dict[str, Any]],
        targets: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        crossings: list[dict[str, Any]] = []
        for link in links:
            process = processes_by_id.get(int(link.get("process_id") or 0))
            target = next((item for item in targets if StrategyAlignmentN1Service._target_matches(link, item)), None)
            crossings.append(
                {
                    "link_id": link.get("id"),
                    "process": process,
                    "target": target or {
                        "target_ref_type": link.get("target_ref_type"),
                        "target_ref_id": link.get("target_ref_id"),
                        "target_key": link.get("target_key"),
                        "target_payload": link.get("target_payload") or link.get("target_payload_json") or {},
                    },
                    "contribution_type": link.get("contribution_type"),
                    "contribution_weight": link.get("contribution_weight"),
                    "notes": link.get("notes"),
                }
            )
        return crossings

    @staticmethod
    def _maturity_risk_weight(maturity_level: Any) -> float | None:
        normalized = _slug(maturity_level).replace("-", "_")
        if normalized in {"", "nao_definido", "na", "none"}:
            return 0.9
        if normalized == "inicial":
            return 0.9
        if normalized == "gerenciado":
            return 0.7
        return None

    @staticmethod
    def _severity_from_weight(weight: float) -> str:
        if weight >= 0.85:
            return "high"
        if weight >= 0.6:
            return "medium"
        return "low"

    @staticmethod
    def _risk_signal(
        *,
        signal_type: str,
        weight: float,
        reason: str,
        process: dict[str, Any] | None = None,
        target: dict[str, Any] | None = None,
        gap_type: str | None = None,
    ) -> dict[str, Any]:
        return {
            "signal_type": signal_type,
            "severity": StrategyAlignmentN1Service._severity_from_weight(weight),
            "weight": round(weight, 2),
            "gap_status": "misaligned",
            "gap_type": gap_type,
            "process": process,
            "target": target,
            "reason": reason,
        }

    @staticmethod
    def _analysis_risk_signals(
        *,
        gaps: dict[str, list[dict[str, Any]]],
        crossings: dict[str, list[dict[str, Any]]],
        profiles_by_process: dict[int, dict[str, Any]],
        processes_by_id: dict[int, dict[str, Any]],
        links_by_type: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []

        for crossing in crossings.get("process_to_differentials", []):
            process = crossing.get("process") or {}
            process_id = int(process.get("id") or 0)
            profile = profiles_by_process.get(process_id) or {}
            weight = StrategyAlignmentN1Service._maturity_risk_weight(
                profile.get("maturity_level") or process.get("structuring_level")
            )
            if weight is not None:
                signals.append(
                    StrategyAlignmentN1Service._risk_signal(
                        signal_type="differential_low_maturity_process",
                        weight=weight,
                        process=process,
                        target=crossing.get("target"),
                        gap_type="process_to_differentials",
                        reason="Diferencial competitivo sustentado por processo de baixa maturidade.",
                    )
                )

        for process in gaps.get("processes_without_objective", []):
            profile = profiles_by_process.get(int(process.get("id") or 0)) or {}
            criticality = _slug(profile.get("strategic_criticality")).replace("-", "_")
            if criticality == "alta":
                signals.append(
                    StrategyAlignmentN1Service._risk_signal(
                        signal_type="high_criticality_process_without_objective",
                        weight=0.85,
                        process=processes_by_id.get(int(process.get("id") or 0), process),
                        gap_type="processes_without_objective",
                        reason="Processo de criticidade alta sem contribuição estratégica explícita.",
                    )
                )

        policy_process_ids = {
            int(link.get("process_id") or 0)
            for link in links_by_type.get("policy", [])
            if link.get("process_id") is not None
        }
        for process_id, profile in profiles_by_process.items():
            if _clean_text(profile.get("regulatory_exposure")) and process_id not in policy_process_ids:
                signals.append(
                    StrategyAlignmentN1Service._risk_signal(
                        signal_type="regulatory_exposure_without_policy_link",
                        weight=0.9,
                        process=processes_by_id.get(process_id),
                        target={"regulatory_exposure": profile.get("regulatory_exposure")},
                        gap_type="policies_without_process",
                        reason="Processo com exposição regulatória sem política/requisito regulatório vinculado.",
                    )
                )

        for indicator in gaps.get("process_indicators_without_corporate", []):
            signals.append(
                StrategyAlignmentN1Service._risk_signal(
                    signal_type="process_indicator_without_corporate_line_of_sight",
                    weight=0.65,
                    process=processes_by_id.get(int(indicator.get("process_id") or 0)),
                    target=indicator,
                    gap_type="process_indicators_without_corporate",
                    reason="Indicador operacional sem linha de visada corporativa.",
                )
            )

        signals.sort(key=lambda item: (-float(item.get("weight") or 0), item.get("signal_type") or ""))
        return signals

    @staticmethod
    def _values_without_policy(identity: dict[str, Any]) -> list[dict[str, Any]]:
        values = _normalize_identity_items(identity.get("values", []), kind="value")
        policies = _normalize_identity_items(identity.get("policies", []), kind="policy")
        if not values:
            return []
        if not policies:
            return values

        missing: list[dict[str, Any]] = []
        policy_keys = {_slug(item.get("key")) for item in policies} | {_slug(item.get("name")) for item in policies}
        for value in values:
            linked_keys = value.get("policy_keys") or value.get("policies") or []
            if isinstance(linked_keys, str):
                linked_keys = [linked_keys]
            if not linked_keys or not any(_slug(item) in policy_keys for item in linked_keys):
                missing.append(value)
        return missing

    @staticmethod
    def _readiness_actions(
        *,
        missing_identity: list[str],
        missing_links: list[str],
        process_count: int,
        profile_count: int,
        process_indicator_count: int,
        line_of_sight_count: int,
    ) -> list[str]:
        actions: list[str] = []
        if missing_identity:
            actions.append("Completar identidade organizacional estruturada: " + ", ".join(missing_identity[:6]))
        if process_count == 0:
            actions.append("Cadastrar arquitetura de processos antes da análise N1.")
        elif profile_count < process_count:
            actions.append("Preencher perfil estratégico dos processos sem objetivo/dono/criticidade/SIPOC.")
        if missing_links:
            actions.append("Criar vínculos de rastreabilidade pendentes: " + ", ".join(missing_links))
        if process_indicator_count and line_of_sight_count == 0:
            actions.append("Vincular indicadores de processo aos indicadores corporativos.")
        if not actions:
            actions.append("Executar analyze_strategic_alignment_n1_tool e revisar gaps.")
        return actions

    @staticmethod
    def _target_label(item: dict[str, Any] | None) -> str:
        if not item:
            return "alvo não informado"
        return (
            _clean_text(item.get("name"))
            or _clean_text(item.get("objective"))
            or _clean_text(item.get("title"))
            or _clean_text(item.get("code"))
            or _clean_text(item.get("key"))
            or _clean_text(item.get("id"))
            or "alvo não informado"
        )

    @staticmethod
    def _action(
        *,
        priority: str,
        gap_type: str,
        action: str,
        target: dict[str, Any] | None = None,
        status: str = "unmapped",
        severity: str = "medium",
        weight: float | None = None,
    ) -> dict[str, Any]:
        return {
            "priority": priority,
            "gap_type": gap_type,
            "gap_status": status,
            "severity": severity,
            "weight": round(weight, 2) if weight is not None else None,
            "action": action,
            "target_label": StrategyAlignmentN1Service._target_label(target),
            "target": target,
        }

    @staticmethod
    def _analysis_actions(
        *,
        gaps: dict[str, list[dict[str, Any]]],
        risk_signals: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        for signal in risk_signals:
            actions.append(
                StrategyAlignmentN1Service._action(
                    priority="P0" if signal.get("severity") == "high" else "P1",
                    gap_type=str(signal.get("gap_type") or signal.get("signal_type") or "risk_signal"),
                    status="misaligned",
                    severity=str(signal.get("severity") or "medium"),
                    weight=float(signal.get("weight") or 0),
                    target=signal.get("target") or signal.get("process"),
                    action=f"Mitigar risco: {signal.get('reason')}",
                )
            )

        action_specs = {
            "objectives_without_process": ("P1", "Vincular objetivo estratégico a processo contribuinte ou registrar confirmed_none."),
            "processes_without_objective": ("P1", "Definir objetivo estratégico contribuído pelo processo ou registrar confirmed_none."),
            "processes_without_purpose": ("P1", "Preencher objetivo do processo e propósito operacional."),
            "pillars_without_process": ("P2", "Vincular pilar estratégico a processos contribuintes."),
            "value_propositions_without_process": ("P1", "Mapear processo que entrega a proposta de valor."),
            "differentials_without_process": ("P1", "Conectar diferencial competitivo ao processo core sustentador."),
            "essential_competencies_without_process": ("P2", "Mapear competência essencial aos processos que a materializam."),
            "policies_without_process": ("P1", "Vincular política ou requisito regulatório aos processos aplicáveis."),
            "values_without_policy": ("P1", "Formalizar ou vincular política que materializa o valor organizacional."),
            "process_indicators_without_corporate": ("P1", "Criar linha de visada entre indicador de processo e indicador corporativo."),
        }
        for gap_type, items in gaps.items():
            priority, action_text = action_specs.get(gap_type, ("P2", "Revisar gap de alinhamento estratégico."))
            for item in items:
                actions.append(
                    StrategyAlignmentN1Service._action(
                        priority=priority,
                        gap_type=gap_type,
                        status=StrategyAlignmentN1Service._normalize_gap_status(item.get("gap_status")),
                        severity=str(item.get("severity") or "medium"),
                        target=item,
                        action=action_text,
                    )
                )

        if not actions:
            actions.append(
                StrategyAlignmentN1Service._action(
                    priority="P3",
                    gap_type="none",
                    status="mapped",
                    severity="low",
                    action="Sem gaps críticos detectados no read model N1 atual; validar mapa com consultor/cliente.",
                )
            )

        priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        actions.sort(
            key=lambda item: (
                priority_rank.get(str(item.get("priority")), 9),
                -float(item.get("weight") or 0),
                str(item.get("gap_type") or ""),
                str(item.get("target_label") or ""),
            )
        )
        return actions


__all__ = ["StrategyAlignmentN1Error", "StrategyAlignmentN1Service"]
